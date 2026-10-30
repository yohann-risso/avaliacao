import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  user: { id: 1, role: "supervisor" }, access: vi.fn(), employee: vi.fn(), evaluations: vi.fn(), occurrences: vi.fn(), adjustments: vi.fn(), report: vi.fn(), pdf: vi.fn(),
}));
vi.mock("@/lib/auth", () => ({ requirePeopleManager: vi.fn().mockResolvedValue(mocks.user) }));
vi.mock("@/lib/employee-access", () => ({ requireManagedEmployeeAccess: mocks.access }));
vi.mock("@/lib/data", () => ({ getEmployee: mocks.employee, listWeeklyEvaluations: mocks.evaluations, listWeeklyErrorsForWeeks: mocks.occurrences, listBonusAdjustmentsForWeeks: mocks.adjustments }));
vi.mock("@/lib/report", () => ({ buildMonthlyReport: mocks.report }));
vi.mock("@/lib/employee-report-pdf", () => ({ buildEmployeeReportPdf: mocks.pdf }));

import { GET } from "@/app/api/export/colaborador-pdf/route";
import { weeksForCompetencia } from "@/lib/dates";

beforeEach(() => {
  vi.clearAllMocks();
  mocks.access.mockResolvedValue({ id: 42 });
  mocks.employee.mockResolvedValue({ id: 42, name: "José", active: 0 });
  mocks.evaluations.mockResolvedValue([]);
  mocks.occurrences.mockResolvedValue([]);
  mocks.adjustments.mockResolvedValue([]);
  mocks.report.mockResolvedValue({ rows: [{ employeeId: 42, total: 100 }] });
  mocks.pdf.mockResolvedValue(new TextEncoder().encode("%PDF-1.7"));
});

describe("download do relatório individual", () => {
  it("limita os dados ao colaborador e às semanas do fechamento, incluindo inativos", async () => {
    const response = await GET(new Request("http://localhost/api/export/colaborador-pdf?employee=42&month=2026-10"));
    expect(response.status).toBe(200);
    expect(response.headers.get("Content-Type")).toBe("application/pdf");
    expect(response.headers.get("Content-Disposition")).toContain("colaborador-42-fechamento-2026-10.pdf");
    expect(response.headers.get("Cache-Control")).toBe("private, no-store");
    expect(mocks.access).toHaveBeenCalledWith(mocks.user, 42);
    for (const query of [mocks.evaluations, mocks.occurrences, mocks.adjustments]) {
      expect(query).toHaveBeenCalledWith(weeksForCompetencia("2026-10"), [42]);
    }
    expect(mocks.report).toHaveBeenCalledWith("2026-10", mocks.user, { includeInactive: true });
    expect(mocks.pdf.mock.calls[0][0].summary).toEqual({ employeeId: 42, total: 100 });
  });

  it.each(["employee=0&month=2026-10", "employee=42&month=2026-13", "employee=42", "employee=1.5&month=2026-10"])("rejeita parâmetros inválidos: %s", async (query) => {
    expect((await GET(new Request(`http://localhost/api/export/colaborador-pdf?${query}`))).status).toBe(400);
    expect(mocks.access).not.toHaveBeenCalled();
    expect(mocks.pdf).not.toHaveBeenCalled();
  });

  it("bloqueia exportação de pessoas fora da equipe antes de consultar seus dados", async () => {
    mocks.access.mockRejectedValue(new Error("Fora da equipe"));
    expect((await GET(new Request("http://localhost/api/export/colaborador-pdf?employee=42&month=2026-10"))).status).toBe(403);
    expect(mocks.employee).not.toHaveBeenCalled();
    expect(mocks.evaluations).not.toHaveBeenCalled();
    expect(mocks.pdf).not.toHaveBeenCalled();
  });
});
