export const WEEKLY_CRITERIA = [
  { key: "assiduidade", label: "Assiduidade", monthlyCap: 150 },
  { key: "qualidade", label: "Qualidade", monthlyCap: 100 },
  { key: "taxa_erros", label: "Taxa de erros", monthlyCap: 100 },
  { key: "produtividade", label: "Produtividade", monthlyCap: 100 },
  { key: "comportamento", label: "Comportamento", monthlyCap: 100 },
] as const;

export const MONITOR_FIXED_VALUE = 300;

export const PAY_BANDS = [
  { max: 50, multiplier: 0 },
  { max: 70, multiplier: 0.25 },
  { max: 80, multiplier: 0.5 },
  { max: 90, multiplier: 0.75 },
  { max: 100, multiplier: 1 },
] as const;

export const TENURE_BONUS_PER_YEAR = 30;

export type WeeklyCriterionKey = (typeof WEEKLY_CRITERIA)[number]["key"];
