const SECTOR_LOCALE = "pt-BR";

function cleanSectorName(value: string): string {
  return String(value || "").normalize("NFC").trim().replace(/\s+/gu, " ");
}

function sectorKey(value: string): string {
  return cleanSectorName(value).toLocaleLowerCase(SECTOR_LOCALE);
}

export function normalizeSectorName(value: string, existingSectors: string[] = []): string {
  const cleaned = cleanSectorName(value);
  if (!cleaned) return "";

  const existing = existingSectors
    .map(cleanSectorName)
    .find((sector) => sectorKey(sector) === sectorKey(cleaned));
  const canonical = existing || cleaned;
  const [first, ...rest] = [...canonical];

  return `${first.toLocaleUpperCase(SECTOR_LOCALE)}${rest.join("")}`;
}
