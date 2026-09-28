import type { AppUser, Employee } from "@/lib/types";

function leadershipIdsVisibleTo(user: AppUser, employees: Employee[]): Set<number> {
  if (!user.evaluator_employee_id || !user.evaluator_name) return new Set();
  const leadershipIds = new Set([user.evaluator_employee_id]);
  let foundDescendant = true;
  while (foundDescendant) {
    foundDescendant = false;
    for (const employee of employees) {
      if (
        employee.is_leadership
        && employee.evaluator_employee_id
        && leadershipIds.has(employee.evaluator_employee_id)
        && !leadershipIds.has(employee.id)
      ) {
        leadershipIds.add(employee.id);
        foundDescendant = true;
      }
    }
  }
  return leadershipIds;
}

export function employeesVisibleTo(user: AppUser, employees: Employee[]): Employee[] {
  if (user.role === "admin") return employees;
  const leadershipIds = leadershipIdsVisibleTo(user, employees);
  return employees.filter((employee) => (
    employee.id !== user.evaluator_employee_id
    && employee.evaluator_employee_id !== null
    && leadershipIds.has(employee.evaluator_employee_id)
  ));
}

export function evaluatorsVisibleTo(user: AppUser, employees: Employee[]): Employee[] {
  const evaluators = employees.filter((employee) => employee.active && employee.is_leadership);
  if (user.role === "admin") return evaluators;
  const leadershipIds = leadershipIdsVisibleTo(user, employees);
  return evaluators.filter((employee) => leadershipIds.has(employee.id));
}
