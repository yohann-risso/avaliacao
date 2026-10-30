import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AppUser } from "@/lib/types";

const mocks = vi.hoisted(() => ({ sql: vi.fn(), queries: [] as string[], rows: [{ id: 42, role: "Auxiliar" }] }));
vi.mock("server-only", () => ({}));
vi.mock("@/lib/db", () => ({ sql: mocks.sql }));

import { requireEmployeeReportAccess, requireManagedEmployeeAccess } from "@/lib/employee-access";

function user(role: AppUser["role"] = "avaliador"): AppUser {
  return { id: 1, username: "usuario", role, evaluator_employee_id: 10, evaluator_name: "Liderança" };
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.queries.length = 0;
  mocks.rows = [{ id: 42, role: "Auxiliar" }];
  mocks.sql.mockImplementation((strings: TemplateStringsArray, ...values: unknown[]) => {
    const query = strings.reduce((result, part, index) => result + part + (values[index] ?? ""), "");
    if (/^\s*select id, role/.test(query)) {
      mocks.queries.push(query);
      return Promise.resolve(mocks.rows);
    }
    return query;
  });
});

describe("consulta individual para relatório", () => {
  it.each(["avaliador", "supervisor"] as const)("restringe %s à hierarquia da liderança vinculada", async (role) => {
    await expect(requireEmployeeReportAccess(user(role), 42)).resolves.toEqual({ id: 42, role: "Auxiliar" });
    expect(mocks.queries[0]).toContain("where id = 42");
    expect(mocks.queries[0]).toContain("and evaluator_employee_id in");
    expect(mocks.queries[0]).toContain("with recursive evaluator_tree");
    expect(mocks.queries[0]).toContain("where id = 10");
  });

  it.each(["admin", "rh"] as const)("preserva a consulta organizacional para %s", async (role) => {
    await requireEmployeeReportAccess(user(role), 42);
    expect(mocks.queries[0]).not.toContain("and evaluator_employee_id in");
  });

  it("nega relatório sem vínculo ativo antes de consultar dados", async () => {
    await expect(requireEmployeeReportAccess({ ...user(), evaluator_name: "" }, 42)).rejects.toThrow("liderança ativa");
    expect(mocks.sql).not.toHaveBeenCalled();
  });

  it("nega pessoas não retornadas pela consulta com escopo", async () => {
    mocks.rows = [];
    await expect(requireEmployeeReportAccess(user(), 99)).rejects.toThrow("não pertence à sua equipe");
  });

  it("mantém o avaliador sem permissão de gestão de pessoas", async () => {
    await expect(requireManagedEmployeeAccess(user(), 42)).rejects.toThrow("não permite gerenciar pessoas");
    expect(mocks.sql).not.toHaveBeenCalled();
  });
});
