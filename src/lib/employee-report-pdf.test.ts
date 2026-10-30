import { PDFDocument, PDFPage } from "pdf-lib";
import { afterEach, describe, expect, it, vi } from "vitest";
import { buildEmployeeReportPdf, type EmployeeReportPdfInput } from "@/lib/employee-report-pdf";

function fixture(): EmployeeReportPdfInput {
  return {
    month: "2026-10",
    employee: { id: 42, name: "José da Conceição", sector: "Expedição", role: "Auxiliar", hire_date: "2025-01-01", active: 1 } as EmployeeReportPdfInput["employee"],
    weeks: ["2026-09-28", "2026-10-05"],
    evaluations: [{ id: 1, employee_id: 42, week_start: "2026-09-28", evaluator: "Márcia", qualidade_pct: 80, qualidade_just: "Conferência incompleta", notes: "Observação geral da semana" }],
    occurrences: [{ id: 2, employee_id: 42, week_start: "2026-09-28", error_type: "Q03", severity: "MEDIO", qty: 2, notes: "Contexto da ocorrência", role_snapshot: "Auxiliar", created_at: "" }],
    adjustments: [{ id: 3, employee_id: 42, week_start: "2026-10-05", amount: -15, description: "Correção justificada", created_by_username: "RH", created_by_user_id: 1, created_at: "" }],
  };
}

afterEach(() => vi.restoreAllMocks());

describe("relatório individual em PDF", () => {
  it("inclui notas, justificativas, ocorrências, ajustes e semanas sem avaliação", async () => {
    const draw = vi.spyOn(PDFPage.prototype, "drawText");
    const input = fixture();
    input.occurrences.push({ ...input.occurrences[0], id: 99, week_start: "2026-08-03", notes: "OUTRO FECHAMENTO" });
    input.adjustments.push({ ...input.adjustments[0], id: 99, week_start: "2026-08-03", description: "OUTRO AJUSTE" });
    const bytes = await buildEmployeeReportPdf(input);
    const text = draw.mock.calls.map(([value]) => value).join("\n");
    expect(text).toContain("José da Conceição");
    expect(text).toContain("Conferência incompleta");
    expect(text).toContain("Observação geral da semana");
    expect(text).toContain("Contexto da ocorrência");
    expect(text).toContain("Correção justificada");
    expect(text).toContain("Sem avaliação registrada nesta semana");
    expect(text).not.toContain("OUTRO FECHAMENTO");
    expect(text).not.toContain("OUTRO AJUSTE");
    expect((await PDFDocument.load(bytes)).getPageCount()).toBeGreaterThan(0);
  });

  it("preserva textos extensos em várias páginas e mantém o conteúdo nas margens", async () => {
    const draw = vi.spyOn(PDFPage.prototype, "drawText");
    const input = fixture();
    input.evaluations[0].notes = `${"Observações detalhadas para revisão. ".repeat(350)}\n${"X".repeat(300)}\nFIM DO TEXTO`;
    const bytes = await buildEmployeeReportPdf(input);
    expect((await PDFDocument.load(bytes)).getPageCount()).toBeGreaterThan(3);
    const text = draw.mock.calls.map(([value]) => value).join("\n");
    expect(text).toContain("FIM DO TEXTO");
    const body = draw.mock.calls.map(([value]) => value).filter((value) => !value.startsWith("Relatório individual -")).join(" ");
    expect(body.replace(/\s+/g, " ").match(/Observações detalhadas para revisão\./g)).toHaveLength(350);
    for (const [value, options] of draw.mock.calls) {
      expect(options!.y).toBeGreaterThanOrEqual(24);
      expect(options!.x).toBeGreaterThanOrEqual(36);
      expect(options!.x! + options!.font!.widthOfTextAtSize(value, options!.size!)).toBeLessThanOrEqual(559.29);
    }
  });

  it("continua justificativas extensas nas tabelas, repete os cabeçalhos e preserva todas as palavras", async () => {
    const draw = vi.spyOn(PDFPage.prototype, "drawText");
    const rectangles = vi.spyOn(PDFPage.prototype, "drawRectangle");
    const input = fixture();
    input.evaluations[0].qualidade_just = `${"REGISTROINTEGRAL ".repeat(900)}FIM DA JUSTIFICATIVA`;
    input.occurrences[0].notes = `${"OCORRENCIACOMPLETA ".repeat(350)}FIM DA OCORRÊNCIA`;
    input.adjustments[0].description = `${"AJUSTECOMPLETO ".repeat(250)}FIM DO AJUSTE`;
    const bytes = await buildEmployeeReportPdf(input);
    expect((await PDFDocument.load(bytes)).getPageCount()).toBeGreaterThan(4);
    const text = draw.mock.calls.map(([value]) => value).join(" ");
    expect(text.match(/REGISTROINTEGRAL/g)).toHaveLength(900);
    expect(text.match(/OCORRENCIACOMPLETA/g)).toHaveLength(350);
    expect(text.match(/AJUSTECOMPLETO/g)).toHaveLength(250);
    expect(text).toContain("FIM DA JUSTIFICATIVA");
    expect(text).toContain("FIM DA OCORRÊNCIA");
    expect(text).toContain("FIM DO AJUSTE");
    expect(draw.mock.calls.filter(([value]) => value === "Justificativa").length).toBeGreaterThan(1);
    for (const [options] of rectangles.mock.calls) {
      expect(options!.y).toBeGreaterThanOrEqual(52);
      expect(options!.x! + options!.width!).toBeLessThanOrEqual(559.29);
    }
  });

  it("mantém notas de 100% com justificativa e separa o consolidado dos registros", async () => {
    const draw = vi.spyOn(PDFPage.prototype, "drawText");
    const input = fixture();
    input.evaluations[0].qualidade_pct = 100;
    input.evaluations[0].qualidade_just = "Justificativa positiva preservada";
    const bytes = await buildEmployeeReportPdf(input);
    const text = draw.mock.calls.map(([value]) => value).join(" ");
    expect(text).toContain("Justificativa positiva preservada");
    expect(text).toContain("Avaliações por semana");
    expect(text).toContain("Registros e justificativas");
    expect((await PDFDocument.load(bytes)).getPageCount()).toBe(2);
  });
});
