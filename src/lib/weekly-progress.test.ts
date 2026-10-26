import { describe, expect, it } from "vitest";
import { weeklyProgress } from "@/lib/weekly-progress";
import type { Employee } from "@/lib/types";

describe("progresso semanal", () => {
  const employees = [{ id: 1, hire_date: "2026-10-05" }, { id: 2, hire_date: "2026-10-12" }] as Employee[];

  it("usa a elegibilidade de cada semana e ignora avaliações duplicadas ou fora do filtro", () => {
    expect(weeklyProgress(["2026-10-05", "2026-10-12"], employees, [
      { employee_id: 1, week_start: "2026-10-05" },
      { employee_id: 2, week_start: "2026-10-05" },
      { employee_id: 1, week_start: "2026-10-12 " },
      { employee_id: 1, week_start: "2026-10-12" },
      { employee_id: 99, week_start: "2026-10-12" },
    ])).toEqual({
      "2026-10-05": { completed: 1, total: 1, percent: 100 },
      "2026-10-12": { completed: 1, total: 2, percent: 50 },
    });
  });

  it("mantém zero quando não há colaboradores elegíveis", () => {
    expect(weeklyProgress(["2026-09-28"], employees, [])).toEqual({ "2026-09-28": { completed: 0, total: 0, percent: 0 } });
  });
});
