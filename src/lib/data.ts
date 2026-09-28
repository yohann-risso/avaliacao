import "server-only";

import { sql } from "@/lib/db";
import { weeksForCompetencia } from "@/lib/dates";
import type { Employee, WeeklyError, WeeklyErrorWithEmployee, WeeklyEvaluation } from "@/lib/types";

export type LoginUserRow = {
  id: number;
  username: string;
  role: "admin" | "avaliador";
  active: number;
  evaluator_employee_id: number | null;
  evaluator_name: string;
  evaluator_sector: string;
  last_login_at: string;
  created_at: string;
  updated_at: string;
};

export async function loginUserCount(): Promise<number> {
  const [row] = await sql<{ count: number }[]>`select count(*)::int as count from login_users`;
  return row?.count ?? 0;
}

export async function listLoginUsers(): Promise<LoginUserRow[]> {
  return sql<LoginUserRow[]>`
    select
      u.id, u.username, u.role, u.active, u.evaluator_employee_id,
      coalesce(e.name, '') as evaluator_name,
      coalesce(e.sector, '') as evaluator_sector,
      u.last_login_at, u.created_at, u.updated_at
    from login_users u
    left join employees e on e.id = u.evaluator_employee_id
    order by u.active desc, lower(u.username)
  `;
}

export async function listEmployees(includeInactive = true): Promise<Employee[]> {
  const activeFilter = includeInactive ? sql`` : sql`where active = 1`;
  return sql<Employee[]>`
    select
      id, name, sector, role, hire_date, monitor_start_date, leadership_start_date,
      termination_date, is_monitor, is_leadership, active, created_at, updated_at
    from employees
    ${activeFilter}
    order by active desc, lower(name)
  `;
}

export async function listActiveEmployees(): Promise<Employee[]> {
  return listEmployees(false);
}

export async function getEmployee(employeeId: number): Promise<Employee | null> {
  const rows = await sql<Employee[]>`
    select
      id, name, sector, role, hire_date, monitor_start_date, leadership_start_date,
      termination_date, is_monitor, is_leadership, active, created_at, updated_at
    from employees
    where id = ${employeeId}
    limit 1
  `;
  return rows[0] ?? null;
}

export async function listEvaluators(): Promise<Employee[]> {
  return sql<Employee[]>`
    select
      id, name, sector, role, hire_date, monitor_start_date, leadership_start_date,
      termination_date, is_monitor, is_leadership, active, created_at, updated_at
    from employees
    where active = 1 and coalesce(is_leadership, 0) = 1
    order by lower(name)
  `;
}

export async function listWeeklyEvaluations(weeks: string[], employeeIds?: number[]): Promise<WeeklyEvaluation[]> {
  if (!weeks.length) return [];
  const employeeFilter = employeeIds?.length ? sql`and w.employee_id in ${sql(employeeIds)}` : sql``;
  return sql<WeeklyEvaluation[]>`
    select w.*, e.name as employee_name, e.sector, e.role
    from weekly_evaluations w
    join employees e on e.id = w.employee_id
    where trim(w.week_start) in ${sql(weeks)}
    ${employeeFilter}
    order by w.week_start desc, lower(e.name)
  `;
}

export async function getWeeklyEvaluation(employeeId: number, weekStart: string): Promise<WeeklyEvaluation | null> {
  const rows = await listWeeklyEvaluations([weekStart], [employeeId]);
  return rows[0] ?? null;
}

export async function listWeeklyErrors(employeeId: number, weekStart: string): Promise<WeeklyError[]> {
  return sql<WeeklyError[]>`
    select id, employee_id, week_start, role_snapshot, error_type, severity, qty,
      coalesce(notes, '') as notes, created_at
    from weekly_errors
    where employee_id = ${employeeId} and trim(week_start) = ${weekStart}
    order by created_at desc, id desc
  `;
}

export async function listWeeklyErrorsForWeeks(weeks: string[]): Promise<WeeklyError[]> {
  if (!weeks.length) return [];
  return sql<WeeklyError[]>`
    select id, employee_id, trim(week_start) as week_start, role_snapshot, error_type, severity,
      qty, coalesce(notes, '') as notes, created_at
    from weekly_errors
    where trim(week_start) in ${sql(weeks)}
    order by week_start, employee_id, id
  `;
}

