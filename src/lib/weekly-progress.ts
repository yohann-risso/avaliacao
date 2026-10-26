import { employeesEligibleForWeek } from "@/lib/employee-scope";
import type { Employee, WeeklyEvaluation } from "@/lib/types";

export type WeeklyProgress = { completed: number; total: number; percent: number };

export function weeklyProgress(
  weeks: string[],
  employees: Employee[],
  evaluations: Pick<WeeklyEvaluation, "employee_id" | "week_start">[],
): Record<string, WeeklyProgress> {
  return Object.fromEntries(weeks.map((week) => {
    const eligibleIds = new Set(employeesEligibleForWeek(employees, week).map((employee) => employee.id));
    const completed = new Set(evaluations
      .filter((evaluation) => evaluation.week_start.trim() === week && eligibleIds.has(evaluation.employee_id))
      .map((evaluation) => evaluation.employee_id)).size;
    const total = eligibleIds.size;
    return [week, { completed, total, percent: total ? Math.round(completed / total * 100) : 0 }];
  }));
}
