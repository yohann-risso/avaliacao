import { describe, expect, it } from "vitest";

import { canManagePeopleRole, isTeamScopedRole, userRoleLabel } from "@/lib/permissions";

describe("permissões por perfil", () => {
  it("permite gestão de pessoas para administrador e supervisor", () => {
    expect(canManagePeopleRole("admin")).toBe(true);
    expect(canManagePeopleRole("supervisor")).toBe(true);
    expect(canManagePeopleRole("avaliador")).toBe(false);
  });

  it("mantém avaliador e supervisor limitados à equipe vinculada", () => {
    expect(isTeamScopedRole("admin")).toBe(false);
    expect(isTeamScopedRole("supervisor")).toBe(true);
    expect(isTeamScopedRole("avaliador")).toBe(true);
  });

  it("exibe os nomes dos três perfis", () => {
    expect(userRoleLabel("admin")).toBe("Administrador");
    expect(userRoleLabel("supervisor")).toBe("Supervisor");
    expect(userRoleLabel("avaliador")).toBe("Avaliador");
  });
});
