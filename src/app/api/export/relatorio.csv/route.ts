import { requireAdmin } from "@/lib/auth";
import { currentMonth } from "@/lib/dates";
import { buildMonthlyReport } from "@/lib/report";

export const dynamic = "force-dynamic";

function csvCell(value: unknown): string {
  const text = String(value ?? "").replace(/"/g, '""');
  return `"${text}"`;
}

export async function GET(request: Request) {
  await requireAdmin();
  const requested = new URL(request.url).searchParams.get("month") || "";
  const month = /^\d{4}-\d{2}$/.test(requested) ? requested : currentMonth();
  const report = await buildMonthlyReport(month);
  const header = ["Funcionário", "Setor", "Função", "Grupo", "Semanas elegíveis", "Semanas avaliadas", "Ocorrências", "Pontos de regra", "Desconto de regras (R$)", "Impacto das regras", "Média (%)", "Base (R$)", "Monitoria fixa (R$)", "Tempo (R$)", "Total (R$)", "Status"];
  const lines = [header, ...report.rows.map((row) => [
    row.name, row.sector, row.role, row.group, row.eligibleWeeks, row.evaluatedWeeks, row.errors,
    row.rulePoints.toFixed(2), row.ruleDiscount.toFixed(2), row.ruleImpact,
    row.average?.toFixed(2) || "", row.basePayment.toFixed(2), row.monitorPayment.toFixed(2),
    row.tenurePayment.toFixed(2), row.total.toFixed(2), row.status,
  ])].map((line) => line.map(csvCell).join(";"));
  return new Response(`\uFEFF${lines.join("\r\n")}`, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="fechamento-${month}.csv"`,
      "Cache-Control": "private, no-store",
    },
  });
}
