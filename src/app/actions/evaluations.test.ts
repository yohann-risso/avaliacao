import ExcelJS from "exceljs";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => {
  const transaction = vi.fn(async () => []);
  const sql = Object.assign(vi.fn(async () => []), {
    begin: vi.fn(async (callback: (transaction: (...args: unknown[]) => Promise<unknown[]>) => Promise<void>) => callback(transaction)),
  });
  return {
    revalidatePath: vi.fn(),
    redirectWith: vi.fn(),
    requireEmployeesAccess: vi.fn(async () => undefined),
    requireEvaluationEditor: vi.fn(async () => ({
      id: 7,
      username: "supervisor",
      role: "supervisor",
      evaluator_employee_id: 10,
      evaluator_name: "Robson",
    })),
    sql,
    transaction,
  };
});

vi.mock("next/cache", () => ({ revalidatePath: mocks.revalidatePath }));
vi.mock("@/lib/auth", () => ({ requireEvaluationEditor: mocks.requireEvaluationEditor }));
vi.mock("@/lib/db", () => ({ sql: mocks.sql }));
vi.mock("@/lib/employee-access", () => ({
  requireEmployeeAccess: vi.fn(),
  requireEmployeesAccess: mocks.requireEmployeesAccess,
}));
vi.mock("@/lib/action-utils", () => ({
  integer: (formData: FormData, name: string, fallback = 0) => {
    const value = Number(String(formData.get(name) || "").trim());
    return Number.isInteger(value) ? value : fallback;
  },
  percentage: (formData: FormData, name: string) => Number(formData.get(name)),
  publicError: (error: unknown) => error instanceof Error ? error.message : "Erro desconhecido.",
  redirectWith: mocks.redirectWith,
  text: (formData: FormData, name: string) => String(formData.get(name) || "").trim(),
}));

import { importWeeklyWorkbookAction } from "@/app/actions/evaluations";

async function importFormData(): Promise<FormData> {
  const workbook = new ExcelJS.Workbook();
  const sheet = workbook.addWorksheet("Avaliacoes");
  sheet.addRow([
    "employee_id",
    "semana",
    "itens",
    "assiduidade (%)",
    "qualidade (%)",
    "taxa erros (%)",
    "produtividade (%)",
    "comportamento (%)",
    "avaliador",
    "observações",
  ]);
  sheet.addRow([1, "2026-09-21", 10, 100, 100, 100, 100, 100, "Robson", "Importação de teste"]);
  const buffer = await workbook.xlsx.writeBuffer();
  const formData = new FormData();
  formData.set("week_start", "2026-09-21");
  formData.set("confirm", "on");
  formData.set("workbook", new File([new Uint8Array(buffer)], "avaliacoes.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  }));
  return formData;
}

describe("importWeeklyWorkbookAction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.redirectWith.mockImplementation(() => {
      throw new Error("NEXT_REDIRECT");
    });
    vi.spyOn(console, "info").mockImplementation(() => undefined);
    vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  it("não captura o redirecionamento de sucesso como erro", async () => {
    await expect(importWeeklyWorkbookAction(await importFormData())).rejects.toThrow("NEXT_REDIRECT");

    expect(mocks.transaction).toHaveBeenCalledOnce();
    expect(mocks.revalidatePath).toHaveBeenCalledWith("/avaliacoes");
    expect(mocks.redirectWith).toHaveBeenCalledOnce();
    expect(mocks.redirectWith).toHaveBeenCalledWith(
      "/avaliacoes?week=2026-09-21",
      "success",
      "1 avaliação(ões) importada(s).",
    );
  });
});
