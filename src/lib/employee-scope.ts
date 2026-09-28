import type { AppUser, Employee } from "@/lib/types";

export function employeesVisibleTo(user: AppUser, employees: Employee[]): Employee[] {
  if (user.role === "admin") return employees;
  if (!user.evaluator_employee_id || !user.evaluator_name) return [];

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

  return employees.filter((employee) => (
    employee.id !== user.evaluator_employee_id
    && employee.evaluator_employee_id !== null
    && leadershipIds.has(employee.evaluator_employee_id)
  ));
}
