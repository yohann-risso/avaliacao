const DAY_MS = 86_400_000;

export function parseIsoDate(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || "").trim());
  if (!match) return null;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  return Number.isNaN(date.getTime()) ? null : date;
}

export function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function currentMonth(): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(new Date());
  const year = parts.find((part) => part.type === "year")?.value;
  const month = parts.find((part) => part.type === "month")?.value;
  return `${year}-${month}`;
}

export function todayBrazil(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

export function monthBr(month: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(month);
  return match ? `${match[2]}/${match[1]}` : month;
}

export function dateBr(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ""));
  return match ? `${match[3]}/${match[2]}/${match[1]}` : value || "—";
}

export function mondayOf(date: Date): Date {
  const weekday = date.getUTCDay();
  const distance = weekday === 0 ? 6 : weekday - 1;
  return new Date(date.getTime() - distance * DAY_MS);
}

export function normalizeMonday(value: string): string {
  const parsed = parseIsoDate(value);
  if (!parsed) throw new Error("Data inválida.");
  return isoDate(mondayOf(parsed));
}

export function competenciaFromWeek(weekStart: string): string {
  const monday = parseIsoDate(weekStart);
  if (!monday) throw new Error("Semana inválida.");
  const friday = new Date(monday.getTime() + 4 * DAY_MS);
  let year = friday.getUTCFullYear();
  let month = friday.getUTCMonth() + 1;
  if (friday.getUTCDate() > 25) {
    month += 1;
    if (month === 13) {
      month = 1;
      year += 1;
    }
  }
  return `${year}-${String(month).padStart(2, "0")}`;
}

export function weeksForCompetencia(month: string): string[] {
  const match = /^(\d{4})-(\d{2})$/.exec(month);
  if (!match) throw new Error("Competência inválida.");
  const year = Number(match[1]);
  const monthIndex = Number(match[2]) - 1;
  const first = new Date(Date.UTC(year, monthIndex, 1));
  const last = new Date(Date.UTC(year, monthIndex + 1, 0));
  let cursor = mondayOf(new Date(first.getTime() - 35 * DAY_MS));
  const end = mondayOf(new Date(last.getTime() + 35 * DAY_MS));
  const weeks: string[] = [];

  while (cursor <= end) {
    const value = isoDate(cursor);
    if (competenciaFromWeek(value) === month) weeks.push(value);
    cursor = new Date(cursor.getTime() + 7 * DAY_MS);
  }
  return weeks.slice(-4);
}

export function isWeekAfterStart(startDate: string, weekStart: string): boolean {
  const start = parseIsoDate(startDate);
  const week = parseIsoDate(weekStart);
  if (!start || !week) return false;
  return week > mondayOf(start);
}

export function isWeekBeforeOrOnTermination(terminationDate: string, weekStart: string): boolean {
  if (!terminationDate) return true;
  const termination = parseIsoDate(terminationDate);
  const week = parseIsoDate(weekStart);
  return Boolean(termination && week && week <= termination);
}

export function eligibleWeeks(
  hireDate: string,
  terminationDate: string,
  weeks: string[],
): string[] {
  return weeks.filter(
    (week) => isWeekAfterStart(hireDate, week) && isWeekBeforeOrOnTermination(terminationDate, week),
  );
}

export function yearsInCompany(hireDate: string, reference: Date): number {
  const hire = parseIsoDate(hireDate);
  if (!hire) return 0;
  let years = reference.getUTCFullYear() - hire.getUTCFullYear();
  const anniversary = new Date(Date.UTC(reference.getUTCFullYear(), hire.getUTCMonth(), hire.getUTCDate()));
  if (reference < anniversary) years -= 1;
  return Math.max(0, years);
}

export function monthReferenceDate(month: string): Date {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Date(Date.UTC(year, monthNumber, 0));
}
