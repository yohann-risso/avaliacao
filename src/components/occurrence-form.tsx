"use client";

import { useState } from "react";
import { AlertTriangle, Plus } from "lucide-react";

import { addWeeklyOccurrenceAction } from "@/app/actions/evaluations";
import { SubmitButton } from "@/components/submit-button";
import { WEEKLY_CRITERIA } from "@/lib/constants";
import { EVALUATION_RULES, type RuleCategory } from "@/lib/rules";

const categories: RuleCategory[] = ["ASSIDUIDADE", "QUALIDADE", "PRODUTIVIDADE", "COMPORTAMENTO"];

function points(value: number): string {
  return new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(value);
}

export function OccurrenceForm({ employeeId, weekStart }: { employeeId: number; weekStart: string }) {
  const [code, setCode] = useState(EVALUATION_RULES[0].code);
  const [quantity, setQuantity] = useState(1);
  const rule = EVALUATION_RULES.find((item) => item.code === code) || EVALUATION_RULES[0];
  const affected = WEEKLY_CRITERIA.filter((criterion) => Number(rule.weeklyDiscounts[criterion.key] || 0) > 0);

  return (
    <form action={addWeeklyOccurrenceAction} className="panel occurrence-form-card">
      <input type="hidden" name="employee_id" value={employeeId} />
      <input type="hidden" name="week_start" value={weekStart} />
      <div className="panel-head"><div><h3>Nova ocorrência</h3><p>Escolha o código; o desconto é recalculado ao salvar.</p></div><span className={`rule-code ${rule.level === "CRITICO" ? "danger" : rule.level === "ALTO" ? "warning" : ""}`}>{rule.code}</span></div>
      <div className="form-grid">
        <div className="field span-9"><label>Código e motivo</label><select name="occurrence_code" value={code} onChange={(event) => setCode(event.target.value)}>{categories.map((category) => <optgroup key={category} label={category}>{EVALUATION_RULES.filter((item) => item.category === category).map((item) => <option key={item.code} value={item.code}>{item.code} · {item.occurrence}</option>)}</optgroup>)}</select></div>
        <div className="field span-3"><label>Quantidade</label><input type="number" name="qty" min="1" max="31" value={quantity} onChange={(event) => setQuantity(Math.max(1, Number(event.target.value) || 1))} required /></div>
        <div className="field span-12"><label>Contexto ou evidência</label><textarea name="occurrence_notes" placeholder="Data, situação observada ou documento relacionado" /></div>
      </div>
      <div className="rule-preview">
        <AlertTriangle size={18} />
        <div><strong>{points(rule.points * quantity)} ponto(s) de desconto</strong><p>{rule.directive}</p><div className="actions">{affected.map((criterion) => <span className="badge warning" key={criterion.key}>{criterion.label}: -{Math.min(100, Number(rule.weeklyDiscounts[criterion.key]) * quantity)}%</span>)}</div></div>
      </div>
      <SubmitButton className="button primary wide"><Plus size={16} /> Registrar ocorrência</SubmitButton>
    </form>
  );
}
