import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AppUser, Employee } from "@/lib/types";

vi.mock("server-only", () => ({}));

const dataMocks = vi.hoisted(() => ({
  listEmployees: vi.fn(),
  listWeeklyEvaluations: vi.fn(),
  listWeeklyErrorsForWeeks: vi.fn(),
  listBonusAdjustmentsForWeeks: vi.fn(),
}));

vi.mock("@/lib/data", () => dataMocks);

import { buildMonthlyReport } from "@/lib/report";

function employee(overrides: Partial<Employee>): Employee {
  return {
    id: 1,
    name: "Colaborador",
    sector: "Operação",
    role: "Auxiliar",
    evaluator_employee_id: 10,
    evaluator_name: "Coordenador",
    hire_date: "2020-01-01",
    monitor_start_date: "",
    leadership_start_date: "",
    termination_date: "",
    is_monitor: 0,
    is_leadership: 0,
    active: 1,
    created_at: "",
    updated_at: "",
    ...overrides,
  };
}

const evaluator: AppUser = {
  id: 7,
  username: "avaliador",
  role: "avaliador",
  evaluator_employee_id: 10,
  evaluator_name: "Coordenador",
};

describe("escopo do fechamento mensal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    dataMocks.listWeeklyEvaluations.mockResolvedValue([]);
    dataMocks.listWeeklyErrorsForWeeks.mockResolvedValue([]);
    dataMocks.listBonusAdjustmentsForWeeks.mockResolvedValue([]);
  });

  it.each(["avaliador", "supervisor"] as const)("carrega dados financeiros somente da equipe do perfil %s", async (role) => {
    dataMocks.listEmployees.mockResolvedValue([
      employee({ id: 10, name: "Coordenador", evaluator_employee_id: null, is_leadership: 1 }),
      employee({ id: 1, name: "Vinculado", evaluator_employee_id: 10 }),
      employee({ id: 20, name: "Outra liderança", evaluator_employee_id: null, is_leadership: 1 }),
      employee({ id: 2, name: "Fora da equipe", evaluator_employee_id: 20 }),
    ]);

    const report = await buildMonthlyReport("2026-10", { ...evaluator, role });

    expect(report.rows.map((row) => row.employeeId)).toEqual([1]);
    expect(dataMocks.listWeeklyEvaluations).toHaveBeenCalledWith(expect.any(Array), [1]);
    expect(dataMocks.listWeeklyErrorsForWeeks).toHaveBeenCalledWith(expect.any(Array), [1]);
    expect(dataMocks.listBonusAdjustmentsForWeeks).toHaveBeenCalledWith(expect.any(Array), [1]);
  });

  it.each(["avaliador", "supervisor"] as const)("não consulta outras equipes quando o perfil %s não tem vínculo ativo", async (role) => {
    dataMocks.listEmployees.mockResolvedValue([
      employee({ id: 1, name: "Sem acesso", evaluator_employee_id: 10 }),
    ]);

    const report = await buildMonthlyReport("2026-10", { ...evaluator, role, evaluator_name: "" });

    expect(report.rows).toEqual([]);
    expect(dataMocks.listWeeklyEvaluations).toHaveBeenCalledWith(expect.any(Array), []);
    expect(dataMocks.listWeeklyErrorsForWeeks).toHaveBeenCalledWith(expect.any(Array), []);
    expect(dataMocks.listBonusAdjustmentsForWeeks).toHaveBeenCalledWith(expect.any(Array), []);
  });
});
