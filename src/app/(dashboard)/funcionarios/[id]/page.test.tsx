import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ user: vi.fn(), access: vi.fn(), employee: vi.fn(), report: vi.fn(), list: vi.fn(), recent: vi.fn() }));
vi.mock("@/lib/auth", () => ({ requireReportViewer: mocks.user }));
vi.mock("@/lib/employee-access", () => ({ requireEmployeeReportAccess: mocks.access, evaluatorsVisibleTo: () => [] }));
vi.mock("@/lib/data", () => ({ getEmployee: mocks.employee, listEmployees: mocks.list, listRecentWeeklyEvaluations: mocks.recent, listRecentWeeklyErrors: mocks.recent, listRecentBonusAdjustments: mocks.recent }));
vi.mock("@/lib/report", () => ({ buildMonthlyReport: mocks.report }));
vi.mock("@/app/actions/employees", () => ({ updateEmployeeAction: vi.fn(), toggleEmployeeAction: vi.fn() }));
vi.mock("@/components/employee-fields", () => ({ EmployeeFields: () => createElement("div", null, "CAMPOS_EDICAO") }));
vi.mock("@/components/submit-button", () => ({ SubmitButton: () => null }));

import EmployeeProfilePage from "./page";

beforeEach(() => {
  vi.clearAllMocks();
  mocks.user.mockResolvedValue({ id: 1, role: "avaliador", username: "avaliador", evaluator_employee_id: 10, evaluator_name: "Liderança" });
  mocks.access.mockResolvedValue({ id: 42 });
  mocks.employee.mockResolvedValue({ id: 42, name: "José", sector: "Expedição", role: "Auxiliar", hire_date: "2020-01-01", active: 1 });
  mocks.list.mockResolvedValue([]);
  mocks.recent.mockResolvedValue([]);
  mocks.report.mockResolvedValue({ rows: [] });
});

async function render() {
  return renderToStaticMarkup(await EmployeeProfilePage({ params: Promise.resolve({ id: "42" }), searchParams: Promise.resolve({ month: "2026-09" }) }));
}

describe("perfil e download para avaliador", () => {
  it("exibe o download no fechamento selecionado sem controles de cadastro", async () => {
    const html = await render();
    expect(html).toContain("Baixar relatório em PDF");
    expect(html).toContain('/api/export/colaborador-pdf');
    expect(html).toContain('value="2026-09"');
    expect(html).toContain('/relatorios?month=2026-09');
    expect(html).not.toContain("Editar dados e elegibilidade");
    expect(html).not.toContain("Desativar colaborador");
    expect(html).not.toContain("CAMPOS_EDICAO");
    expect(mocks.access).toHaveBeenCalledWith(expect.objectContaining({ role: "avaliador" }), 42);
  });

  it("preserva os controles de cadastro para RH", async () => {
    mocks.user.mockResolvedValue({ id: 2, role: "rh", username: "rh" });
    const html = await render();
    expect(html).toContain("Editar dados e elegibilidade");
    expect(html).toContain("Desativar colaborador");
  });

  it("não consulta os registros quando o colaborador está fora da equipe", async () => {
    mocks.access.mockRejectedValue(new Error("Fora da equipe"));
    await expect(render()).rejects.toThrow("Fora da equipe");
    expect(mocks.employee).not.toHaveBeenCalled();
    expect(mocks.recent).not.toHaveBeenCalled();
  });
});
