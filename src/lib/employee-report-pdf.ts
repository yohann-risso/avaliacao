import { PDFDocument, StandardFonts, rgb } from "pdf-lib";

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

// Standard PDF fonts support Portuguese accents, but not arbitrary Unicode.
function printable(value: unknown): string {
  return String(value ?? "").normalize("NFC").replace(/\t/g, "    ").replace(/[^\x20-\x7E\xA0-\xFF]/g, " ");
}

export async function buildEmployeeReportPdf(input: EmployeeReportPdfInput): Promise<Uint8Array> {
  const { employee, month, weeks, summary } = input;
  const pdf = await PDFDocument.create();
  pdf.setTitle(`Relatório individual - ${employee.name} - ${monthBr(month)}`);
  const regular = await pdf.embedFont(StandardFonts.Helvetica);
  const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
  const width = 595.28;
  const height = 841.89;
  const margin = 40;
  const contentWidth = width - margin * 2;
  const ink = rgb(0.07, 0.15, 0.23);
  let page = pdf.addPage([width, height]);
  let y = height - margin;

  const newPage = () => {
    page = pdf.addPage([width, height]);
    y = height - margin;
    page.drawText(`Relatório individual - ${monthBr(month)} - #${employee.id}`, { x: margin, y, size: 9, font: bold, color: ink });
    y -= 26;
  };
  const ensureSpace = (space: number) => { if (y - space < 46) newPage(); };
  const paragraph = (value: unknown, strong = false, size = 10) => {
    const font = strong ? bold : regular;
    const lineHeight = size + 5;
    // Wrap by actual font width, including long words and explicit newlines.
    for (const rawLine of String(value ?? "").split(/\r\n|\r|\n/)) {
      const words = printable(rawLine).split(/\s+/).filter(Boolean);
      let line = "";
      const draw = () => {
        ensureSpace(lineHeight);
        page.drawText(line, { x: margin, y, size, font, color: ink });
        y -= lineHeight;
        line = "";
      };
      for (const word of words) {
        if (line && font.widthOfTextAtSize(`${line} ${word}`, size) > contentWidth) draw();
        for (const char of `${line ? " " : ""}${word}`) {
          if (font.widthOfTextAtSize(line + char, size) > contentWidth) draw();
          line += char;
        }
      }
      draw();
    }
    y -= 4;
  };
  const section = (title: string) => {
    ensureSpace(120);
    y -= 10;
    page.drawLine({ start: { x: margin, y }, end: { x: width - margin, y }, thickness: 0.6, color: rgb(0.8, 0.85, 0.9) });
    y -= 21;
    paragraph(title, true, 12);
  };

  paragraph("Avaliação & Bonificação", true, 18);
  paragraph(`Relatório individual - Fechamento ${monthBr(month)}`, true, 13);
  paragraph(`${employee.name} (#${employee.id})`, true, 12);
  paragraph(`Setor: ${employee.sector} | Função: ${employee.role}`);
  paragraph(`Admissão: ${dateBr(employee.hire_date)} | Situação atual: ${employee.active ? "Ativo" : "Inativo"}`);
  paragraph(`Semanas da competência: ${weeks.map(dateBr).join(" | ")}`);

  section("Resumo do fechamento");
  if (summary) {
    paragraph(`Status: ${summary.status} | Grupo: ${summary.group} | Semanas avaliadas: ${summary.evaluatedWeeks}/${summary.eligibleWeeks}`);
    paragraph(`Média: ${summary.average === null ? "Sem avaliação" : pct(summary.average)} | Semanas pendentes: ${summary.missingWeeks}`);
    paragraph(`Base após regras: ${brl(summary.basePayment)} | Descontos por regras: ${brl(summary.ruleDiscount)}`);
    paragraph(`Monitoria: ${brl(summary.monitorPayment)} | Tempo de casa: ${brl(summary.tenurePayment)} | Ajustes: ${brl(summary.adjustmentTotal)}`);
    paragraph(`Total do fechamento: ${brl(summary.total)}`, true, 12);
    paragraph(`Aplicação das regras: ${summary.ruleImpact}`);
  } else {
    paragraph("Colaborador sem semanas elegíveis neste fechamento.");
  }

  section("Avaliações, observações e justificativas");
  for (const week of weeks) {
    const evaluations = input.evaluations.filter((item) => String(item.week_start).trim() === week);
    ensureSpace(65);
    paragraph(`Semana de ${dateBr(week)}`, true, 11);
    if (!evaluations.length) paragraph(summary?.group === "Coord./Sup." ? "Sem avaliação semanal registrada. Liderança com base mensal." : "Sem avaliação registrada nesta semana.");
    for (const evaluation of evaluations) {
      paragraph(`Avaliador: ${evaluation.evaluator || "Não informado"}`);
      for (const criterion of WEEKLY_CRITERIA) {
        ensureSpace(48);
        paragraph(`${criterion.label}: ${pct(Number(evaluation[`${criterion.key}_pct`] ?? 0))}`, true);
        paragraph(`Justificativa: ${evaluation[`${criterion.key}_just`] || "Não informada."}`);
      }
      paragraph(`Observações gerais: ${evaluation.notes || "Não informadas."}`);
    }
  }

  section("Ocorrências da competência");
  const occurrences = input.occurrences.filter((item) => weeks.includes(String(item.week_start).trim()));
  if (!occurrences.length) paragraph("Nenhuma ocorrência registrada neste fechamento.");
  for (const occurrence of occurrences) {
    ensureSpace(65);
    const rule = getEvaluationRule(occurrence.error_type);
    paragraph(`${dateBr(occurrence.week_start)} - ${occurrence.error_type} - ${rule?.occurrence || "Regra legada"}`, true);
    paragraph(`Gravidade: ${occurrence.severity} | Quantidade: ${occurrence.qty} | Pontos de referência: ${(Number(rule?.points || 0) * occurrence.qty).toLocaleString("pt-BR")}`);
    paragraph(`Observações: ${occurrence.notes || "Não informadas."}`);
  }

  section("Ajustes financeiros e justificativas");
  const adjustments = input.adjustments.filter((item) => weeks.includes(String(item.week_start).trim()));
  if (!adjustments.length) paragraph("Nenhum ajuste financeiro registrado neste fechamento.");
  for (const adjustment of adjustments) {
    ensureSpace(65);
    paragraph(`${dateBr(adjustment.week_start)} - ${Number(adjustment.amount) >= 0 ? "Acréscimo" : "Desconto"}: ${brl(Math.abs(Number(adjustment.amount)))}`, true);
    paragraph(`Responsável: ${adjustment.created_by_username || "Não informado"}`);
    paragraph(`Justificativa: ${adjustment.description || "Não informada."}`);
  }

  const pages = pdf.getPages();
  pages.forEach((current, index) => {
    current.drawText(`Fechamento ${monthBr(month)} | Colaborador #${employee.id}`, { x: margin, y: 24, font: regular, size: 8, color: ink });
    const label = `Página ${index + 1} de ${pages.length}`;
    current.drawText(label, { x: width - margin - regular.widthOfTextAtSize(label, 8), y: 24, font: regular, size: 8, color: ink });
  });
  return pdf.save();
}
