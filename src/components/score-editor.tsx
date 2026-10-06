"use client";

import { useMemo, useState } from "react";
import { Banknote, Check, Save, SkipForward, Sparkles } from "lucide-react";

import { saveWeeklyEvaluationAction } from "@/app/actions/evaluations";
import { SubmitButton } from "@/components/submit-button";
import { WEEKLY_CRITERIA, type WeeklyCriterionKey } from "@/lib/constants";
import { brl, pct, totalAfterFinancialAdjustments, weeklyPaymentBreakdown } from "@/lib/money";
import type { WeeklyError } from "@/lib/types";

type EvaluationDraft = Record<string, string | number | null>;

export function ScoreEditor({
  employeeId,
  week,
  evaluation,
  occurrences,
  evaluatorNames,
  selectedEvaluator,
  nextEmployeeId,
  adjustmentTotal,
  readOnly = false,
}: {
  employeeId: number;
  week: string;
  evaluation: EvaluationDraft | null;
  occurrences: WeeklyError[];
  evaluatorNames: string[];
  selectedEvaluator: string;
  nextEmployeeId?: number;
  adjustmentTotal: number;
  readOnly?: boolean;
}) {
  const [scores, setScores] = useState<Record<WeeklyCriterionKey, number>>(() => Object.fromEntries(
    WEEKLY_CRITERIA.map((criterion) => [criterion.key, Number(evaluation?.[`${criterion.key}_pct`] ?? 100)]),
  ) as Record<WeeklyCriterionKey, number>);
  const preview = useMemo(() => {
    const row: Record<string, number> = {};
    for (const criterion of WEEKLY_CRITERIA) row[`${criterion.key}_pct`] = scores[criterion.key];
    return weeklyPaymentBreakdown(row, occurrences);
  }, [scores, occurrences]);
  const finalTotal = totalAfterFinancialAdjustments(preview.total, [{ amount: adjustmentTotal }]);
  const average = WEEKLY_CRITERIA.reduce((sum, criterion) => sum + scores[criterion.key], 0) / WEEKLY_CRITERIA.length;

  function setScore(key: WeeklyCriterionKey, value: number) {
    setScores((current) => ({ ...current, [key]: Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0)) }));
  }

  return (
    <form action={readOnly ? undefined : saveWeeklyEvaluationAction} className="evaluation-editor">
      <input type="hidden" name="employee_id" value={employeeId} />
      <input type="hidden" name="week_start" value={week} />
      <section className="panel evaluation-score-panel">
        <div className="panel-head evaluation-panel-head">
          <div><p className="eyebrow">{readOnly ? "Consulta da semana" : "Avaliação da semana"}</p><h2>Resultado por quesito</h2><p>{readOnly ? "Registro consolidado, disponível somente para consulta." : "A nota define a faixa; ocorrências aplicam o desconto depois."}</p></div>
          <div className="score-summary"><small>Média atual</small><strong>{pct(average)}</strong></div>
        </div>

        <div className="score-grid">
          {WEEKLY_CRITERIA.map((criterion) => {
            const score = scores[criterion.key];
            const payment = preview.byCriterion[criterion.key];
            const discounted = payment.gross > payment.paid;
            return (
              <article className={`score-card ${discounted ? "discounted" : ""}`} key={criterion.key}>
                <header><div><span>{criterion.label}</span><small>até {brl(criterion.monthlyCap)} / mês</small></div><strong>{score.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%</strong></header>
                <input aria-label={`${criterion.label} em porcentagem`} className="score-range" type="range" min="0" max="100" step="0.1" value={score} onChange={(event) => setScore(criterion.key, Number(event.target.value))} disabled={readOnly} />
                <div className="quick-scores" aria-label={`Atalhos de ${criterion.label}`}>
                  {[100, 90, 80, 70, 50].map((value) => <button className={score === value ? "active" : ""} type="button" key={value} onClick={() => setScore(criterion.key, value)} disabled={readOnly}>{value}</button>)}
                  <input type="number" name={`${criterion.key}_pct`} min="0" max="100" step="0.1" value={score} onChange={(event) => setScore(criterion.key, Number(event.target.value))} readOnly={readOnly} required />
                </div>
                <div className="score-payment"><span>{discounted ? "Após ocorrência" : "Prévia semanal"}</span><strong>{brl(payment.paid)}</strong>{discounted ? <small>-{brl(payment.gross - payment.paid)}</small> : <Check size={15} />}</div>
                <label className="field justification-field"><span>Justificativa {score < 100 && !readOnly ? "*" : ""}</span><textarea name={`${criterion.key}_just`} defaultValue={String(evaluation?.[`${criterion.key}_just`] || "")} placeholder={score < 100 ? "Explique o resultado abaixo de 100%" : "Opcional"} readOnly={readOnly} required={score < 100 && !readOnly} /></label>
              </article>
            );
          })}
        </div>

        <div className="form-grid evaluation-meta">
          <div className="field span-3"><label>Itens executados</label><input type="number" name="items_count" min="0" defaultValue={Number(evaluation?.items_count || 0)} readOnly={readOnly} required /></div>
          <div className="field span-3"><label>Avaliador *</label>{readOnly ? <input value={selectedEvaluator || "Não informado"} readOnly /> : <select name="evaluator" defaultValue={selectedEvaluator} required>{evaluatorNames.map((name) => <option key={name} value={name}>{name}</option>)}</select>}</div>
          <div className="field span-6"><label>Observações gerais</label><textarea name="notes" defaultValue={String(evaluation?.notes || "")} placeholder="Contexto geral da semana" readOnly={readOnly} /></div>
        </div>
        {!readOnly && !evaluatorNames.length ? <div className="notice error">Nenhum avaliador disponível. Vincule o usuário a uma liderança ativa.</div> : null}
      </section>

      <aside className="panel payment-rail">
        <div className="payment-rail-title"><span className="metric-icon green"><Banknote size={18} /></span><div><p className="eyebrow">Prévia em tempo real</p><h2>Bonificação semanal</h2></div></div>
        <div className="payment-total"><small>Valor após regras e ajustes</small><strong>{brl(finalTotal)}</strong><span>{brl(preview.total)} após as regras</span></div>
        <div className="payment-breakdown">
          {WEEKLY_CRITERIA.map((criterion) => {
            const item = preview.byCriterion[criterion.key];
            return <div key={criterion.key}><span>{criterion.label}</span><strong>{brl(item.paid)}</strong>{item.gross > item.paid ? <small>-{brl(item.gross - item.paid)}</small> : null}</div>;
          })}
          {adjustmentTotal !== 0 ? <div className="manual-adjustment-row"><span>Ajustes manuais</span><strong className={adjustmentTotal > 0 ? "success-text" : "danger-text"}>{adjustmentTotal > 0 ? "+" : "−"}{brl(Math.abs(adjustmentTotal))}</strong></div> : null}
        </div>
        <div className={`impact-callout ${preview.discount ? "warning" : "success"}`}><Sparkles size={17} /><div><strong>{preview.discount ? `${brl(preview.discount)} descontados` : "Sem descontos"}</strong><span>{preview.occurrencePoints.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} pontos de ocorrência</span></div></div>
        {!readOnly ? <div className="sticky-actions">
          <SubmitButton className="button primary wide"><Save size={16} /> Salvar avaliação</SubmitButton>
          {nextEmployeeId ? <SubmitButton className="button secondary wide" name="next_employee_id" value={nextEmployeeId}><SkipForward size={16} /> Salvar e ir ao próximo</SubmitButton> : null}
        </div> : <div className="notice info">Acesso do RH em modo de consulta.</div>}
      </aside>
    </form>
  );
}
