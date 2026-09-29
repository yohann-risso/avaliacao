import { PDFDocument, StandardFonts, rgb } from "pdf-lib";

import { dateBr, monthBr } from "@/lib/dates";
import { brl } from "@/lib/money";
import { reportScopeLabel, summarizeReportRows } from "@/lib/report-selection";
import type { ReportRow } from "@/lib/report";

const CSV_HEADER = [
  "Funcionário",
  "Setor",
  "Função",
  "Grupo",
  "Semanas elegíveis",
  "Semanas avaliadas",
  "Ocorrências",
  "Pontos de regra",
  "Desconto de regras (R$)",
  "Impacto das regras",
  "Média (%)",
  "Base (R$)",
  "Monitoria fixa (R$)",
  "Tempo de casa (R$)",
  "Ajustes manuais (R$)",
  "Total (R$)",
  "Status",
];

function csvCell(value: unknown): string {
  const text = String(value ?? "").replace(/"/g, '""');
  return `"${text}"`;
}

export function buildReportCsv(rows: ReportRow[]): string {
  const lines = [CSV_HEADER, ...rows.map((row) => [
    row.name,
    row.sector,
    row.role,
    row.group,
    row.eligibleWeeks,
    row.evaluatedWeeks,
    row.errors,
    row.rulePoints.toFixed(2),
    row.ruleDiscount.toFixed(2),
    row.ruleImpact,
    row.average?.toFixed(2) || "",
    row.basePayment.toFixed(2),
    row.monitorPayment.toFixed(2),
    row.tenurePayment.toFixed(2),
    row.adjustmentTotal.toFixed(2),
    row.total.toFixed(2),
    row.status,
  ])].map((line) => line.map(csvCell).join(";"));
  return `\uFEFF${lines.join("\r\n")}`;
}

function pdfText(value: unknown): string {
  return String(value ?? "").normalize("NFC").replace(/[^\u0020-\u007E\u00A0-\u00FF]/g, " ");
}

function truncated(value: unknown, maxLength: number): string {
  const text = pdfText(value);
  return text.length > maxLength ? `${text.slice(0, Math.max(0, maxLength - 3))}...` : text;
}

function deductionBrl(value: number): string {
  return value > 0 ? `-${brl(value)}` : brl(0);
}

export function sortReportRowsAlphabetically(rows: ReportRow[]): ReportRow[] {
  return [...rows].sort((left, right) => left.name.localeCompare(right.name, "pt-BR") || left.sector.localeCompare(right.sector, "pt-BR"));
}

export async function buildExecutiveReportPdf({
  month,
  rows,
  sectors,
  query = "",
  includeInactive = false,
}: {
  month: string;
  rows: ReportRow[];
  sectors: string[];
  query?: string;
  includeInactive?: boolean;
}): Promise<Uint8Array> {
  const sortedRows = sortReportRowsAlphabetically(rows);
  const summary = summarizeReportRows(sortedRows);
  const pdf = await PDFDocument.create();
  const regular = await pdf.embedFont(StandardFonts.Helvetica);
  const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
  const pageSize: [number, number] = [842, 595];
  const financialColumns = [34, 216, 330, 422, 500, 576, 650, 731];
  const financialLabels = ["Funcionário", "Setor", "Penalidades", "Base", "Monitoria", "Tempo de casa", "Ajustes", "Total"];
  const weeklyColumns = [34, 206, 320, 390, 462, 534, 606, 682];
  const weeklyLabels = ["Funcionário", "Setor", "Semana", "Assiduidade", "Qualidade", "Taxa de erros", "Produtividade", "Comportamento"];
  let page = pdf.addPage(pageSize);
  let y = 548;

  const drawHeader = () => {
    page.drawRectangle({ x: 0, y: 522, width: 842, height: 73, color: rgb(0.043, 0.094, 0.165) });
    page.drawText(pdfText("Avaliação & Bonificação"), { x: 34, y: 566, font: bold, size: 18, color: rgb(1, 1, 1) });
    page.drawText(pdfText(`Fechamento executivo - ${monthBr(month)}`), { x: 34, y: 547, font: regular, size: 10, color: rgb(0.76, 0.86, 0.93) });
    const employeeScope = includeInactive ? "ativos e inativos" : "somente ativos";
    page.drawText(truncated(`Setores: ${reportScopeLabel(sectors, query)} | Funcionários: ${employeeScope}`, 135), { x: 34, y: 531, font: regular, size: 8, color: rgb(0.66, 0.78, 0.88) });
    y = 500;
  };
  const drawSectionTitle = (title: string) => {
    page.drawText(pdfText(title), { x: 34, y, font: bold, size: 10, color: rgb(0.07, 0.15, 0.23) });
    y -= 18;
  };
  const drawFinancialLabels = () => {
    financialLabels.forEach((label, index) => page.drawText(pdfText(label), { x: financialColumns[index], y, font: bold, size: 7.5, color: rgb(0.38, 0.46, 0.54) }));
    y -= 13;
  };
  const drawWeeklyLabels = () => {
    weeklyLabels.forEach((label, index) => page.drawText(pdfText(label), { x: weeklyColumns[index], y, font: bold, size: 7.2, color: rgb(0.38, 0.46, 0.54) }));
    y -= 13;
  };
  const newFinancialPage = () => {
    page = pdf.addPage(pageSize);
    drawHeader();
    drawSectionTitle("Resumo financeiro por colaborador");
    drawFinancialLabels();
  };
  const newWeeklyPage = () => {
    page = pdf.addPage(pageSize);
    drawHeader();
    drawSectionTitle("Percentuais por quesito - semana a semana");
    drawWeeklyLabels();
  };
  const drawSummaryTable = () => {
    const metrics = [
      { label: "Base bruta", value: brl(summary.baseTotal + summary.ruleDiscount) },
      { label: "Penalidades", value: deductionBrl(summary.ruleDiscount) },
      { label: "Base após regras", value: brl(summary.baseTotal) },
      { label: "Monitoria", value: brl(summary.monitorTotal) },
      { label: "Tempo de casa", value: brl(summary.tenureTotal) },
      { label: "Ajustes", value: `${summary.adjustmentTotal > 0 ? "+" : summary.adjustmentTotal < 0 ? "-" : ""}${brl(Math.abs(summary.adjustmentTotal))}` },
      { label: "Total final", value: brl(summary.total) },
    ];
    const tableX = 34;
    const tableWidth = 776;
    const cellWidth = tableWidth / metrics.length;
    page.drawRectangle({ x: tableX, y: y - 36, width: tableWidth, height: 40, color: rgb(0.95, 0.97, 0.98), borderColor: rgb(0.84, 0.88, 0.91), borderWidth: 0.6 });
    metrics.forEach((metric, index) => {
      const x = tableX + index * cellWidth;
      if (index) page.drawLine({ start: { x, y: y - 36 }, end: { x, y: y + 4 }, thickness: 0.5, color: rgb(0.84, 0.88, 0.91) });
      page.drawText(truncated(metric.label, 20), { x: x + 7, y: y - 9, font: regular, size: 6.7, color: rgb(0.38, 0.46, 0.54) });
      page.drawText(truncated(metric.value, 18), { x: x + 7, y: y - 26, font: index === metrics.length - 1 ? bold : regular, size: 8, color: index === metrics.length - 1 ? rgb(0.09, 0.47, 0.39) : rgb(0.07, 0.15, 0.23) });
    });
    y -= 52;
  };

  drawHeader();
  drawSummaryTable();
  drawSectionTitle("Resumo financeiro por colaborador");
  drawFinancialLabels();

  if (!sortedRows.length) {
    page.drawText("Nenhum registro encontrado para os filtros selecionados.", { x: 34, y: y - 10, font: regular, size: 10, color: rgb(0.38, 0.46, 0.54) });
  }

  for (const row of sortedRows) {
    if (y < 45) newFinancialPage();
    page.drawLine({ start: { x: 34, y: y - 5 }, end: { x: 810, y: y - 5 }, thickness: 0.5, color: rgb(0.86, 0.89, 0.92) });
    const values = [
      truncated(row.name, 30),
      truncated(row.sector, 18),
      truncated(deductionBrl(row.ruleDiscount), 15),
      truncated(brl(row.basePayment), 13),
      truncated(brl(row.monitorPayment), 13),
      truncated(brl(row.tenurePayment), 13),
      truncated(brl(row.adjustmentTotal), 13),
      truncated(brl(row.total), 13),
    ];
    values.forEach((value, index) => page.drawText(pdfText(value), {
      x: financialColumns[index],
      y,
      font: index === 0 || index === 7 ? bold : regular,
      size: 7,
      color: rgb(0.07, 0.15, 0.23),
    }));
    y -= 20;
  }

  const weeklyRows = sortedRows.flatMap((row) => row.weeklyPercentages.map((percentages) => ({ row, percentages })));
  newWeeklyPage();
  if (!weeklyRows.length) {
    page.drawText(pdfText("Não há avaliações semanais para os filtros selecionados."), { x: 34, y: y - 10, font: regular, size: 10, color: rgb(0.38, 0.46, 0.54) });
  }
  const percentage = (value: number) => `${Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
  for (const item of weeklyRows) {
    if (y < 45) newWeeklyPage();
    page.drawLine({ start: { x: 34, y: y - 5 }, end: { x: 810, y: y - 5 }, thickness: 0.5, color: rgb(0.86, 0.89, 0.92) });
    const values = [
      truncated(item.row.name, 28),
      truncated(item.row.sector, 17),
      dateBr(item.percentages.weekStart),
      percentage(item.percentages.assiduidade),
      percentage(item.percentages.qualidade),
      percentage(item.percentages.taxaErros),
      percentage(item.percentages.produtividade),
      percentage(item.percentages.comportamento),
    ];
    values.forEach((value, index) => page.drawText(pdfText(value), {
      x: weeklyColumns[index],
      y,
      font: index === 0 ? bold : regular,
      size: 7,
      color: rgb(0.07, 0.15, 0.23),
    }));
    y -= 18;
  }

  const pages = pdf.getPages();
  pages.forEach((currentPage, index) => {
    currentPage.drawText(pdfText("Documento gerado pelo sistema. Valores consolidados conforme os filtros selecionados."), { x: 34, y: 22, font: regular, size: 7, color: rgb(0.38, 0.46, 0.54) });
    currentPage.drawText(pdfText(`Página ${index + 1} de ${pages.length}`), { x: 754, y: 22, font: regular, size: 7, color: rgb(0.38, 0.46, 0.54) });
  });
  return pdf.save();
}
