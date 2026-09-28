"use server";

import { revalidatePath } from "next/cache";

import { checkbox, integer, publicError, redirectWith, text } from "@/lib/action-utils";
import { requireAdmin, requirePeopleManager } from "@/lib/auth";
import { todayBrazil } from "@/lib/dates";
import { sql } from "@/lib/db";
import { requireEvaluatorManagementAccess, requireManagedEmployeeAccess } from "@/lib/employee-access";
import type { AppUser } from "@/lib/types";

type EmployeePayload = {
  name: string;
  sector: string;
  role: string;
  evaluatorEmployeeId: number | null;
  hireDate: string;
  monitorStartDate: string;
  leadershipStartDate: string;
  terminationDate: string;
  isMonitor: boolean;
  isLeadership: boolean;
};

function employeePayload(formData: FormData): EmployeePayload {
  const payload = {
    name: text(formData, "name"),
    sector: text(formData, "sector"),
    role: text(formData, "role"),
    evaluatorEmployeeId: integer(formData, "evaluator_employee_id") || null,
    hireDate: text(formData, "hire_date"),
    monitorStartDate: text(formData, "monitor_start_date"),
    leadershipStartDate: text(formData, "leadership_start_date"),
    terminationDate: text(formData, "termination_date"),
    isMonitor: checkbox(formData, "is_monitor"),
    isLeadership: checkbox(formData, "is_leadership"),
  };
  if (!payload.name || !payload.sector || !payload.role || !payload.hireDate) {
    throw new Error("Nome, setor, função e contratação são obrigatórios.");
  }
  if (payload.isLeadership && payload.isMonitor) throw new Error("Coordenação/supervisão não pode ser marcada como monitor.");
  if (!payload.isLeadership && !payload.evaluatorEmployeeId) throw new Error("Selecione o avaliador responsável pelo funcionário.");
  if (payload.isMonitor && !payload.monitorStartDate) throw new Error("Informe a data de início como monitor.");
  if (payload.isLeadership && !payload.leadershipStartDate) throw new Error("Informe a data de início em coordenação/supervisão.");
  return payload;
}

async function validateEvaluatorLink(user: AppUser, employeeId: number | undefined, evaluatorEmployeeId: number): Promise<number> {
  if (employeeId && evaluatorEmployeeId === employeeId) {
    throw new Error("Uma liderança não pode ser vinculada a ela mesma.");
  }
  const validatedId = await requireEvaluatorManagementAccess(user, evaluatorEmployeeId);
  if (employeeId) {
    const cycle = await sql<{ id: number }[]>`
      with recursive descendants(id) as (
        select id from employees where evaluator_employee_id = ${employeeId}
        union
        select child.id
        from employees child
        join descendants parent on child.evaluator_employee_id = parent.id
      )
      select id from descendants where id = ${evaluatorEmployeeId} limit 1
    `;
    if (cycle[0]) throw new Error("Esse vínculo criaria um ciclo na hierarquia de avaliadores.");
  }
  return validatedId;
}

async function validatedEvaluatorId(user: AppUser, item: EmployeePayload, employeeId?: number): Promise<number | null> {
  if (employeeId && !item.isLeadership) {
    const subordinates = await sql<{ id: number }[]>`
      select id from employees where evaluator_employee_id = ${employeeId} limit 1
    `;
    if (subordinates[0]) throw new Error("Reatribua a equipe antes de remover o perfil de coordenação/supervisão.");
  }
  if (!item.evaluatorEmployeeId) return null;
  return validateEvaluatorLink(user, employeeId, item.evaluatorEmployeeId);
}

function revalidateEmployeeScopePaths(): void {
  for (const path of ["/funcionarios", "/funcionarios/vinculos", "/avaliacoes", "/visao-geral", "/ocorrencias", "/monitoria"]) {
    revalidatePath(path);
  }
}

export async function createEmployeeAction(formData: FormData): Promise<void> {
  const actor = await requirePeopleManager();
  try {
    const item = employeePayload(formData);
    if (actor.role === "supervisor" && !item.evaluatorEmployeeId) {
      throw new Error("Selecione uma liderança responsável da sua equipe.");
    }
    const evaluatorEmployeeId = await validatedEvaluatorId(actor, item);
    const now = new Date().toISOString();
    const active = item.terminationDate && item.terminationDate <= todayBrazil() ? 0 : 1;
    await sql`
      insert into employees (
        name, sector, role, evaluator_employee_id, hire_date, monitor_start_date, leadership_start_date,
        termination_date, is_monitor,
        is_leadership, active, deactivated_at, created_at, created_by_user_id,
        created_by_username, updated_by_user_id, updated_by_username, updated_at
      ) values (
        ${item.name}, ${item.sector}, ${item.role}, ${evaluatorEmployeeId}, ${item.hireDate},
        ${item.isMonitor ? item.monitorStartDate : ""},
        ${item.isLeadership ? item.leadershipStartDate : ""},
        ${item.terminationDate}, ${item.isMonitor ? 1 : 0}, ${item.isLeadership ? 1 : 0}, ${active},
        ${active ? "" : now}, ${now}, ${actor.id}, ${actor.username}, ${actor.id}, ${actor.username}, ${now}
      )
    `;
  } catch (error) {
    redirectWith("/funcionarios", "error", publicError(error));
  }
  revalidateEmployeeScopePaths();
  redirectWith("/funcionarios", "success", "Funcionário cadastrado.");
}

