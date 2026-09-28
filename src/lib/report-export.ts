import { PDFDocument, StandardFonts, rgb } from "pdf-lib";

import { monthBr } from "@/lib/dates";
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
  "Tempo (R$)",
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

export async function buildExecutiveReportPdf({
  month,
  rows,
  sectors,
  query = "",
}: {
  month: string;
  rows: ReportRow[];
  sectors: string[];
  query?: string;
}): Promise<Uint8Array> {
  const summary = summarizeReportRows(rows);
  const pdf = await PDFDocument.create();
  const regular = await pdf.embedFont(StandardFonts.Helvetica);
  const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
  const pageSize: [number, number] = [842, 595];
  const columns = [34, 176, 274, 338, 404, 472, 540, 608, 676, 744];
  const labels = ["Funcionario", "Setor", "Grupo", "Cobertura", "Regras", "Base", "Monitor", "Tempo", "Ajustes", "Total"];
  let page = pdf.addPage(pageSize);
  let y = 548;

  const drawHeader = () => {
    page.drawRectangle({ x: 0, y: 522, width: 842, height: 73, color: rgb(0.043, 0.094, 0.165) });
    page.drawText("Avaliacao & Bonificacao", { x: 34, y: 566, font: bold, size: 18, color: rgb(1, 1, 1) });
    page.drawText(`Fechamento executivo - ${monthBr(month)}`, { x: 34, y: 547, font: regular, size: 10, color: rgb(0.76, 0.86, 0.93) });
    page.drawText(truncated(`Setores: ${reportScopeLabel(sectors, query)}`, 130), { x: 34, y: 531, font: regular, size: 8, color: rgb(0.66, 0.78, 0.88) });
    y = 500;
  };
  const drawColumnLabels = () => {
    labels.forEach((label, index) => page.drawText(label, { x: columns[index], y, font: bold, size: 7.5, color: rgb(0.38, 0.46, 0.54) }));
    y -= 13;
  };
  const newPage = () => {
    page = pdf.addPage(pageSize);
    drawHeader();
    drawColumnLabels();
  };

  drawHeader();
  page.drawText(`Cobertura: ${summary.coverage.toFixed(1)}%`, { x: 34, y, font: bold, size: 10.5, color: rgb(0.07, 0.15, 0.23) });
  page.drawText(`Pendencias: ${summary.pending}`, { x: 220, y, font: bold, size: 10.5, color: rgb(0.07, 0.15, 0.23) });
  page.drawText(`Pessoas: ${rows.length}`, { x: 380, y, font: bold, size: 10.5, color: rgb(0.07, 0.15, 0.23) });
  page.drawText(truncated(`Total: ${brl(summary.total)}`, 30), { x: 535, y, font: bold, size: 10.5, color: rgb(0.09, 0.47, 0.39) });
  y -= 28;
  drawColumnLabels();

  if (!rows.length) {
    page.drawText("Nenhum registro encontrado para os filtros selecionados.", { x: 34, y: y - 10, font: regular, size: 10, color: rgb(0.38, 0.46, 0.54) });
  }

  for (const row of rows) {
    if (y < 45) newPage();
    page.drawLine({ start: { x: 34, y: y - 5 }, end: { x: 810, y: y - 5 }, thickness: 0.5, color: rgb(0.86, 0.89, 0.92) });
    const values = [
      truncated(row.name, 24),
      truncated(row.sector, 16),
      row.group,
      row.group === "Coord./Sup." ? "Base mensal" : `${row.evaluatedWeeks}/${row.eligibleWeeks}`,
      truncated(`-${brl(row.ruleDiscount)}`, 13),
      truncated(brl(row.basePayment), 13),
      truncated(brl(row.monitorPayment), 13),
      truncated(brl(row.tenurePayment), 13),
      truncated(brl(row.adjustmentTotal), 13),
      truncated(brl(row.total), 13),
    ];
    values.forEach((value, index) => page.drawText(pdfText(value), {
      x: columns[index],
      y,
      font: index === 0 || index === 9 ? bold : regular,
      size: 7,
      color: rgb(0.07, 0.15, 0.23),
    }));
    y -= 20;
  }

  const pages = pdf.getPages();
  pages.forEach((currentPage, index) => {
    currentPage.drawText("Documento gerado pelo sistema. Confira as pendencias antes do envio ao RH.", { x: 34, y: 22, font: regular, size: 7, color: rgb(0.38, 0.46, 0.54) });
    currentPage.drawText(`Pagina ${index + 1} de ${pages.length}`, { x: 754, y: 22, font: regular, size: 7, color: rgb(0.38, 0.46, 0.54) });
  });
  return pdf.save();
}
