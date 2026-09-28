"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp, BadgeDollarSign, Plus } from "lucide-react";

import { addBonusAdjustmentAction } from "@/app/actions/evaluations";
import { SubmitButton } from "@/components/submit-button";
import { brl } from "@/lib/money";

export function FinancialAdjustmentForm({ employeeId, weekStart }: { employeeId: number; weekStart: string }) {
  const [type, setType] = useState<"addition" | "deduction">("addition");
  const [amount, setAmount] = useState("");
  const numericAmount = Number(amount.replace(",", "."));
  const preview = Number.isFinite(numericAmount) && numericAmount > 0 ? numericAmount : 0;

  return (
    <form action={addBonusAdjustmentAction} className="panel financial-adjustment-form">
      <input type="hidden" name="employee_id" value={employeeId} />
      <input type="hidden" name="week_start" value={weekStart} />
      <div className="panel-head">
        <div><h3>Ajuste financeiro</h3><p>Inclua um adicional ou desconto avulso no fechamento.</p></div>
        <span className={`adjustment-direction ${type}`} aria-label={type === "addition" ? "Adicional" : "Desconto"}>
          {type === "addition" ? <ArrowUp size={17} /> : <ArrowDown size={17} />}
        </span>
      </div>
      <div className="form-grid">
        <div className="field span-4">
          <label>Operação</label>
          <select name="adjustment_type" value={type} onChange={(event) => setType(event.target.value as "addition" | "deduction")}>
            <option value="addition">Acrescentar</option>
            <option value="deduction">Diminuir</option>
          </select>
        </div>
        <div className="field span-4">
          <label>Valor (R$)</label>
          <input name="amount" type="number" inputMode="decimal" min="0.01" max="100000" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="0,00" required />
        </div>
        <div className="field span-12">
          <label>Descrição *</label>
          <textarea name="description" minLength={3} maxLength={240} placeholder="Ex.: apoio em inventário, campanha especial ou correção de fechamento" required />
        </div>
      </div>
      <div className={`adjustment-preview ${type}`}>
        <BadgeDollarSign size={18} />
        <div><strong>{type === "addition" ? "+" : "−"}{brl(preview)}</strong><span>Altera somente o valor financeiro; as notas permanecem iguais.</span></div>
      </div>
      <SubmitButton className="button primary wide"><Plus size={16} /> Registrar ajuste</SubmitButton>
    </form>
  );
}
