import { requireReportViewer } from "@/lib/auth";
import { getEmployee, listBonusAdjustmentsForWeeks, listWeeklyErrorsForWeeks, listWeeklyEvaluations } from "@/lib/data";
import { weeksForCompetencia } from "@/lib/dates";
import { requireEmployeeReportAccess } from "@/lib/employee-access";
import { buildEmployeeReportPdf } from "@/lib/employee-report-pdf";
import { buildMonthlyReport } from "@/lib/report";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const user = await requireReportViewer();
  const params = new URL(request.url).searchParams;
  const employeeId = Number(params.get("employee"));
  const month = params.get("month") || "";
  if (!Number.isSafeInteger(employeeId) || employeeId < 1 || !/^\d{4}-(0[1-9]|1[0-2])$/.test(month)) {
    return Response.json({ error: "Colaborador ou fechamento inválido." }, { status: 400 });
  }
  try {
    await requireEmployeeReportAccess(user, employeeId);
  } catch {
    return Response.json({ error: "Colaborador indisponível para seu perfil." }, { status: 403 });
  }
  const employee = await getEmployee(employeeId);
  if (!employee) return Response.json({ error: "Colaborador não encontrado." }, { status: 404 });
  const weeks = weeksForCompetencia(month);
  const [evaluations, occurrences, adjustments, report] = await Promise.all([
    listWeeklyEvaluations(weeks, [employeeId]),
    listWeeklyErrorsForWeeks(weeks, [employeeId]),
    listBonusAdjustmentsForWeeks(weeks, [employeeId]),
    buildMonthlyReport(month, user, { includeInactive: true }),
  ]);
  const bytes = await buildEmployeeReportPdf({ month, employee, weeks, evaluations, occurrences, adjustments, summary: report.rows.find((row) => row.employeeId === employeeId) });
  return new Response(Buffer.from(bytes), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="colaborador-${employeeId}-fechamento-${month}.pdf"`,
      "Cache-Control": "private, no-store",
    },
  });
}
