"use server";

import { revalidatePath } from "next/cache";

import { checkbox, integer, publicError, raw, redirectWith, text } from "@/lib/action-utils";
import { hashPassword, normalizeUsername, requireAdmin } from "@/lib/auth";
import { sql } from "@/lib/db";
import type { UserRole } from "@/lib/types";

function userRole(formData: FormData): UserRole {
  const value = text(formData, "role");
  if (value !== "admin" && value !== "rh" && value !== "supervisor" && value !== "avaliador") {
    throw new Error("Perfil de acesso inválido.");
  }
  return value;
}

async function evaluatorId(formData: FormData): Promise<number | null> {
  const value = integer(formData, "evaluator_employee_id");
  if (!value) return null;
  const rows = await sql<{ id: number }[]>`
    select id from employees where id = ${value} and active = 1 and coalesce(is_leadership, 0) = 1 limit 1
  `;
  if (!rows[0]) throw new Error("Selecione um avaliador ativo de coordenação/supervisão.");
  return value;
}

export async function createUserAction(formData: FormData): Promise<void> {
  await requireAdmin();
  try {
    const username = normalizeUsername(text(formData, "username"));
    const role = userRole(formData);
    const passwordHash = hashPassword(raw(formData, "password"));
    const evaluator = role === "admin" || role === "rh" ? null : await evaluatorId(formData);
    if (role !== "admin" && role !== "rh" && !evaluator) throw new Error("Vincule o usuário a uma liderança ativa.");
    const now = new Date().toISOString();
    await sql`
      insert into login_users (username, password_hash, role, evaluator_employee_id, active, created_at, updated_at)
      values (${username}, ${passwordHash}, ${role}, ${evaluator}, 1, ${now}, ${now})
    `;
  } catch (error) {
    redirectWith("/usuarios", "error", publicError(error));
  }
  revalidatePath("/usuarios");
  redirectWith("/usuarios", "success", "Usuário cadastrado.");
}

export async function updateUserAction(formData: FormData): Promise<void> {
  const actor = await requireAdmin();
  try {
    const id = integer(formData, "id");
    if (!id) throw new Error("Usuário inválido.");
    const username = normalizeUsername(text(formData, "username"));
    const role = userRole(formData);
    const active = checkbox(formData, "active");
    if (id === actor.id && !active) throw new Error("Você não pode desativar o próprio acesso.");
    const evaluator = role === "admin" || role === "rh" ? null : await evaluatorId(formData);
    if (role !== "admin" && role !== "rh" && !evaluator) throw new Error("Vincule o usuário a uma liderança ativa.");
    const password = raw(formData, "password");
    const now = new Date().toISOString();
    if (password) {
      await sql`
        update login_users set username = ${username}, password_hash = ${hashPassword(password)},
          role = ${role}, evaluator_employee_id = ${evaluator}, active = ${active ? 1 : 0}, updated_at = ${now}
        where id = ${id}
      `;
    } else {
      await sql`
        update login_users set username = ${username}, role = ${role}, evaluator_employee_id = ${evaluator},
          active = ${active ? 1 : 0}, updated_at = ${now}
        where id = ${id}
      `;
    }
  } catch (error) {
    redirectWith("/usuarios", "error", publicError(error));
  }
  revalidatePath("/usuarios");
  redirectWith("/usuarios", "success", "Usuário atualizado.");
}
