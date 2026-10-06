import type { UserRole } from "@/lib/types";

export function isTeamScopedRole(role: UserRole): boolean {
  return role === "avaliador" || role === "supervisor";
}

export function canManagePeopleRole(role: UserRole): boolean {
  return role === "admin" || role === "rh" || role === "supervisor";
}

export function canManageOrganizationRole(role: UserRole): boolean {
  return role === "admin" || role === "rh";
}

export function canViewReportsRole(role: UserRole): boolean {
  return role === "admin" || role === "rh";
}

export function canEditEvaluationsRole(role: UserRole): boolean {
  return role === "admin" || role === "supervisor" || role === "avaliador";
}

export function userRoleLabel(role: UserRole): string {
  if (role === "admin") return "Administrador";
  if (role === "rh") return "Recursos Humanos";
  if (role === "supervisor") return "Supervisor";
  return "Avaliador";
}
