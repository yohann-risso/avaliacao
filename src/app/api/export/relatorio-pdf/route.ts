import { PDFDocument, StandardFonts, rgb } from "pdf-lib";

import { requireAdmin } from "@/lib/auth";
import { currentMonth, monthBr } from "@/lib/dates";
import { brl } from "@/lib/money";
import { buildMonthlyReport } from "@/lib/report";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  await requireAdmin();
  const requested = new URL(request.url).searchParams.get("month") || "";
  const month = /^\d{4}-\d{2}$/.test(requested) ? requested : currentMonth();
  const report = await buildMonthlyReport(month);
  const pdf = await PDFDocument.create();
  const regular = await pdf.embedFont(StandardFonts.Helvetica);
  const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
  const pageSize: [number, number] = [842, 595];
  let page = pdf.addPage(pageSize);
  let y = 548;

  const header = () => {
    page.drawRectangle({ x: 0, y: 535, width: 842, height: 60, color: rgb(0.043, 0.094, 0.165) });
    page.drawText("Avaliacao & Bonificacao", { x: 34, y: 566, font: bold, size: 18, color: rgb(1, 1, 1) });
    page.drawText(`Fechamento executivo - ${monthBr(month)}`, { x: 34, y: 546, font: regular, size: 10, color: rgb(0.76, 0.86, 0.93) });
    y = 516;
  };
  const newPage = () => { page = pdf.addPage(pageSize); header(); };
  header();
  page.drawText(`Cobertura: ${report.coverage.toFixed(1)}%`, { x: 34, y, font: bold, size: 11, color: rgb(0.07, 0.15, 0.23) });
  page.drawText(`Pendencias: ${report.pending}`, { x: 220, y, font: bold, size: 11, color: rgb(0.07, 0.15, 0.23) });
  page.drawText(`Total: ${brl(report.total)}`, { x: 410, y, font: bold, size: 11, color: rgb(0.09, 0.47, 0.39) });
  y -= 28;
  const columns = [34, 235, 330, 410, 495, 580, 665, 755];
  const labels = ["Funcionario", "Grupo", "Cobertura", "Regras", "Base", "Monitor fixo", "Tempo", "Total"];
  labels.forEach((label, index) => page.drawText(label, { x: columns[index], y, font: bold, size: 8, color: rgb(0.38, 0.46, 0.54) }));
  y -= 13;
  for (const row of report.rows) {
    if (y < 45) {
      newPage();
      labels.forEach((label, index) => page.drawText(label, { x: columns[index], y, font: bold, size: 8, color: rgb(0.38, 0.46, 0.54) }));
      y -= 13;
    }
    page.drawLine({ start: { x: 34, y: y - 5 }, end: { x: 810, y: y - 5 }, thickness: 0.5, color: rgb(0.86, 0.89, 0.92) });
    const values = [
      row.name.slice(0, 30), row.group, row.group === "Coord./Sup." ? "Base mensal" : `${row.evaluatedWeeks}/${row.eligibleWeeks}`,
      `-${brl(row.ruleDiscount)}`, brl(row.basePayment), brl(row.monitorPayment), brl(row.tenurePayment), brl(row.total),
    ];
    values.forEach((value, index) => page.drawText(value, { x: columns[index], y, font: index === 0 || index === 6 ? bold : regular, size: 8, color: rgb(0.07, 0.15, 0.23) }));
    y -= 20;
  }
  page.drawText("Documento gerado pelo sistema. Confira as pendencias antes do envio ao RH.", { x: 34, y: 22, font: regular, size: 7, color: rgb(0.38, 0.46, 0.54) });
  const bytes = await pdf.save();
  return new Response(Buffer.from(bytes), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="fechamento-${month}.pdf"`,
      "Cache-Control": "private, no-store",
    },
  });
}
