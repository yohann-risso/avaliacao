import { describe, expect, it } from "vitest";

import {
  filterReportRows,
  normalizeSectorSelection,
  reportExportQuery,
  reportOccurrences,
  summarizeReportRows,
} from "@/lib/report-selection";
import type { ReportRow } from "@/lib/report";

function row(overrides: Partial<ReportRow>): ReportRow {
  return {
    employeeId: 1,
    name: "Ana",
    sector: "Operações",
    role: "Analista",
    group: "Operação",
    eligibleWeeks: 4,
    evaluatedWeeks: 4,
    missingWeeks: 0,
    errors: 0,
    rulePoints: 0,
    ruleDiscount: 0,
    ruleImpact: "Sem desconto por ocorrência",
    average: 100,
    basePayment: 550,
    monitorPayment: 0,
    tenurePayment: 30,
    adjustmentTotal: 0,
    total: 580,
    status: "OK",
    occurrences: [],
    weeklyPercentages: [],
    ...overrides,
  };
}

describe("seleção de setores do fechamento", () => {
  const rows = [
    row({ employeeId: 1, name: "Ana", sector: "Operações" }),
    row({ employeeId: 2, name: "Bruno", sector: "Qualidade", evaluatedWeeks: 2, missingWeeks: 2, status: "Pendente", total: 300, ruleDiscount: 25 }),
    row({ employeeId: 3, name: "Carla", sector: "Financeiro", group: "Coord./Sup.", eligibleWeeks: 4, evaluatedWeeks: 0, total: 700, monitorPayment: 300, adjustmentTotal: -20 }),
  ];

  it("normaliza setores repetidos enviados pela URL", () => {
    expect(normalizeSectorSelection([" Qualidade ", "Operações", "Qualidade", ""])).toEqual(["Qualidade", "Operações"]);
  });

  it("filtra vários setores e mantém a busca combinada", () => {
    expect(filterReportRows(rows, ["Operações", "Qualidade"]).map((item) => item.name)).toEqual(["Ana", "Bruno"]);
    expect(filterReportRows(rows, ["Operações", "Qualidade"], "qualidade").map((item) => item.name)).toEqual(["Bruno"]);
  });

  it("recalcula o fechamento somente com as pessoas selecionadas", () => {
    const summary = summarizeReportRows(filterReportRows(rows, ["Qualidade", "Financeiro"]));
    expect(summary.total).toBe(1000);
    expect(summary.pending).toBe(1);
    expect(summary.weeklyExpected).toBe(4);
    expect(summary.weeklyDone).toBe(2);
    expect(summary.coverage).toBe(50);
    expect(summary.ruleDiscount).toBe(25);
    expect(summary.monitorTotal).toBe(300);
    expect(summary.adjustmentTotal).toBe(-20);
    expect(summary.baseTotal).toBe(1100);
    expect(summary.tenureTotal).toBe(60);
  });

  it("traz ocorrências somente das pessoas que permaneceram nos filtros", () => {
    const rowsWithOccurrences = [
      row({ employeeId: 1, name: "Ana", sector: "Operações", occurrences: [{ id: 10, weekStart: "2026-09-07", code: "Q03", severity: "MEDIO", quantity: 2, notes: "Duas falhas" }] }),
      row({ employeeId: 2, name: "Bruno", sector: "Qualidade", occurrences: [{ id: 11, weekStart: "2026-09-14", code: "C04", severity: "BAIXO", quantity: 1, notes: "" }] }),
    ];

    const occurrences = reportOccurrences(filterReportRows(rowsWithOccurrences, ["Qualidade"]));

    expect(occurrences).toHaveLength(1);
    expect(occurrences[0]).toMatchObject({ employeeName: "Bruno", code: "C04", quantity: 1 });
  });

  it("considera coberta uma seleção formada apenas por liderança", () => {
    const leadership = filterReportRows(rows, ["Financeiro"]);
    expect(summarizeReportRows(leadership).coverage).toBe(100);
  });

  it("mantém todos os setores na query de exportação", () => {
    const params = new URLSearchParams(reportExportQuery("2026-09", ["Operações", "Qualidade"], "ana", true));
    expect(params.get("month")).toBe("2026-09");
    expect(params.getAll("sector")).toEqual(["Operações", "Qualidade"]);
    expect(params.get("q")).toBe("ana");
    expect(params.get("inactive")).toBe("1");
  });
});
