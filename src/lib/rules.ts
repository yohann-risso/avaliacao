import { WEEKLY_CRITERIA, type WeeklyCriterionKey } from "@/lib/constants";

export type RuleCategory = "ASSIDUIDADE" | "QUALIDADE" | "PRODUTIVIDADE" | "COMPORTAMENTO";

export type EvaluationRule = {
  code: string;
  category: RuleCategory;
  occurrence: string;
  level: "BAIXO" | "MEDIO" | "ALTO" | "CRITICO";
  points: number;
  directive: string;
  weeklyDiscounts: Partial<Record<WeeklyCriterionKey, number>>;
  weeklyPointValue?: number;
  monthlyAssiduidadeDiscount?: number;
  monthlyAssiduidadePointValue?: number;
  priorityCriteria?: WeeklyCriterionKey[];
};

export type OccurrenceInput = {
  error_type?: string;
  qty?: number;
  week_start?: string;
};

const otherCriteria: WeeklyCriterionKey[] = ["qualidade", "taxa_erros", "produtividade", "comportamento"];

function discounts(keys: WeeklyCriterionKey[], percentage: number): Partial<Record<WeeklyCriterionKey, number>> {
  return Object.fromEntries(keys.map((key) => [key, percentage]));
}

export const EVALUATION_RULES: readonly EvaluationRule[] = [
  {
    code: "A01", category: "ASSIDUIDADE", occurrence: "Falta sem atestado / alto", level: "ALTO", points: 250,
    directive: "Perde 100% da assiduidade do mês e 100% dos outros quesitos na semana. Na reincidência, perde 100% do bônus-base mensal.",
    weeklyDiscounts: discounts(otherCriteria, 100), weeklyPointValue: 100,
    monthlyAssiduidadeDiscount: 100, monthlyAssiduidadePointValue: 150,
  },
  {
    code: "A02", category: "ASSIDUIDADE", occurrence: "Falta com atestado / baixo", level: "BAIXO", points: 47.5,
    directive: "Perde 100% da assiduidade semanal e 20% por dia nos outros quesitos. A reincidência repete o desconto.",
    weeklyDiscounts: { assiduidade: 100, ...discounts(otherCriteria, 20) }, priorityCriteria: ["assiduidade"],
  },
  {
    code: "A03", category: "ASSIDUIDADE", occurrence: "Declaração de até 50% da carga horária / baixo", level: "BAIXO", points: 87.5,
    directive: "Perde 100% da assiduidade semanal e 50% dos outros quesitos.",
    weeklyDiscounts: { assiduidade: 100, ...discounts(otherCriteria, 50) },
  },
  {
    code: "A04", category: "ASSIDUIDADE", occurrence: "Declaração acima de 50% da carga horária / alto", level: "ALTO", points: 137.5,
    directive: "Perde 100% da assiduidade semanal e todos os bônus variáveis da semana.",
    weeklyDiscounts: discounts(WEEKLY_CRITERIA.map((criterion) => criterion.key), 100),
  },
  {
    code: "A05", category: "ASSIDUIDADE", occurrence: "Saída por poucas horas / baixo", level: "BAIXO", points: 37.5,
    directive: "Perde 100% da assiduidade semanal.", weeklyDiscounts: { assiduidade: 100 },
  },
  {
    code: "A06", category: "ASSIDUIDADE", occurrence: "Saída superior a 50% do dia / alto", level: "ALTO", points: 125,
    directive: "Considera meia falta: perde 50% da assiduidade do mês e 50% dos outros quesitos na semana.",
    weeklyDiscounts: discounts(otherCriteria, 50), weeklyPointValue: 50,
    monthlyAssiduidadeDiscount: 50, monthlyAssiduidadePointValue: 75,
  },
  {
    code: "A07", category: "ASSIDUIDADE", occurrence: "Atraso até 7h30 / baixo", level: "BAIXO", points: 9.37,
    directive: "Perde 25% do bônus semanal de assiduidade.", weeklyDiscounts: { assiduidade: 25 },
  },
  {
    code: "A08", category: "ASSIDUIDADE", occurrence: "Atraso depois de 7h30 / alto", level: "ALTO", points: 37.5,
    directive: "Perde 100% do bônus semanal de assiduidade.", weeklyDiscounts: { assiduidade: 100 },
  },
  {
    code: "Q01", category: "QUALIDADE", occurrence: "Crítico", level: "CRITICO", points: 50,
    directive: "Perde 100% da bonificação semanal de Qualidade e Taxa de erros.", weeklyDiscounts: { qualidade: 100, taxa_erros: 100 },
  },
  {
    code: "Q02", category: "QUALIDADE", occurrence: "Alto", level: "ALTO", points: 25,
    directive: "Perde 50% da bonificação semanal de Qualidade e Taxa de erros.", weeklyDiscounts: { qualidade: 50, taxa_erros: 50 },
  },
  {
    code: "Q03", category: "QUALIDADE", occurrence: "Médio", level: "MEDIO", points: 12.5,
    directive: "Perde 25% da bonificação semanal de Qualidade e Taxa de erros.", weeklyDiscounts: { qualidade: 25, taxa_erros: 25 },
  },
  {
    code: "Q04", category: "QUALIDADE", occurrence: "Baixo", level: "BAIXO", points: 5,
    directive: "Perde 10% da bonificação semanal de Qualidade e Taxa de erros.", weeklyDiscounts: { qualidade: 10, taxa_erros: 10 },
  },
  {
    code: "P01", category: "PRODUTIVIDADE", occurrence: "Crítico", level: "CRITICO", points: 25,
    directive: "Perde 100% da bonificação semanal de Produtividade.", weeklyDiscounts: { produtividade: 100 },
  },
  {
    code: "P02", category: "PRODUTIVIDADE", occurrence: "Alto", level: "ALTO", points: 12.5,
    directive: "Perde 50% da bonificação semanal de Produtividade.", weeklyDiscounts: { produtividade: 50 },
  },
  {
    code: "P03", category: "PRODUTIVIDADE", occurrence: "Médio", level: "MEDIO", points: 6.3,
    directive: "Perde 25% da bonificação semanal de Produtividade.", weeklyDiscounts: { produtividade: 25 },
  },
  {
    code: "P04", category: "PRODUTIVIDADE", occurrence: "Baixo", level: "BAIXO", points: 2.5,
    directive: "Perde 10% da bonificação semanal de Produtividade.", weeklyDiscounts: { produtividade: 10 },
  },
  {
    code: "C01", category: "COMPORTAMENTO", occurrence: "Crítico", level: "CRITICO", points: 25,
    directive: "Perde 100% da bonificação semanal de Comportamento. Cabe carta de advertência.", weeklyDiscounts: { comportamento: 100 },
  },
  {
    code: "C02", category: "COMPORTAMENTO", occurrence: "Alto", level: "ALTO", points: 12.5,
    directive: "Perde 50% da bonificação semanal de Comportamento.", weeklyDiscounts: { comportamento: 50 },
  },
  {
    code: "C03", category: "COMPORTAMENTO", occurrence: "Médio", level: "MEDIO", points: 6.3,
    directive: "Perde 25% da bonificação semanal de Comportamento.", weeklyDiscounts: { comportamento: 25 },
  },
  {
    code: "C04", category: "COMPORTAMENTO", occurrence: "Baixo", level: "BAIXO", points: 2.5,
    directive: "Perde 10% da bonificação semanal de Comportamento.", weeklyDiscounts: { comportamento: 10 },
  },
] as const;

