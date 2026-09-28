import "server-only";

import { sql } from "@/lib/db";
import { canManagePeopleRole, isTeamScopedRole } from "@/lib/permissions";
import type { AppUser } from "@/lib/types";

export { employeesVisibleTo, evaluatorsVisibleTo } from "@/lib/employee-scope";

function evaluatorHierarchyFilter(evaluatorEmployeeId: number) {
  return sql`
    and evaluator_employee_id in (
      with recursive evaluator_tree(id) as (
        select id
        from employees
        where id = ${evaluatorEmployeeId}
          and active = 1
          and coalesce(is_leadership, 0) = 1
        union
        select child.id
        from employees child
        join evaluator_tree parent on child.evaluator_employee_id = parent.id
        where child.active = 1
          and coalesce(child.is_leadership, 0) = 1
      )
      select id from evaluator_tree
    )
  `;
}

function evaluatorIdHierarchyFilter(evaluatorEmployeeId: number) {
  return sql`
    and id in (
      with recursive evaluator_tree(id) as (
        select id
        from employees
        where id = ${evaluatorEmployeeId}
          and active = 1
          and coalesce(is_leadership, 0) = 1
        union
        select child.id
        from employees child
        join evaluator_tree parent on child.evaluator_employee_id = parent.id
        where child.active = 1
          and coalesce(child.is_leadership, 0) = 1
      )
      select id from evaluator_tree
    )
  `;
}

function assertActiveEvaluatorLink(user: AppUser): void {
  if (isTeamScopedRole(user.role) && (!user.evaluator_employee_id || !user.evaluator_name)) {
    throw new Error("Seu usuário não está vinculado a uma liderança ativa.");
  }
}

export async function requireEmployeeAccess(
  user: AppUser,
  employeeId: number,
): Promise<{ id: number; role: string }> {
  assertActiveEvaluatorLink(user);
  const evaluatorFilter = isTeamScopedRole(user.role)
    ? evaluatorHierarchyFilter(Number(user.evaluator_employee_id))
    : sql``;
  const rows = await sql<{ id: number; role: string }[]>`
    select id, role
    from employees
    where id = ${employeeId}
      and active = 1
      and coalesce(is_leadership, 0) = 0
      ${evaluatorFilter}
    limit 1
  `;
  if (!rows[0]) throw new Error("Funcionário inativo, não avaliável ou não vinculado ao seu avaliador.");
  return rows[0];
}

export async function requireEmployeesAccess(user: AppUser, employeeIds: number[]): Promise<void> {
  if (!employeeIds.length) return;
  assertActiveEvaluatorLink(user);
  const evaluatorFilter = isTeamScopedRole(user.role)
    ? evaluatorHierarchyFilter(Number(user.evaluator_employee_id))
    : sql``;
  const rows = await sql<{ id: number }[]>`
    select id
    from employees
    where id in ${sql(employeeIds)}
      and active = 1
      and coalesce(is_leadership, 0) = 0
      ${evaluatorFilter}
  `;
  const allowedIds = new Set(rows.map((row) => row.id));
  const invalidId = employeeIds.find((employeeId) => !allowedIds.has(employeeId));
  if (invalidId) throw new Error(`O funcionário #${invalidId} está inativo, não é avaliável ou não está vinculado ao seu avaliador.`);
}

export async function requireManagedEmployeeAccess(
  user: AppUser,
  employeeId: number,
): Promise<{ id: number; role: string }> {
  if (!canManagePeopleRole(user.role)) throw new Error("Seu perfil não permite gerenciar pessoas.");
  assertActiveEvaluatorLink(user);
  const evaluatorFilter = user.role === "supervisor"
    ? evaluatorHierarchyFilter(Number(user.evaluator_employee_id))
    : sql``;
  const rows = await sql<{ id: number; role: string }[]>`
    select id, role
    from employees
    where id = ${employeeId}
      ${evaluatorFilter}
    limit 1
  `;
  if (!rows[0]) throw new Error("A pessoa selecionada não pertence à sua equipe.");
  return rows[0];
}

export async function requireEvaluatorManagementAccess(user: AppUser, evaluatorEmployeeId: number): Promise<number> {
  if (!canManagePeopleRole(user.role)) throw new Error("Seu perfil não permite gerenciar pessoas.");
  assertActiveEvaluatorLink(user);
  const hierarchyFilter = user.role === "supervisor"
    ? evaluatorIdHierarchyFilter(Number(user.evaluator_employee_id))
    : sql``;
  const rows = await sql<{ id: number }[]>`
    select id
    from employees
    where id = ${evaluatorEmployeeId}
      and active = 1
      and coalesce(is_leadership, 0) = 1
      ${hierarchyFilter}
    limit 1
  `;
  if (!rows[0]) throw new Error("Selecione uma liderança ativa da sua equipe.");
  return rows[0].id;
}
