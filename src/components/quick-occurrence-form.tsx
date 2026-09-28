"use client";

import { useState } from "react";
import { AlertTriangle, Plus } from "lucide-react";

import { addWeeklyOccurrenceAction } from "@/app/actions/evaluations";
import { SubmitButton } from "@/components/submit-button";
import { dateBr } from "@/lib/dates";
import { EVALUATION_RULES, type RuleCategory } from "@/lib/rules";

const categories: RuleCategory[] = ["ASSIDUIDADE", "QUALIDADE", "PRODUTIVIDADE", "COMPORTAMENTO"];

export function QuickOccurrenceForm({
  employees,
  weeks,
  returnTo,
}: {
  employees: Array<{ id: number; name: string; sector: string }>;
  weeks: string[];
  returnTo: string;
}) {
  const [code, setCode] = useState(EVALUATION_RULES[0].code);
  const [quantity, setQuantity] = useState(1);
  const rule = EVALUATION_RULES.find((item) => item.code === code) || EVALUATION_RULES[0];
  return (
    <form action={addWeeklyOccurrenceAction} className="panel quick-occurrence-form">
      <input type="hidden" name="return_to" value={returnTo} />
      <div className="panel-head"><div><p className="eyebrow">Lançamento rápido</p><h2>Registrar ocorrência</h2><p>O registro entra imediatamente no cálculo da semana.</p></div><span className={`rule-code ${rule.level === "CRITICO" ? "danger" : rule.level === "ALTO" ? "warning" : ""}`}>{rule.code}</span></div>
      <div className="form-grid">
        <div className="field span-4"><label>Colaborador</label><select name="employee_id" required>{employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.name} · {employee.sector}</option>)}</select></div>
        <div className="field span-3"><label>Semana</label><select name="week_start" defaultValue={weeks.at(-1)}>{weeks.map((week, index) => <option key={week} value={week}>S{index + 1} · {dateBr(week)}</option>)}</select></div>
        <div className="field span-4"><label>Regra</label><select name="occurrence_code" value={code} onChange={(event) => setCode(event.target.value)}>{categories.map((category) => <optgroup key={category} label={category}>{EVALUATION_RULES.filter((item) => item.category === category).map((item) => <option key={item.code} value={item.code}>{item.code} · {item.occurrence}</option>)}</optgroup>)}</select></div>
        <div className="field span-1"><label>Qtd.</label><input type="number" name="qty" min="1" max="31" value={quantity} onChange={(event) => setQuantity(Math.max(1, Number(event.target.value) || 1))} required /></div>
        <div className="field span-9"><label>Contexto ou evidência</label><input name="occurrence_notes" placeholder="Data, situação observada ou documento relacionado" /></div>
        <div className="span-actions"><SubmitButton><Plus size={16} /> Registrar e recalcular</SubmitButton></div>
      </div>
      <div className="rule-preview compact"><AlertTriangle size={17} /><div><strong>{(rule.points * quantity).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} pontos/R$ de referência</strong><p>{rule.directive}</p></div></div>
    </form>
  );
}
