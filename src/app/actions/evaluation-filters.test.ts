import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ sql: vi.fn(), redirect: vi.fn(), access: vi.fn() }));
vi.mock("@/lib/db", () => ({ sql: mocks.sql }));
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
vi.mock("next/navigation", () => ({ redirect: mocks.redirect }));
vi.mock("@/lib/auth", () => ({ requireEvaluationEditor: vi.fn().mockResolvedValue({ id: 1, role: "avaliador", evaluator_name: "Liderança" }) }));
vi.mock("@/lib/employee-access", () => ({ requireEmployeeAccess: mocks.access, requireEmployeesAccess: vi.fn() }));

import { saveWeeklyEvaluationAction } from "@/app/actions/evaluations";
import { WEEKLY_CRITERIA } from "@/lib/constants";

function evaluationForm() {
  const form = new FormData();
  form.set("week_start", "2026-10-12");
  form.set("employee_id", "42");
  form.set("items_count", "10");
  WEEKLY_CRITERIA.forEach(({ key }) => form.set(`${key}_pct`, "100"));
  return form;
}

describe("filtro após salvar avaliação", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.sql.mockResolvedValue([]);
    mocks.access.mockResolvedValue({ id: 42 });
    mocks.redirect.mockImplementation(() => { throw new Error("REDIRECT"); });
  });

  it("mantém a semana e o colaborador na URL que será usada no refresh", async () => {
    await expect(saveWeeklyEvaluationAction(evaluationForm())).rejects.toThrow("REDIRECT");
    const url = new URL(mocks.redirect.mock.calls[0][0], "https://example.test");
    expect(url.pathname).toBe("/avaliacoes");
    expect(url.searchParams.get("week")).toBe("2026-10-12");
    expect(url.searchParams.get("employee")).toBe("42");
    expect(url.searchParams.get("success")).toBe("Avaliação semanal salva.");
  });

  it("mantém a semana ao salvar e seguir para o próximo colaborador", async () => {
    const form = evaluationForm();
    form.set("next_employee_id", "43");
    await expect(saveWeeklyEvaluationAction(form)).rejects.toThrow("REDIRECT");
    const url = new URL(mocks.redirect.mock.calls[0][0], "https://example.test");
    expect(url.searchParams.get("week")).toBe("2026-10-12");
    expect(url.searchParams.get("employee")).toBe("43");
  });

  it("preserva o filtro também quando a gravação falha", async () => {
    mocks.sql.mockRejectedValueOnce(new Error("Falha ao gravar."));
    await expect(saveWeeklyEvaluationAction(evaluationForm())).rejects.toThrow("REDIRECT");
    const url = new URL(mocks.redirect.mock.calls[0][0], "https://example.test");
    expect(url.searchParams.get("week")).toBe("2026-10-12");
    expect(url.searchParams.get("employee")).toBe("42");
    expect(url.searchParams.get("error")).toBe("Falha ao gravar.");
  });
});
