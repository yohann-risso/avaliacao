"use client";

import { useState } from "react";

import { addWeeklyOccurrenceAction } from "@/app/actions/evaluations";
import { SubmitButton } from "@/components/submit-button";
import { EVALUATION_RULES, type RuleCategory } from "@/lib/rules";

const categories: RuleCategory[] = ["ASSIDUIDADE", "QUALIDADE", "PRODUTIVIDADE", "COMPORTAMENTO"];

function points(value: number): string {
  return new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(value);
}

export function OccurrenceForm({ employeeId, weekStart }: { employeeId: number; weekStart: string }) {
  const [code, setCode] = useState(EVALUATION_RULES[0].code);
  const rule = EVALUATION_RULES.find((item) => item.code === code) || EVALUATION_RULES[0];

  return (
    <form action={addWeeklyOccurrenceAction} className="card">
      <input type="hidden" name="employee_id" value={employeeId} />
      <input type="hidden" name="week_start" value={weekStart} />
      <div className="form-grid">
        <div className="field span-9">
          <label>Código e ocorrência</label>
          <select name="occurrence_code" value={code} onChange={(event) => setCode(event.target.value)}>
            {categories.map((category) => (
              <optgroup key={category} label={category}>
                {EVALUATION_RULES.filter((item) => item.category === category).map((item) => (
                  <option key={item.code} value={item.code}>{item.code} · {item.occurrence}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
        <div className="field span-3"><label>Quantidade</label><input type="number" name="qty" min="1" max="31" defaultValue="1" required /></div>
        <div className="field span-12"><label>Observação</label><textarea name="occurrence_notes" placeholder="Contexto, data ou evidência da ocorrência" /></div>
      </div>
      <div className="notice info" style={{ marginTop: 14 }}>
        <strong>{rule.code} · {rule.category} · {rule.level}</strong><br />
        Referência: {points(rule.points)} ponto(s) de desconto. {rule.directive}
      </div>
      <div className="actions" style={{ marginTop: 14 }}><SubmitButton>Registrar ocorrência</SubmitButton></div>
    </form>
  );
}