const rulesByCode = new Map(EVALUATION_RULES.map((rule) => [rule.code, rule]));

export function getEvaluationRule(code: unknown): EvaluationRule | undefined {
  return rulesByCode.get(String(code || "").trim().toUpperCase());
}

function quantity(occurrence: OccurrenceInput): number {
  const value = Number(occurrence.qty || 0);
  return Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0;
}

export function ruleQuantity(occurrences: OccurrenceInput[], code: string): number {
  return occurrences.reduce((total, occurrence) => {
    return getEvaluationRule(occurrence.error_type)?.code === code ? total + quantity(occurrence) : total;
  }, 0);
}

export type WeeklyOccurrenceImpact = {
  discounts: Record<WeeklyCriterionKey, number>;
  points: number;
  recognizedQuantity: number;
};

export function weeklyOccurrenceImpact(occurrences: OccurrenceInput[]): WeeklyOccurrenceImpact {
  const result: WeeklyOccurrenceImpact = {
    discounts: Object.fromEntries(WEEKLY_CRITERIA.map((criterion) => [criterion.key, 0])) as Record<WeeklyCriterionKey, number>,
    points: 0,
    recognizedQuantity: 0,
  };
  for (const occurrence of occurrences) {
    const rule = getEvaluationRule(occurrence.error_type);
    const qty = quantity(occurrence);
    if (!rule || !qty) continue;
    result.points += rule.points * qty;
    result.recognizedQuantity += qty;
    for (const criterion of WEEKLY_CRITERIA) {
      const discount = Number(rule.weeklyDiscounts[criterion.key] || 0) * qty;
      result.discounts[criterion.key] = Math.min(100, result.discounts[criterion.key] + discount);
    }
  }
  return result;
}

export type MonthlyOccurrenceImpact = {
  assiduidadeDiscount: number;
  assiduidadePointValue: number;
  blocksMonthlyBase: boolean;
  a01Quantity: number;
  points: number;
};

export function monthlyOccurrenceImpact(occurrences: OccurrenceInput[]): MonthlyOccurrenceImpact {
  let assiduidadeDiscount = 0;
  let a01Quantity = 0;
  let points = 0;
  let assiduidadePointValue = 0;
  for (const occurrence of occurrences) {
    const rule = getEvaluationRule(occurrence.error_type);
    const qty = quantity(occurrence);
    if (!rule || !qty) continue;
    points += rule.points * qty;
    assiduidadeDiscount += Number(rule.monthlyAssiduidadeDiscount || 0) * qty;
    assiduidadePointValue += Number(rule.monthlyAssiduidadePointValue || 0) * qty;
    if (rule.code === "A01") a01Quantity += qty;
  }
  return {
    assiduidadeDiscount: Math.min(100, assiduidadeDiscount),
    assiduidadePointValue,
    blocksMonthlyBase: a01Quantity >= 2,
    a01Quantity,
    points,
  };
}
