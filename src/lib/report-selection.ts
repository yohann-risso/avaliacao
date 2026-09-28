import type { ReportRow } from "@/lib/report";

export type ReportSummary = {
  total: number;
  pending: number;
  coverage: number;
  weeklyExpected: number;
  weeklyDone: number;
  monitorTotal: number;
  adjustmentTotal: number;
  ruleDiscount: number;
  recurrenceBlocks: number;
};

export function firstSearchParam(value: string | string[] | undefined): string {
  return String(Array.isArray(value) ? value[0] || "" : value || "");
}

export function normalizeSectorSelection(value: string | string[] | undefined): string[] {
  const values = Array.isArray(value) ? value : value ? [value] : [];
  return [...new Set(values.map((item) => item.trim()).filter(Boolean))];
}

export function filterReportRows(rows: ReportRow[], sectors: string[], query = ""): ReportRow[] {
  const selected = new Set(sectors);
  const normalizedQuery = query.trim().toLocaleLowerCase("pt-BR");
  return rows.filter((row) => {
    const matchesSector = !selected.size || selected.has(row.sector);
    const searchable = `${row.name} ${row.role} ${row.sector}`.toLocaleLowerCase("pt-BR");
    return matchesSector && (!normalizedQuery || searchable.includes(normalizedQuery));
  });
}

export function summarizeReportRows(rows: ReportRow[]): ReportSummary {
  const operation = rows.filter((row) => row.group === "Operação");
  const weeklyExpected = operation.reduce((sum, row) => sum + row.eligibleWeeks, 0);
  const weeklyDone = operation.reduce((sum, row) => sum + row.evaluatedWeeks, 0);
  return {
    total: rows.reduce((sum, row) => sum + row.total, 0),
    pending: rows.filter((row) => row.status === "Pendente").length,
    coverage: weeklyExpected ? (weeklyDone / weeklyExpected) * 100 : rows.length ? 100 : 0,
    weeklyExpected,
    weeklyDone,
    monitorTotal: rows.reduce((sum, row) => sum + row.monitorPayment, 0),
    adjustmentTotal: rows.reduce((sum, row) => sum + row.adjustmentTotal, 0),
    ruleDiscount: rows.reduce((sum, row) => sum + row.ruleDiscount, 0),
    recurrenceBlocks: rows.filter((row) => row.ruleImpact.includes("bloqueado")).length,
  };
}

export function reportExportQuery(month: string, sectors: string[], query = ""): string {
  const params = new URLSearchParams({ month });
  for (const sector of sectors) params.append("sector", sector);
  if (query.trim()) params.set("q", query.trim());
  return params.toString();
}

export function reportScopeLabel(sectors: string[], query = ""): string {
  const sectorLabel = sectors.length ? sectors.join(", ") : "Todos os setores";
  return query.trim() ? `${sectorLabel} · busca: ${query.trim()}` : sectorLabel;
}
