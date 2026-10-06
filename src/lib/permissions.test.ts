import { describe, expect, it } from "vitest";

import {
  canEditEvaluationsRole,
  canManageOrganizationRole,
  canManagePeopleRole,
  canViewReportsRole,
  isTeamScopedRole,
  userRoleLabel,
} from "@/lib/permissions";

describe("permissões por perfil", () => {
  it("permite gestão de pessoas para administrador, RH e supervisor", () => {
    expect(canManagePeopleRole("admin")).toBe(true);
    expect(canManagePeopleRole("rh")).toBe(true);
    expect(canManagePeopleRole("supervisor")).toBe(true);
    expect(canManagePeopleRole("avaliador")).toBe(false);
  });

  it("dá ao RH visão organizacional e relatórios, mas mantém avaliações somente para consulta", () => {
    expect(canManageOrganizationRole("admin")).toBe(true);
    expect(canManageOrganizationRole("rh")).toBe(true);
    expect(canManageOrganizationRole("supervisor")).toBe(false);
    expect(canManageOrganizationRole("avaliador")).toBe(false);
    expect(canViewReportsRole("admin")).toBe(true);
    expect(canViewReportsRole("rh")).toBe(true);
    expect(canViewReportsRole("supervisor")).toBe(false);
    expect(canViewReportsRole("avaliador")).toBe(false);
    expect(canEditEvaluationsRole("rh")).toBe(false);
    expect(canEditEvaluationsRole("admin")).toBe(true);
    expect(canEditEvaluationsRole("supervisor")).toBe(true);
    expect(canEditEvaluationsRole("avaliador")).toBe(true);
  });

  it("mantém avaliador e supervisor limitados à equipe vinculada", () => {
    expect(isTeamScopedRole("admin")).toBe(false);
    expect(isTeamScopedRole("rh")).toBe(false);
    expect(isTeamScopedRole("supervisor")).toBe(true);
    expect(isTeamScopedRole("avaliador")).toBe(true);
  });

  it("exibe os nomes dos quatro perfis", () => {
    expect(userRoleLabel("admin")).toBe("Administrador");
    expect(userRoleLabel("rh")).toBe("Recursos Humanos");
    expect(userRoleLabel("supervisor")).toBe("Supervisor");
    expect(userRoleLabel("avaliador")).toBe("Avaliador");
  });
});
