import { requireAdmin } from "@/lib/auth";
import { currentMonth } from "@/lib/dates";
import { buildReportCsv } from "@/lib/report-export";
import { filterReportRows, normalizeSectorSelection } from "@/lib/report-selection";
import { buildMonthlyReport } from "@/lib/report";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  await requireAdmin();
  const searchParams = new URL(request.url).searchParams;
  const requested = searchParams.get("month") || "";
  const month = /^\d{4}-\d{2}$/.test(requested) ? requested : currentMonth();
  const includeInactive = searchParams.get("inactive") === "1";
  const report = await buildMonthlyReport(month, { includeInactive });
  const sectors = normalizeSectorSelection(searchParams.getAll("sector"));
  const rows = filterReportRows(report.rows, sectors, searchParams.get("q") || "");
  return new Response(buildReportCsv(rows), {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="fechamento-${month}.csv"`,
      "Cache-Control": "private, no-store",
    },
  });
}
