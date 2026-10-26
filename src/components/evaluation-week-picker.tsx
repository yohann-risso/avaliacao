"use client";

import Link from "next/link";
import { Check, Download } from "lucide-react";
import { useState } from "react";
import { flushSync } from "react-dom";

import { competenciaFromWeek, dateBr, isoDate, parseIsoDate, weeksForCompetencia } from "@/lib/dates";
import type { WeeklyProgress } from "@/lib/weekly-progress";

export function EvaluationWeekPicker({ week, employeeId, employees, progress }: {
  week: string;
  employeeId: number;
  employees: { id: number; name: string; sector: string }[];
  progress: Record<string, WeeklyProgress>;
}) {
  const initialMonth = competenciaFromWeek(week);
  const [month, setMonth] = useState(initialMonth);
  const [selectedWeek, setSelectedWeek] = useState(week);
  const weeks = weeksForCompetencia(month);

  // Keep existing links usable even when their week precedes the four-week window.
  if (month === initialMonth && !weeks.includes(week)) weeks.unshift(week);

  return (
    <form method="get" action="/avaliacoes" className="filter-bar wrap">
      <div className="field compact">
        <label htmlFor="evaluation-month">Competência</label>
        <input
          id="evaluation-month"
          type="month"
          value={month}
          required
          onChange={(event) => {
            const value = event.target.value;
            if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(value)) return;
            flushSync(() => {
              setMonth(value);
              setSelectedWeek(weeksForCompetencia(value)[0]);
            });
            event.currentTarget.form?.requestSubmit();
          }}
        />
      </div>
      <fieldset className="evaluation-weeks">
        <legend>Semana da competência</legend>
        <div className="evaluation-week-options">
          {weeks.map((start, index) => {
            const monday = parseIsoDate(start)!;
            const friday = isoDate(new Date(monday.getTime() + 4 * 86_400_000));
            const selected = selectedWeek === start;
            const status = progress[start];
            return (
              <label className="evaluation-week-option" key={start}>
                <input
                  type="radio"
                  name="week"
                  value={start}
                  checked={selected}
                  onChange={(event) => {
                    flushSync(() => setSelectedWeek(start));
                    event.currentTarget.form?.requestSubmit();
                  }}
                  onClick={(event) => {
                    // Also load a preselected week after changing the competence.
                    if (selected) event.currentTarget.form?.requestSubmit();
                  }}
                />
                <span className="evaluation-week-title">Semana {index + 1}<Check size={14} aria-hidden="true" /></span>
                <span className="evaluation-week-range">{dateBr(start).slice(0, 5)} a {dateBr(friday).slice(0, 5)}</span>
                {status ? <>
                  <span className={`evaluation-week-track ${status.total > 0 && status.completed === status.total ? "complete" : ""}`} aria-hidden="true"><span style={{ width: `${status.percent}%` }} /></span>
                  <span className="evaluation-week-progress"><span>{status.completed}/{status.total} concluídas</span><span>{status.percent}%</span></span>
                </> : <span className="evaluation-week-progress">Carregando progresso…</span>}
              </label>
            );
          })}
        </div>
      </fieldset>
      <div className="field compact grow"><label htmlFor="evaluation-employee">Colaborador</label><select id="evaluation-employee" name="employee" defaultValue={employeeId} onChange={(event) => event.currentTarget.form?.requestSubmit()}>{employees.map((employee) => <option value={employee.id} key={employee.id}>{employee.name} · {employee.sector}</option>)}</select></div>
      <button className="button secondary" type="submit">Carregar</button>
      <Link className="button ghost" href={`/api/export/avaliacoes?week=${week}`}><Download size={16} /> Planilha</Link>
      <span className="filter-context">{progress[week].completed}/{progress[week].total} concluídas</span>
    </form>
  );
}
