import { describe, expect, it } from "vitest";

import { eligibleWeeks, isWeekOnOrAfterStart } from "@/lib/dates";

describe("elegibilidade semanal por data de contratação", () => {
  const weeks = ["2026-10-05", "2026-10-12", "2026-10-19", "2026-10-26"];

  it("inclui a semana quando a contratação ocorre na própria data da semana", () => {
    expect(isWeekOnOrAfterStart("2026-10-12", "2026-10-12")).toBe(true);
    expect(eligibleWeeks("2026-10-12", "", weeks)).toEqual(["2026-10-12", "2026-10-19", "2026-10-26"]);
  });

  it("ignora semanas anteriores à contratação", () => {
    expect(isWeekOnOrAfterStart("2026-10-13", "2026-10-12")).toBe(false);
    expect(eligibleWeeks("2026-10-13", "", weeks)).toEqual(["2026-10-19", "2026-10-26"]);
  });

  it("mantém o limite da data de desligamento", () => {
    expect(eligibleWeeks("2026-10-05", "2026-10-19", weeks)).toEqual(["2026-10-05", "2026-10-12", "2026-10-19"]);
  });
});
