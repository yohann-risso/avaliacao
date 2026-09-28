import { requireAdmin } from "@/lib/auth";
import { currentMonth } from "@/lib/dates";
import { buildExecutiveReportPdf } from "@/lib/report-export";
import { filterReportRows, normalizeSectorSelection } from "@/lib/report-selection";
import { buildMonthlyReport } from "@/lib/report";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  await requireAdmin();
  const searchParams = new URL(request.url).searchParams;
  const requested = searchParams.get("month") || "";
  const month = /^\d{4}-\d{2}$/.test(requested) ? requested : currentMonth();
  const report = await buildMonthlyReport(month);
  const sectors = normalizeSectorSelection(searchParams.getAll("sector"));
  const query = searchParams.get("q") || "";
  const rows = filterReportRows(report.rows, sectors, query);
  const bytes = await buildExecutiveReportPdf({ month, rows, sectors, query });
  return new Response(Buffer.from(bytes), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="fechamento-${month}.pdf"`,
      "Cache-Control": "private, no-store",
    },
  });
}
