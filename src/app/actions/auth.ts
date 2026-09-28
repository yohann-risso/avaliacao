"use server";

import { redirect } from "next/navigation";

import { createSession, clearSession, hashPassword, normalizeUsername, verifyPassword } from "@/lib/auth";
import { sql } from "@/lib/db";
import { loginUserCount } from "@/lib/data";
import { publicError, raw, text } from "@/lib/action-utils";

export type AuthState = { error: string };

export async function loginAction(_state: AuthState, formData: FormData): Promise<AuthState> {
  const destination = "/visao-geral";
  try {
    const username = normalizeUsername(text(formData, "username"));
    const password = raw(formData, "password");
    const rows = await sql<{
      id: number;
      password_hash: string;
      role: "admin" | "avaliador";
      active: number;
    }[]>`
      select id, password_hash, role, active
      from login_users
      where lower(username) = ${username}
      limit 1
    `;
    const user = rows[0];
    if (!user || user.active !== 1 || !verifyPassword(password, user.password_hash)) {
      return { error: "Usuário ou senha inválidos." };
    }
    await sql`update login_users set last_login_at = ${new Date().toISOString()} where id = ${user.id}`;
    await createSession(user.id);
  } catch (error) {
    return { error: publicError(error) };
  }
  redirect(destination);
}

export async function createInitialAdminAction(_state: AuthState, formData: FormData): Promise<AuthState> {
  try {
    const username = normalizeUsername(text(formData, "username"));
    const password = raw(formData, "password");
    const confirmation = raw(formData, "password_confirmation");
    if (password !== confirmation) return { error: "As senhas não coincidem." };
    if ((await loginUserCount()) > 0) return { error: "O administrador inicial já foi criado." };
    const rows = await sql<{ id: number }[]>`
      insert into login_users (username, password_hash, role, active, created_at, updated_at)
      values (${username}, ${hashPassword(password)}, 'admin', 1, ${new Date().toISOString()}, ${new Date().toISOString()})
      returning id
    `;
    await createSession(rows[0].id);
  } catch (error) {
    return { error: publicError(error) };
  }
  redirect("/visao-geral");
}

export async function logoutAction(): Promise<void> {
  await clearSession();
  redirect("/login");
}
