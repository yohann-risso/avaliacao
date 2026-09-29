import { MONITOR_FIXED_VALUE, PAY_BANDS, TENURE_BONUS_PER_YEAR, WEEKLY_CRITERIA, type WeeklyCriterionKey } from "@/lib/constants";
import { monthReferenceDate, yearsInCompany } from "@/lib/dates";
import { aggregateOccurrenceQuantities, EVALUATION_RULES, monthlyOccurrenceImpact, type OccurrenceInput } from "@/lib/rules";

export type FinancialAdjustmentInput = { amount: number | string };

function currency(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

export function financialAdjustmentTotal(adjustments: FinancialAdjustmentInput[] = []): number {
  return currency(adjustments.reduce((sum, adjustment) => {
    const amount = Number(adjustment.amount);
    return sum + (Number.isFinite(amount) ? amount : 0);
  }, 0));
}

export function totalAfterFinancialAdjustments(base: number, adjustments: FinancialAdjustmentInput[] = []): number {
  return currency(Math.max(0, Number(base || 0) + financialAdjustmentTotal(adjustments)));
}

export function clampPercentage(value: unknown): number {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? Math.max(0, Math.min(100, numeric)) : 0;
}

export function bandMultiplier(value: unknown): number {
  const percentage = clampPercentage(value);
  return PAY_BANDS.find((band) => percentage <= band.max)?.multiplier ?? 0;
}

export function weeklyPaymentBreakdown(row: Record<string, unknown>, occurrences: OccurrenceInput[] = []) {
  const weekCount = 4;
  const quantitiesByCode = aggregateOccurrenceQuantities(occurrences);
  const byCriterion = Object.fromEntries(WEEKLY_CRITERIA.map((criterion) => {
    const gross = (criterion.monthlyCap / weekCount) * bandMultiplier(row[`${criterion.key}_pct`]);
    return [criterion.key, { gross, paid: gross, discountPercentage: 0 }];
  })) as Record<(typeof WEEKLY_CRITERIA)[number]["key"], { gross: number; paid: number; discountPercentage: number }>;

  for (const rule of EVALUATION_RULES) {
    const qty = quantitiesByCode.get(rule.code) || 0;
    if (!qty) continue;
    let pointBudget = Number(rule.weeklyPointValue ?? rule.points) * qty;
    const desired = new Map<WeeklyCriterionKey, number>();
    for (const criterion of WEEKLY_CRITERIA) {
      const percentage = Math.min(100, Number(rule.weeklyDiscounts[criterion.key] || 0) * qty);
      const weeklyReference = criterion.monthlyCap / weekCount;
      if (percentage > 0) desired.set(criterion.key, weeklyReference * percentage / 100);
    }

    for (const key of rule.priorityCriteria || []) {
      const amount = Math.min(pointBudget, desired.get(key) || 0, byCriterion[key].paid);
      byCriterion[key].paid -= amount;
      pointBudget -= amount;
      desired.delete(key);
    }

    if (pointBudget > 0 && desired.size) {
      const available = [...desired.entries()].map(([key, amount]) => [key, Math.min(amount, byCriterion[key].paid)] as const);
      const desiredTotal = available.reduce((sum, [, amount]) => sum + amount, 0);
      const factor = desiredTotal > 0 ? Math.min(1, pointBudget / desiredTotal) : 0;
      for (const [key, amount] of available) byCriterion[key].paid -= amount * factor;
    }
  }

  for (const criterion of WEEKLY_CRITERIA) {
    const item = byCriterion[criterion.key];
    item.paid = Math.max(0, item.paid);
    item.discountPercentage = item.gross > 0 ? ((item.gross - item.paid) / item.gross) * 100 : 0;
  }
  const gross = Object.values(byCriterion).reduce((sum, item) => sum + item.gross, 0);
  const total = Object.values(byCriterion).reduce((sum, item) => sum + item.paid, 0);
  const occurrencePoints = EVALUATION_RULES.reduce((sum, rule) => sum + rule.points * (quantitiesByCode.get(rule.code) || 0), 0);
  return { byCriterion, gross, total, discount: gross - total, occurrencePoints };
}

export function weeklyPayment(row: Record<string, unknown>, occurrences: OccurrenceInput[] = []): number {
  return weeklyPaymentBreakdown(row, occurrences).total;
}

export function monthlyBasePayment(rows: Record<string, unknown>[], occurrences: OccurrenceInput[]) {
  const occurrencesByWeek = new Map<string, OccurrenceInput[]>();
  for (const occurrence of occurrences) {
    const week = String(occurrence.week_start || "").trim();
    const current = occurrencesByWeek.get(week) || [];
    current.push(occurrence);
    occurrencesByWeek.set(week, current);
  }
  const byCriterion = Object.fromEntries(WEEKLY_CRITERIA.map((criterion) => [criterion.key, 0])) as Record<(typeof WEEKLY_CRITERIA)[number]["key"], number>;
  const grossByCriterion = Object.fromEntries(WEEKLY_CRITERIA.map((criterion) => [criterion.key, 0])) as Record<(typeof WEEKLY_CRITERIA)[number]["key"], number>;
  let gross = 0;
  for (const row of rows) {
    const breakdown = weeklyPaymentBreakdown(row, occurrencesByWeek.get(String(row.week_start || "").trim()) || []);
    gross += breakdown.gross;
    for (const criterion of WEEKLY_CRITERIA) {
      byCriterion[criterion.key] += breakdown.byCriterion[criterion.key].paid;
      grossByCriterion[criterion.key] += breakdown.byCriterion[criterion.key].gross;
    }
  }
  const monthlyImpact = monthlyOccurrenceImpact(occurrences);
  if (monthlyImpact.blocksMonthlyBase) {
    for (const criterion of WEEKLY_CRITERIA) byCriterion[criterion.key] = 0;
  } else {
    const desired = grossByCriterion.assiduidade * monthlyImpact.assiduidadeDiscount / 100;
    const applied = Math.min(byCriterion.assiduidade, desired, monthlyImpact.assiduidadePointValue);
    byCriterion.assiduidade -= applied;
  }
  const total = Object.values(byCriterion).reduce((sum, value) => sum + value, 0);
  return { byCriterion, gross, total, discount: gross - total, ...monthlyImpact };
}

export function monitorPayment(eligible = false): number {
  return eligible ? MONITOR_FIXED_VALUE : 0;
}

export function tenurePayment(hireDate: string, month: string): number {
  return yearsInCompany(hireDate, monthReferenceDate(month)) * TENURE_BONUS_PER_YEAR;
}

export function brl(value: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value || 0);
}

export function pct(value: unknown): string {
  return `${clampPercentage(value).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}