export async function listOccurrenceRowsForWeeks(weeks: string[]): Promise<WeeklyErrorWithEmployee[]> {
  if (!weeks.length) return [];
  return sql<WeeklyErrorWithEmployee[]>`
    select
      w.id, w.employee_id, trim(w.week_start) as week_start, w.role_snapshot,
      w.error_type, w.severity, w.qty, coalesce(w.notes, '') as notes, w.created_at,
      e.name as employee_name, e.sector as employee_sector, e.role as employee_role
    from weekly_errors w
    join employees e on e.id = w.employee_id
    where trim(w.week_start) in ${sql(weeks)}
    order by w.week_start desc, w.created_at desc, w.id desc
  `;
}

export async function listRecentWeeklyEvaluations(employeeId: number, limit = 16): Promise<WeeklyEvaluation[]> {
  const safeLimit = Math.max(1, Math.min(52, Math.floor(limit)));
  return sql<WeeklyEvaluation[]>`
    select w.*, e.name as employee_name, e.sector, e.role
    from weekly_evaluations w
    join employees e on e.id = w.employee_id
    where w.employee_id = ${employeeId}
    order by trim(w.week_start) desc
    limit ${safeLimit}
  `;
}

export async function listRecentWeeklyErrors(employeeId: number, limit = 50): Promise<WeeklyError[]> {
  const safeLimit = Math.max(1, Math.min(200, Math.floor(limit)));
  return sql<WeeklyError[]>`
    select id, employee_id, trim(week_start) as week_start, role_snapshot, error_type,
      severity, qty, coalesce(notes, '') as notes, created_at
    from weekly_errors
    where employee_id = ${employeeId}
    order by trim(week_start) desc, created_at desc, id desc
    limit ${safeLimit}
  `;
}

export type DashboardStats = {
  activeEmployees: number;
  userCount: number;
  linkedUsers: number;
  leadershipCount: number;
  monitorCount: number;
  weeklyDone: number;
  weeklyExpected: number;
  issues: number;
};

export async function getDashboardStats(month: string): Promise<DashboardStats> {
  const weeks = weeksForCompetencia(month);
  const [peopleRows, userRows, weeklyRows] = await Promise.all([
    sql<{ active: number; evaluable: number; monitors: number; leadership: number }[]>`
      select
        count(*) filter (where active = 1)::int as active,
        count(*) filter (where active = 1 and coalesce(is_leadership, 0) = 0)::int as evaluable,
        count(*) filter (where active = 1 and is_monitor = 1 and coalesce(is_leadership, 0) = 0)::int as monitors,
        count(*) filter (where active = 1 and coalesce(is_leadership, 0) = 1)::int as leadership
      from employees
    `,
    sql<{ users: number; linked: number }[]>`
      select count(*)::int as users,
        count(*) filter (where evaluator_employee_id is not null)::int as linked
      from login_users
    `,
    sql<{ done: number }[]>`
      select count(*)::int as done from (
        select w.employee_id, trim(w.week_start)
        from weekly_evaluations w
        join employees e on e.id = w.employee_id
        where e.active = 1 and coalesce(e.is_leadership, 0) = 0
          and trim(w.week_start) in ${sql(weeks)}
        group by w.employee_id, trim(w.week_start)
      ) coverage
    `,
  ]);

  const people = peopleRows[0] ?? { active: 0, evaluable: 0, monitors: 0, leadership: 0 };
  const users = userRows[0] ?? { users: 0, linked: 0 };
  const weeklyExpected = people.evaluable * weeks.length;
  const weeklyDone = weeklyRows[0]?.done ?? 0;
  return {
    activeEmployees: people.active,
    userCount: users.users,
    linkedUsers: users.linked,
    leadershipCount: people.leadership,
    monitorCount: people.monitors,
    weeklyDone,
    weeklyExpected,
    issues: Math.max(0, weeklyExpected - weeklyDone),
  };
}
