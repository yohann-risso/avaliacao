import { describe, expect, it } from "vitest";

import { competenciaFromWeek, eligibleWeeks, weeksForCompetencia } from "@/lib/dates";
import { bandMultiplier, monthlyBasePayment, monitorPayment, tenurePayment, weeklyPayment, weeklyPaymentBreakdown } from "@/lib/money";
import { getEvaluationRule, monthlyOccurrenceImpact } from "@/lib/rules";

describe("competência operacional", () => {
  it("move para o mês seguinte quando a sexta passa do dia 25", () => {
    expect(competenciaFromWeek("2026-05-18")).toBe("2026-05");
    expect(competenciaFromWeek("2026-05-25")).toBe("2026-06");
  });

  it("retorna apenas semanas pertencentes à competência", () => {
    const weeks = weeksForCompetencia("2026-05");
    expect(weeks).toHaveLength(4);
    expect(weeks.every((week) => competenciaFromWeek(week) === "2026-05")).toBe(true);
  });

  it("considera somente semanas posteriores à semana da contratação", () => {
    expect(eligibleWeeks("2026-05-06", "", ["2026-05-04", "2026-05-11"])).toEqual(["2026-05-11"]);
  });
});

describe("pagamento", () => {
  it("mantém as faixas contínuas para percentuais decimais", () => {
    expect(bandMultiplier(50)).toBe(0);
    expect(bandMultiplier(50.1)).toBe(0.25);
    expect(bandMultiplier(90.5)).toBe(1);
  });

  it("rateia o teto mensal entre as semanas da competência", () => {
    const week = weeksForCompetencia("2026-05")[0];
    const count = weeksForCompetencia("2026-05").length;
    expect(weeklyPayment({
      week_start: week,
      assiduidade_pct: 100,
      qualidade_pct: 100,
      taxa_erros_pct: 100,
      produtividade_pct: 100,
      comportamento_pct: 100,
    })).toBeCloseTo(550 / count, 6);
  });

  it("calcula o adicional por anos completos", () => {
    expect(tenurePayment("2020-09-01", "2026-09")).toBe(180);
  });

  it("paga monitoria como valor fixo sem avaliação", () => {
    expect(monitorPayment(true)).toBe(300);
    expect(monitorPayment(false)).toBe(0);
  });
});

describe("regras corporativas", () => {
  const weeks = weeksForCompetencia("2026-05");
  const fullScore = (week: string) => ({
    week_start: week,
    assiduidade_pct: 100,
    qualidade_pct: 100,
    taxa_erros_pct: 100,
    produtividade_pct: 100,
    comportamento_pct: 100,
  });

  it("usa os códigos e pontos definidos no documento", () => {
    expect(getEvaluationRule("Q03")?.points).toBe(12.5);
    expect(getEvaluationRule("A07")?.points).toBe(9.37);
  });

  it("aplica PONTOS como desconto semanal depois da faixa", () => {
    expect(weeks).toHaveLength(4);
    const q03 = weeklyPaymentBreakdown(fullScore(weeks[0]), [{ error_type: "Q03", qty: 1 }]);
    expect(q03.discount).toBeCloseTo(12.5, 6);
    const a02 = weeklyPaymentBreakdown(fullScore(weeks[0]), [{ error_type: "A02", qty: 1 }]);
    expect(a02.discount).toBeCloseTo(47.5, 6);
    const a02TwoDays = weeklyPaymentBreakdown(fullScore(weeks[0]), [{ error_type: "A02", qty: 2 }]);
    expect(a02TwoDays.discount).toBeCloseTo(77.5, 6);
  });

  it("limita o desconto ao bônus disponível e à diretriz", () => {
    const lowScore = { ...fullScore(weeks[0]), produtividade_pct: 70 };
    const result = weeklyPaymentBreakdown(lowScore, [{ error_type: "P01", qty: 1 }]);
    expect(result.byCriterion.produtividade.gross).toBeCloseTo(6.25, 6);
    expect(result.byCriterion.produtividade.paid).toBe(0);
  });

  it("consolida A01 e A06 no fechamento mensal", () => {
    const rows = weeks.map(fullScore);
    expect(monthlyBasePayment(rows, [{ error_type: "A01", qty: 1, week_start: weeks[0] }]).discount).toBeCloseTo(250, 6);
    expect(monthlyBasePayment(rows, [{ error_type: "A06", qty: 1, week_start: weeks[0] }]).discount).toBeCloseTo(125, 6);
    expect(monthlyBasePayment(rows, [{ error_type: "A01", qty: 2, week_start: weeks[0] }]).total).toBe(0);
    expect(monthlyOccurrenceImpact([{ error_type: "A01", qty: 2 }]).blocksMonthlyBase).toBe(true);
  });
});
