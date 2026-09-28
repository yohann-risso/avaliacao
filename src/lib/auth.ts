import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { pbkdf2Sync, randomBytes, timingSafeEqual } from "node:crypto";
import { jwtVerify, SignJWT } from "jose";

import { sql } from "@/lib/db";
import type { AppUser } from "@/lib/types";

const COOKIE_NAME = "avaliacao_session";
const PASSWORD_ITERATIONS = 600_000;
const COMMON_PASSWORDS = new Set(["12345678", "admin123", "password", "password123", "senha123", "senha1234"]);

function sessionKey(): Uint8Array {
  const secret = process.env.SESSION_SECRET;
  if (!secret || secret.length < 32) {
    throw new Error("SESSION_SECRET deve ter pelo menos 32 caracteres.");
  }
  return new TextEncoder().encode(secret);
}

export function normalizeUsername(value: string): string {
  const username = String(value || "").replace(/[\r\n]/g, "").trim().toLowerCase();
  if (username.length < 3) throw new Error("O usuário deve ter pelo menos 3 caracteres.");
  return username;
}

export function validatePassword(value: string): string {
  const password = String(value || "");
  if (password.length < 8) throw new Error("A senha deve ter pelo menos 8 caracteres.");
  if (COMMON_PASSWORDS.has(password.trim().toLowerCase())) throw new Error("Use uma senha menos previsível.");
  if (!/[A-Za-zÀ-ÿ]/.test(password) || !/\d/.test(password)) {
    throw new Error("A senha deve combinar letras e números.");
  }
  return password;
}

export function hashPassword(value: string): string {
  const password = validatePassword(value);
  const salt = randomBytes(16);
  const digest = pbkdf2Sync(password, salt, PASSWORD_ITERATIONS, 32, "sha256");
  return `pbkdf2_sha256$${PASSWORD_ITERATIONS}$${salt.toString("hex")}$${digest.toString("hex")}`;
}

export function verifyPassword(value: string, stored: string): boolean {
  try {
    const [algorithm, iterations, saltHex, digestHex] = String(stored || "").split("$");
    if (algorithm !== "pbkdf2_sha256") return false;
    const expected = Buffer.from(digestHex, "hex");
    const candidate = pbkdf2Sync(String(value || ""), Buffer.from(saltHex, "hex"), Number(iterations), expected.length, "sha256");
    return expected.length === candidate.length && timingSafeEqual(expected, candidate);
  } catch {
    return false;
  }
}

export async function createSession(userId: number): Promise<void> {
  const token = await new SignJWT({ userId })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("8h")
    .sign(sessionKey());
  const store = await cookies();
  store.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
}

export async function clearSession(): Promise<void> {
  (await cookies()).delete(COOKIE_NAME);
}

async function sessionUserId(): Promise<number | null> {
  const token = (await cookies()).get(COOKIE_NAME)?.value;
  if (!token) return null;
  try {
    const { payload } = await jwtVerify(token, sessionKey(), { algorithms: ["HS256"] });
    const userId = Number(payload.userId);
    return Number.isInteger(userId) && userId > 0 ? userId : null;
  } catch {
    return null;
  }
}

export const currentUser = cache(async (): Promise<AppUser | null> => {
  const userId = await sessionUserId();
  if (!userId) return null;
  const rows = await sql<AppUser[]>`
    select
      u.id,
      u.username,
      u.role,
      u.evaluator_employee_id,
      coalesce(e.name, '') as evaluator_name
    from login_users u
    left join employees e on e.id = u.evaluator_employee_id
    where u.id = ${userId} and u.active = 1
    limit 1
  `;
  return rows[0] ?? null;
});

export async function requireUser(): Promise<AppUser> {
  const user = await currentUser();
  if (!user) redirect("/login");
  return user;
}

export async function requireAdmin(): Promise<AppUser> {
  const user = await requireUser();
  if (user.role !== "admin") redirect("/avaliacoes");
  return user;
}
