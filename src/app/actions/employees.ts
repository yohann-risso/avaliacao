"use server";

import { revalidatePath } from "next/cache";

import { checkbox, integer, publicError, redirectWith, text } from "@/lib/action-utils";
import { requireAdmin } from "@/lib/auth";
import { todayBrazil } from "@/lib/dates";
import { sql } from "@/lib/db";

type EmployeePayload = {
  name: string;
  sector: string;
  role: string;
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
  if (payload.isMonitor && !payload.monitorStartDate) throw new Error("Informe a data de início como monitor.");
  if (payload.isLeadership && !payload.leadershipStartDate) throw new Error("Informe a data de início em coordenação/supervisão.");
  return payload;
}

export async function createEmployeeAction(formData: FormData): Promise<void> {
  const actor = await requireAdmin();
  try {
    const item = employeePayload(formData);
    const now = new Date().toISOString();
    const active = item.terminationDate && item.terminationDate <= todayBrazil() ? 0 : 1;
    await sql`
      insert into employees (
        name, sector, role, hire_date, monitor_start_date, leadership_start_date,
        termination_date, is_monitor,
        is_leadership, active, deactivated_at, created_at, created_by_user_id,
        created_by_username, updated_by_user_id, updated_by_username, updated_at
      ) values (
        ${item.name}, ${item.sector}, ${item.role}, ${item.hireDate},
        ${item.isMonitor ? item.monitorStartDate : ""},
        ${item.isLeadership ? item.leadershipStartDate : ""},
        ${item.terminationDate}, ${item.isMonitor ? 1 : 0}, ${item.isLeadership ? 1 : 0}, ${active},
        ${active ? "" : now}, ${now}, ${actor.id}, ${actor.username}, ${actor.id}, ${actor.username}, ${now}
      )
    `;
  } catch (error) {
    redirectWith("/funcionarios", "error", publicError(error));
  }
  revalidatePath("/funcionarios");
  redirectWith("/funcionarios", "success", "Funcionário cadastrado.");
}

export async function updateEmployeeAction(formData: FormData): Promise<void> {
  const actor = await requireAdmin();
  try {
    const id = integer(formData, "id");
    if (!id) throw new Error("Funcionário inválido.");
    const item = employeePayload(formData);
    const now = new Date().toISOString();
    const active = item.terminationDate && item.terminationDate <= todayBrazil() ? 0 : 1;
    await sql`
      update employees set
        name = ${item.name}, sector = ${item.sector}, role = ${item.role}, hire_date = ${item.hireDate},
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
  revalidatePath("/funcionarios");
  redirectWith("/funcionarios", "success", "Cadastro atualizado.");
}

export async function toggleEmployeeAction(formData: FormData): Promise<void> {
  const actor = await requireAdmin();
  try {
    const id = integer(formData, "id");
    const nextActive = integer(formData, "active") === 1;
    if (!id) throw new Error("Funcionário inválido.");
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
  revalidatePath("/funcionarios");
  redirectWith("/funcionarios", "success", "Status atualizado.");
}
