"use client";

import { Check } from "lucide-react";
import { useState } from "react";

import { competenciaFromWeek, dateBr, isoDate, parseIsoDate, weeksForCompetencia } from "@/lib/dates";

export function EvaluationWeekPicker({ week }: { week: string }) {
  const initialMonth = competenciaFromWeek(week);
  const [month, setMonth] = useState(initialMonth);
  const [selectedWeek, setSelectedWeek] = useState(week);
  const weeks = weeksForCompetencia(month);

  // Keep existing links usable even when their week precedes the four-week window.
  if (month === initialMonth && !weeks.includes(week)) weeks.unshift(week);

  return (
    <>
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
            setMonth(value);
            setSelectedWeek(weeksForCompetencia(value)[0]);
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
            return (
              <label className="evaluation-week-option" key={start}>
                <input type="radio" name="week" value={start} checked={selected} onChange={() => setSelectedWeek(start)} />
                <span className="evaluation-week-title">Semana {index + 1}<Check size={14} aria-hidden="true" /></span>
                <span className="evaluation-week-range">{dateBr(start).slice(0, 5)} a {dateBr(friday).slice(0, 5)}</span>
              </label>
            );
          })}
        </div>
      </fieldset>
    </>
  );
}
