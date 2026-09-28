import "server-only";

import { MONITOR_FIXED_VALUE, WEEKLY_CRITERIA } from "@/lib/constants";
import { eligibleWeeks, isWeekAfterStart, monthReferenceDate, weeksForCompetencia } from "@/lib/dates";
import { listBonusAdjustmentsForWeeks, listEmployees, listWeeklyErrorsForWeeks, listWeeklyEvaluations } from "@/lib/data";
import { financialAdjustmentTotal, monthlyBasePayment, monitorPayment, tenurePayment, totalAfterFinancialAdjustments } from "@/lib/money";

export type ReportRow = {
  employeeId: number;
  name: string;
  sector: string;
  role: string;
  group: "Operação" | "Coord./Sup.";
  eligibleWeeks: number;
  evaluatedWeeks: number;
  missingWeeks: number;
  errors: number;
  rulePoints: number;
  ruleDiscount: number;
  ruleImpact: string;
  average: number | null;
  basePayment: number;
  monitorPayment: number;
  tenurePayment: number;
  adjustmentTotal: number;
  total: number;
  status: "OK" | "Pendente";
};

export type MonthlyReport = {
  month: string;
  weeks: string[];
  rows: ReportRow[];
  total: number;
  pending: number;
  coverage: number;
  weeklyExpected: number;
  weeklyDone: number;
};

export async function buildMonthlyReport(month: string): Promise<MonthlyReport> {
  const weeks = weeksForCompetencia(month);
  const [employees, weekly, errors, adjustments] = await Promise.all([
    listEmployees(true),
    listWeeklyEvaluations(weeks),
    listWeeklyErrorsForWeeks(weeks),
    listBonusAdjustmentsForWeeks(weeks),
  ]);
  const weeklyByEmployee = new Map<number, typeof weekly>();
  for (const item of weekly) {
    const current = weeklyByEmployee.get(item.employee_id) || [];
    current.push(item);
    weeklyByEmployee.set(item.employee_id, current);
  }
  const errorsByEmployeeRows = new Map<number, typeof errors>();
  const errorsByEmployee = new Map<number, number>();
  for (const item of errors) {
    errorsByEmployee.set(item.employee_id, (errorsByEmployee.get(item.employee_id) || 0) + Number(item.qty || 0));
    const current = errorsByEmployeeRows.get(item.employee_id) || [];
    current.push(item);
    errorsByEmployeeRows.set(item.employee_id, current);
  }
  const adjustmentsByEmployee = new Map<number, typeof adjustments>();
  for (const item of adjustments) {
    const current = adjustmentsByEmployee.get(item.employee_id) || [];
    current.push(item);
    adjustmentsByEmployee.set(item.employee_id, current);
  }

  const rows: ReportRow[] = [];
  for (const employee of employees) {
    const validWeeks = eligibleWeeks(employee.hire_date, employee.termination_date, weeks);
    if (!validWeeks.length) continue;
    const leadershipWeeks = employee.is_leadership
      ? validWeeks.filter((week) => isWeekAfterStart(employee.leadership_start_date, week))
      : [];
    const isLeadership = leadershipWeeks.length > 0;
    const employeeWeekly = (weeklyByEmployee.get(employee.id) || []).filter((item) => validWeeks.includes(String(item.week_start).trim()));
    const monitorEligible = Boolean(
      employee.is_monitor && !isLeadership && validWeeks.some((week) => isWeekAfterStart(employee.monitor_start_date, week)),
    );
    const employeeErrors = (errorsByEmployeeRows.get(employee.id) || []).filter((item) => validWeeks.includes(String(item.week_start).trim()));
    const baseBreakdown = isLeadership
      ? { total: 550, discount: 0, points: 0, blocksMonthlyBase: false, assiduidadeDiscount: 0 }
      : monthlyBasePayment(employeeWeekly, employeeErrors);
    const basePayment = baseBreakdown.total;
    const additionalMonitor = monitorPayment(monitorEligible);
    const tenure = tenurePayment(employee.hire_date, month);
    const employeeAdjustments = (adjustmentsByEmployee.get(employee.id) || []).filter((item) => validWeeks.includes(String(item.week_start).trim()));
    const adjustmentTotal = financialAdjustmentTotal(employeeAdjustments);
    const percentages = employeeWeekly.flatMap((item) => WEEKLY_CRITERIA.map((criterion) => Number(item[`${criterion.key}_pct`] || 0)));
    const missingWeeks = isLeadership ? 0 : Math.max(0, validWeeks.length - new Set(employeeWeekly.map((item) => String(item.week_start).trim())).size);
    const status = missingWeeks ? "Pendente" : "OK";
    const ruleImpact = baseBreakdown.blocksMonthlyBase
      ? "Bônus-base mensal bloqueado por reincidência A01"
      : baseBreakdown.assiduidadeDiscount
        ? `Assiduidade mensal: -${baseBreakdown.assiduidadeDiscount}%`
        : baseBreakdown.discount > 0 ? "Descontos semanais aplicados" : "Sem desconto por ocorrência";
    rows.push({
      employeeId: employee.id,
      name: employee.name,
      sector: employee.sector,
      role: employee.role,
      group: isLeadership ? "Coord./Sup." : "Operação",
      eligibleWeeks: isLeadership ? leadershipWeeks.length : validWeeks.length,
      evaluatedWeeks: isLeadership ? 0 : employeeWeekly.length,
      missingWeeks,
      errors: errorsByEmployee.get(employee.id) || 0,
      rulePoints: baseBreakdown.points,
      ruleDiscount: baseBreakdown.discount,
      ruleImpact,
      average: percentages.length ? percentages.reduce((sum, value) => sum + value, 0) / percentages.length : null,
      basePayment,
      monitorPayment: additionalMonitor,
      tenurePayment: tenure,
      adjustmentTotal,
      total: totalAfterFinancialAdjustments(basePayment + additionalMonitor + tenure, employeeAdjustments),
      status,
    });
  }
  rows.sort((left, right) => right.total - left.total || left.name.localeCompare(right.name, "pt-BR"));
  const operation = rows.filter((row) => row.group === "Operação");
  const weeklyExpected = operation.reduce((sum, row) => sum + row.eligibleWeeks, 0);
  const weeklyDone = operation.reduce((sum, row) => sum + row.evaluatedWeeks, 0);
  return {
    month,
    weeks,
    rows,
    total: rows.reduce((sum, row) => sum + row.total, 0),
    pending: rows.filter((row) => row.status === "Pendente").length,
    coverage: weeklyExpected ? (weeklyDone / weeklyExpected) * 100 : 0,
    weeklyExpected,
    weeklyDone,
  };
}

export function reportCriterionMax(): number {
  return WEEKLY_CRITERIA.reduce((sum, item) => sum + item.monthlyCap, 0) + MONITOR_FIXED_VALUE;
}

export function reportReferenceDate(month: string): string {
  return monthReferenceDate(month).toISOString().slice(0, 10);
}
