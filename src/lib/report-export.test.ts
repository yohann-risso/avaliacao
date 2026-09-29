import { PDFDocument } from "pdf-lib";
import { describe, expect, it } from "vitest";

import { buildExecutiveReportPdf, buildReportCsv, sortReportRowsAlphabetically } from "@/lib/report-export";
import type { ReportRow } from "@/lib/report";

function row(index: number): ReportRow {
  return {
    employeeId: index,
    name: `Funcionário ${index}`,
    sector: index % 2 ? "Operações" : "Qualidade",
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
    weeklyPercentages: [
      {
        weekStart: "2026-08-31",
        assiduidade: 100,
        qualidade: 90,
        taxaErros: 80,
        produtividade: 95,
        comportamento: 100,
      },
    ],
  };
}

describe("exportações do fechamento", () => {
  it("gera CSV somente com as linhas recebidas", () => {
    const csv = buildReportCsv([row(1), row(3)]);
    expect(csv).toContain('"Funcionário 1";"Operações"');
    expect(csv).toContain('"Funcionário 3";"Operações"');
    expect(csv).not.toContain('"Funcionário 2"');
  });

  it("gera PDF paginado com o escopo selecionado", async () => {
    const bytes = await buildExecutiveReportPdf({
      month: "2026-09",
      rows: Array.from({ length: 35 }, (_, index) => row(index + 1)),
      sectors: ["Operações", "Qualidade"],
      includeInactive: true,
    });
    const pdf = await PDFDocument.load(bytes);
    expect(pdf.getPageCount()).toBeGreaterThan(1);
  });

  it("organiza as pessoas em ordem alfabética no PDF", () => {
    const rows = [row(3), row(1), row(2)];
    rows[0].name = "Zélia";
    rows[1].name = "Ágata";
    rows[2].name = "Bruno";
    expect(sortReportRowsAlphabetically(rows).map((item) => item.name)).toEqual(["Ágata", "Bruno", "Zélia"]);
  });
});
