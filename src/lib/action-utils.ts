import { redirect } from "next/navigation";

export function text(formData: FormData, name: string): string {
  return String(formData.get(name) || "").trim();
}

export function raw(formData: FormData, name: string): string {
  return String(formData.get(name) || "");
}

export function integer(formData: FormData, name: string, fallback = 0): number {
  const value = Number(text(formData, name));
  return Number.isInteger(value) ? value : fallback;
}

export function checkbox(formData: FormData, name: string): boolean {
  return formData.get(name) === "on" || formData.get(name) === "1" || formData.get(name) === "true";
}

export function percentage(formData: FormData, name: string): number {
  const value = Number(text(formData, name));
  if (!Number.isFinite(value) || value < 0 || value > 100) throw new Error(`${name}: informe um valor entre 0 e 100.`);
  return value;
}

export function publicError(error: unknown): string {
  if (error instanceof Error) {
    const message = error.message.replace(/postgres(?:ql)?:\/\/[^\s]+/gi, "[CONEXÃO OCULTA]");
    if (message.includes("duplicate key") || message.includes("idx_login_users_username")) return "Registro já cadastrado.";
    if (message.length <= 220) return message;
  }
  return "Não foi possível concluir a operação. Tente novamente.";
}

export function redirectWith(path: string, kind: "success" | "error", message: string): never {
  const params = new URLSearchParams({ [kind]: message });
  redirect(`${path}?${params.toString()}`);
}
