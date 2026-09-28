import type { UserRole } from "@/lib/types";

export function isTeamScopedRole(role: UserRole): boolean {
  return role === "avaliador" || role === "supervisor";
}

export function canManagePeopleRole(role: UserRole): boolean {
  return role === "admin" || role === "supervisor";
}

export function userRoleLabel(role: UserRole): string {
  if (role === "admin") return "Administrador";
  if (role === "supervisor") return "Supervisor";
  return "Avaliador";
}