export async function updateEmployeeAction(formData: FormData): Promise<void> {
  const actor = await requirePeopleManager();
  try {
    const id = integer(formData, "id");
    if (!id) throw new Error("Funcionário inválido.");
    await requireManagedEmployeeAccess(actor, id);
    const item = employeePayload(formData);
    if (actor.role === "supervisor" && !item.evaluatorEmployeeId) {
      throw new Error("Selecione uma liderança responsável da sua equipe.");
    }
    const evaluatorEmployeeId = await validatedEvaluatorId(actor, item, id);
    const now = new Date().toISOString();
    const active = item.terminationDate && item.terminationDate <= todayBrazil() ? 0 : 1;
    await sql`
      update employees set
        name = ${item.name}, sector = ${item.sector}, role = ${item.role},
        evaluator_employee_id = ${evaluatorEmployeeId}, hire_date = ${item.hireDate},
        monitor_start_date = ${item.isMonitor ? item.monitorStartDate : ""},
        leadership_start_date = ${item.isLeadership ? item.leadershipStartDate : ""},
        termination_date = ${item.terminationDate}, is_monitor = ${item.isMonitor ? 1 : 0},
        is_leadership = ${item.isLeadership ? 1 : 0}, active = ${active},
        deactivated_at = ${active ? "" : now}, updated_by_user_id = ${actor.id},
        updated_by_username = ${actor.username}, updated_at = ${now}
      where id = ${id}
    `;
  } catch (error) {
    redirectWith("/funcionarios", "error", publicError(error));
  }
  revalidateEmployeeScopePaths();
  redirectWith("/funcionarios", "success", "Cadastro atualizado.");
}

export async function toggleEmployeeAction(formData: FormData): Promise<void> {
  const actor = await requirePeopleManager();
  try {
    const id = integer(formData, "id");
    const nextActive = integer(formData, "active") === 1;
    if (!id) throw new Error("Funcionário inválido.");
    await requireManagedEmployeeAccess(actor, id);
    if (!nextActive) {
      const subordinates = await sql<{ id: number }[]>`
        select id from employees where evaluator_employee_id = ${id} and active = 1 limit 1
      `;
      if (subordinates[0]) throw new Error("Reatribua a equipe antes de desativar esta liderança.");
    }
    const now = new Date().toISOString();
    await sql`
      update employees set active = ${nextActive ? 1 : 0},
        deactivated_at = ${nextActive ? "" : now},
        termination_date = ${nextActive ? "" : todayBrazil()},
        updated_by_user_id = ${actor.id}, updated_by_username = ${actor.username}, updated_at = ${now}
      where id = ${id}
    `;
  } catch (error) {
    redirectWith("/funcionarios", "error", publicError(error));
  }
  revalidateEmployeeScopePaths();
  redirectWith("/funcionarios", "success", "Status atualizado.");
}

export async function saveEmployeeEvaluatorLinkAction(formData: FormData): Promise<void> {
  const actor = await requirePeopleManager();
  try {
    const employeeId = integer(formData, "employee_id");
    const evaluatorEmployeeId = integer(formData, "evaluator_employee_id");
    if (!employeeId || !evaluatorEmployeeId) throw new Error("Selecione a pessoa e o responsável pelo vínculo.");
    const employees = await sql<{ id: number }[]>`
      select id from employees where id = ${employeeId} and active = 1 limit 1
    `;
    if (!employees[0]) throw new Error("A pessoa selecionada está inativa ou não existe.");
    if (actor.role === "supervisor") await requireManagedEmployeeAccess(actor, employeeId);
    const validatedId = await validateEvaluatorLink(actor, employeeId, evaluatorEmployeeId);
    await sql`
      update employees set evaluator_employee_id = ${validatedId},
        updated_by_user_id = ${actor.id}, updated_by_username = ${actor.username},
        updated_at = ${new Date().toISOString()}
      where id = ${employeeId}
    `;
  } catch (error) {
    redirectWith("/funcionarios/vinculos", "error", publicError(error));
  }
  revalidateEmployeeScopePaths();
  redirectWith("/funcionarios/vinculos", "success", "Vínculo salvo.");
}

export async function deleteEmployeeEvaluatorLinkAction(formData: FormData): Promise<void> {
  const actor = await requireAdmin();
  try {
    const employeeId = integer(formData, "employee_id");
    if (!employeeId) throw new Error("Vínculo inválido.");
    await sql`
      update employees set evaluator_employee_id = null,
        updated_by_user_id = ${actor.id}, updated_by_username = ${actor.username},
        updated_at = ${new Date().toISOString()}
      where id = ${employeeId}
    `;
  } catch (error) {
    redirectWith("/funcionarios/vinculos", "error", publicError(error));
  }
  revalidateEmployeeScopePaths();
  redirectWith("/funcionarios/vinculos", "success", "Vínculo removido.");
}
