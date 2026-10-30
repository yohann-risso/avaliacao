import { PDFDocument, StandardFonts, rgb, type Color, type PDFFont } from "pdf-lib";

import { WEEKLY_CRITERIA } from "@/lib/constants";
import { dateBr, monthBr } from "@/lib/dates";
import { brl, pct } from "@/lib/money";
import type { ReportRow } from "@/lib/report";
import { getEvaluationRule } from "@/lib/rules";
import type { BonusAdjustment, Employee, WeeklyError, WeeklyEvaluation } from "@/lib/types";

export type EmployeeReportPdfInput = {
  month: string;
  employee: Employee;
  weeks: string[];
  evaluations: WeeklyEvaluation[];
  occurrences: WeeklyError[];
  adjustments: BonusAdjustment[];
  summary?: ReportRow;
};

// Helvetica supports Portuguese accents. Normalize common punctuation before encoding.
function printable(value: unknown): string {
  return String(value ?? "").normalize("NFC").replace(/[–—−]/g, "-")
    .replace(/[“”]/g, '"').replace(/[‘’]/g, "'").replace(/\t/g, "    ")
    .replace(/[^\x20-\x7E\xA0-\xFF]/g, " ");
}

type Cell = { text: string; bold?: boolean; fill?: Color; color?: Color };
type Column = { label: string; width: number; align?: "left" | "right" | "center" };

export async function buildEmployeeReportPdf(input: EmployeeReportPdfInput): Promise<Uint8Array> {
  const { employee, month, weeks, summary } = input;
  const evaluations = input.evaluations.filter((item) => weeks.includes(String(item.week_start).trim()));
  const occurrences = input.occurrences.filter((item) => weeks.includes(String(item.week_start).trim()));
  const adjustments = input.adjustments.filter((item) => weeks.includes(String(item.week_start).trim()));
  const pdf = await PDFDocument.create();
  pdf.setTitle(`Relatório individual - ${employee.name} - ${monthBr(month)}`);
  pdf.setAuthor("Avaliação & Bonificação");
  const regular = await pdf.embedFont(StandardFonts.Helvetica);
  const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
  const width = 595.28;
  const height = 841.89;
  const margin = 36;
  const contentWidth = width - margin * 2;
  const bottom = 52;
  const navy = rgb(0.063, 0.157, 0.247);
  const teal = rgb(0.078, 0.49, 0.447);
  const muted = rgb(0.39, 0.45, 0.53);
  const line = rgb(0.82, 0.86, 0.9);
  const pale = rgb(0.95, 0.96, 0.97);
  const mint = rgb(0.89, 0.96, 0.94);
  const white = rgb(1, 1, 1);
  const amber = rgb(1, 0.95, 0.84);
  let page = pdf.addPage([width, height]);
  let y = height - margin;

  const text = (value: string, x: number, baseline: number, size = 9, strong = false, color: Color = navy) => {
    page.drawText(printable(value), { x, y: baseline, font: strong ? bold : regular, size, color });
  };
  const wrap = (value: string, maxWidth: number, font: PDFFont, size: number): string[] => {
    const lines: string[] = [];
    for (const raw of value.split(/\r\n|\r|\n/)) {
      let current = "";
      for (const word of printable(raw).split(/\s+/).filter(Boolean)) {
        if (current && font.widthOfTextAtSize(`${current} ${word}`, size) > maxWidth) {
          lines.push(current);
          current = "";
        }
        for (const character of `${current ? " " : ""}${word}`) {
          if (font.widthOfTextAtSize(current + character, size) > maxWidth) {
            lines.push(current);
            current = "";
          }
          current += character;
        }
      }
      lines.push(current);
    }
    return lines;
  };
  const newPage = () => {
    page = pdf.addPage([width, height]);
    y = height - margin;
    text(`Relatório individual - ${monthBr(month)} - #${employee.id}`, margin, y - 8, 8, true, muted);
    page.drawLine({ start: { x: margin, y: y - 19 }, end: { x: width - margin, y: y - 19 }, thickness: 0.6, color: line });
    y -= 42;
  };
  const ensureSpace = (space: number) => { if (y - space < bottom) newPage(); };
  const paragraph = (value: string, size = 9, strong = false, color: Color = muted) => {
    for (const row of wrap(value, contentWidth, strong ? bold : regular, size)) {
      ensureSpace(size + 5);
      text(row, margin, y - size, size, strong, color);
      y -= size + 5;
    }
    y -= 5;
  };
  const section = (number: string, title: string) => {
    ensureSpace(98);
    y -= 12;
    text(number, margin, y - 14, 17, true, teal);
    text(title, margin + 29, y - 13, 12, true);
    y -= 30;
  };

  // Wrap each cell to its measured width and split oversized rows across pages.
  // Repeat headers and identifying cells to preserve context on continuation pages.
  const table = (columns: Column[], rows: Cell[][], size = 8.5) => {
    const padding = 6;
    const leading = size + 4;
    const drawRow = (cells: Cell[], lines: string[][], start: number, count: number, rowHeight: number, header = false, alternate = false) => {
      let x = margin;
      columns.forEach((column, index) => {
        const cell = cells[index];
        page.drawRectangle({ x, y: y - rowHeight, width: column.width, height: rowHeight, color: cell.fill || (header ? rgb(0.9, 0.93, 0.95) : alternate ? pale : white), borderColor: line, borderWidth: 0.4 });
        const font = header || cell.bold ? bold : regular;
        const available = lines[index].slice(start, start + count);
        const visible = available.length ? available : start > 0 && lines[index].length <= start ? lines[index].slice(0, 1) : [];
        visible.forEach((value, lineIndex) => {
          const measured = font.widthOfTextAtSize(value, size);
          const offset = column.align === "right" ? column.width - padding - measured : column.align === "center" ? (column.width - measured) / 2 : padding;
          text(value, x + offset, y - padding - size - lineIndex * leading, size, header || Boolean(cell.bold), cell.color || navy);
        });
        x += column.width;
      });
      y -= rowHeight;
    };
    const headerCells = columns.map((column) => ({ text: column.label, bold: true }));
    const headerLines = columns.map((column) => wrap(column.label, column.width - padding * 2, bold, size));
    const headerHeight = Math.max(...headerLines.map((item) => item.length)) * leading + padding * 2;
    const header = () => drawRow(headerCells, headerLines, 0, Math.max(...headerLines.map((item) => item.length)), headerHeight, true);
    ensureSpace(headerHeight + leading + padding * 2);
    header();
    rows.forEach((cells, rowIndex) => {
      const lines = cells.map((cell, index) => wrap(cell.text, columns[index].width - padding * 2, cell.bold ? bold : regular, size));
      const totalLines = Math.max(...lines.map((item) => item.length));
      const fullHeight = totalLines * leading + padding * 2;
      const freshPageCapacity = height - margin - 42 - bottom - headerHeight;
      if (fullHeight <= freshPageCapacity && y - fullHeight < bottom) { newPage(); header(); }
      let start = 0;
      while (start < totalLines) {
        let capacity = Math.floor((y - bottom - padding * 2) / leading);
        if (capacity < 1) { newPage(); header(); capacity = Math.floor((y - bottom - padding * 2) / leading); }
        const count = Math.min(totalLines - start, capacity);
        drawRow(cells, lines, start, count, count * leading + padding * 2, false, rowIndex % 2 === 1);
        start += count;
        if (start < totalLines) { newPage(); header(); }
      }
    });
    y -= 8;
  };
  const cells = (...values: string[]): Cell[] => values.map((value) => ({ text: value }));

  text("AVALIAÇÃO & BONIFICAÇÃO", margin, y - 10, 10, true);
  const badge = `FECHAMENTO ${monthBr(month)}`;
  const badgeWidth = bold.widthOfTextAtSize(badge, 8) + 20;
  page.drawRectangle({ x: width - margin - badgeWidth, y: y - 18, width: badgeWidth, height: 24, color: navy });
  text(badge, width - margin - badgeWidth + 10, y - 10, 8, true, white);
  y -= 53;
  text("Relatório do colaborador", margin, y, 25, true);
  y -= 16;
  page.drawLine({ start: { x: margin, y }, end: { x: width - margin, y }, thickness: 2, color: teal });
  y -= 23;
  paragraph(employee.name, 19, true, navy);
  paragraph(`#${employee.id} · ${employee.sector} · ${employee.role}`, 10, false, navy);
  paragraph(`Admissão: ${dateBr(employee.hire_date)} | Situação atual: ${employee.active ? "Ativo" : "Inativo"}`, 8);
  paragraph(summary ? (summary.group === "Coord./Sup." ? "Coordenação / Supervisão · Base mensal" : `${summary.evaluatedWeeks} de ${summary.eligibleWeeks} semanas avaliadas · ${summary.status}`) : "Colaborador sem semanas elegíveis neste fechamento.", 9, true, summary?.status === "Pendente" ? muted : teal);

  section("01", "Resumo do fechamento");
  const gap = 8;
  const cardWidth = (contentWidth - gap * 2) / 3;
  ensureSpace(73);
  const metrics = [
    { label: "Média dos critérios", value: summary?.average == null ? "Sem avaliação" : pct(summary.average), fill: pale, color: teal },
    { label: "Ocorrências", value: String(occurrences.reduce((sum, item) => sum + Number(item.qty || 0), 0)), fill: pale, color: teal },
    { label: "Total a receber", value: summary ? brl(summary.total) : "Não elegível", fill: navy, color: white },
  ];
  metrics.forEach((metric, index) => {
    const x = margin + index * (cardWidth + gap);
    page.drawRectangle({ x, y: y - 62, width: cardWidth, height: 62, color: metric.fill });
    text(metric.label, x + 12, y - 18, 8.5, false, index === 2 ? white : navy);
    const size = Math.min(21, (cardWidth - 24) / bold.widthOfTextAtSize(printable(metric.value), 1));
    text(metric.value, x + 12, y - 46, size, true, metric.color);
  });
  y -= 73;
  if (summary) {
    table([{ label: "Composição", width: contentWidth - 125 }, { label: "Valor", width: 125, align: "right" }], [
      cells("Base após regras", brl(summary.basePayment)), cells("Monitoria", brl(summary.monitorPayment)),
      cells("Tempo de casa", brl(summary.tenurePayment)), cells("Ajustes manuais", brl(summary.adjustmentTotal)),
      [{ text: "Total do fechamento", bold: true, fill: mint, color: teal }, { text: brl(summary.total), bold: true, fill: mint, color: teal }],
    ]);
    paragraph(`Desconto por regras: ${brl(summary.ruleDiscount)} · já considerado na base.`, 7.5);
    paragraph(`Aplicação das regras: ${summary.ruleImpact}`, 7.5);
  } else paragraph("Colaborador sem semanas elegíveis neste fechamento.");

  section("02", "Avaliações por semana");
  const weeklyColumns: Column[] = [{ label: "Critério", width: 120 }, ...weeks.map((week) => ({ label: dateBr(week), width: (contentWidth - 180) / Math.max(1, weeks.length), align: "center" as const })), { label: "Média", width: 60, align: "center" }];
  const weeklyRows = WEEKLY_CRITERIA.map((criterion) => {
    const values = evaluations.map((item) => Number(item[`${criterion.key}_pct`] ?? 0));
    return [{ text: criterion.label }, ...weeks.map((week) => {
      const matches = evaluations.filter((item) => String(item.week_start).trim() === week);
      const value = matches.length ? matches.reduce((sum, item) => sum + Number(item[`${criterion.key}_pct`] ?? 0), 0) / matches.length : null;
      return { text: value === null ? "-" : pct(value), fill: value !== null && value < 90 ? amber : undefined };
    }), { text: values.length ? pct(values.reduce((sum, value) => sum + value, 0) / values.length) : "-", bold: true }];
  });
  table(weeklyColumns, weeklyRows, 8);
  paragraph("Percentuais registrados na avaliação. Os valores financeiros seguem as regras do fechamento.", 7.5);
  const missingWeeks = weeks.filter((week) => !evaluations.some((item) => String(item.week_start).trim() === week));
  if (missingWeeks.length) paragraph(`${summary?.group === "Coord./Sup." ? "Base mensal de liderança. " : ""}Sem avaliação registrada nesta semana: ${missingWeeks.map(dateBr).join(", ")}.`, 7.5);

  newPage();
  paragraph("Registros e justificativas", 23, true, navy);
  page.drawLine({ start: { x: margin, y }, end: { x: width - margin, y }, thickness: 2, color: teal });
  y -= 8;
  section("03", "Justificativas das avaliações");
  const justificationRows = weeks.flatMap((week) => evaluations.filter((item) => String(item.week_start).trim() === week).flatMap((evaluation) => WEEKLY_CRITERIA.filter((criterion) => String(evaluation[`${criterion.key}_just`] || "").trim() || Number(evaluation[`${criterion.key}_pct`] ?? 0) < 100).map((criterion) => cells(
    dateBr(week), `${criterion.label}\n${pct(Number(evaluation[`${criterion.key}_pct`] ?? 0))}`,
    String(evaluation[`${criterion.key}_just`] || "Não informada."),
  ))));
  if (justificationRows.length) table([{ label: "Semana", width: 71 }, { label: "Critério / nota", width: 111 }, { label: "Justificativa", width: contentWidth - 182 }], justificationRows);
  else paragraph(evaluations.length ? "Nenhuma justificativa registrada; critérios avaliados em 100%." : "Nenhuma avaliação registrada neste fechamento.");

  section("04", "Observações gerais");
  if (!evaluations.length) paragraph("Nenhuma observação de avaliação registrada neste fechamento.");
  for (const evaluation of evaluations) {
    ensureSpace(65);
    paragraph(`${dateBr(String(evaluation.week_start).trim())} · Avaliador: ${evaluation.evaluator || "Não informado"}`, 9, true, navy);
    const lines = wrap(String(evaluation.notes || "Não informadas."), contentWidth - 14, regular, 9);
    for (const row of lines) {
      ensureSpace(14);
      page.drawLine({ start: { x: margin, y: y + 1 }, end: { x: margin, y: y - 13 }, thickness: 2, color: teal });
      text(row, margin + 12, y - 9, 9);
      y -= 14;
    }
    y -= 6;
  }

  section("05", "Ocorrências da competência");
  if (!occurrences.length) paragraph("Nenhuma ocorrência registrada neste fechamento.");
  else table([{ label: "Semana", width: 71 }, { label: "Regra / gravidade", width: 112 }, { label: "Qtd.", width: 32, align: "center" }, { label: "Pts.", width: 36, align: "center" }, { label: "Observação", width: contentWidth - 251 }], occurrences.map((item) => {
    const rule = getEvaluationRule(item.error_type);
    return cells(dateBr(item.week_start), `${item.error_type} · ${rule?.occurrence || "Regra legada"}\n${item.severity}`, String(item.qty), (Number(rule?.points || 0) * item.qty).toLocaleString("pt-BR"), item.notes || "Não informada.");
  }), 8);

  section("06", "Ajustes financeiros");
  if (!adjustments.length) paragraph("Nenhum ajuste financeiro registrado neste fechamento.");
  else table([{ label: "Semana", width: 71 }, { label: "Tipo / valor", width: 105 }, { label: "Justificativa / responsável", width: contentWidth - 176 }], adjustments.map((item) => cells(
    dateBr(item.week_start), `${Number(item.amount) >= 0 ? "Acréscimo" : "Desconto"}\n${brl(Math.abs(Number(item.amount)))}`,
    `${item.description || "Não informada."}\nResponsável: ${item.created_by_username || "Não informado"}`,
  )));

  const pages = pdf.getPages();
  pages.forEach((current, index) => {
    current.drawLine({ start: { x: margin, y: 38 }, end: { x: width - margin, y: 38 }, thickness: 0.5, color: line });
    current.drawText(`Colaborador #${employee.id} · Fechamento ${monthBr(month)}`, { x: margin, y: 24, font: regular, size: 7.5, color: muted });
    const label = `${index + 1} / ${pages.length}`;
    current.drawText(label, { x: width - margin - regular.widthOfTextAtSize(label, 8), y: 24, font: regular, size: 8, color: muted });
  });
  return pdf.save();
}
