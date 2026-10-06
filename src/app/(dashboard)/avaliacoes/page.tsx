import Link from "next/link";
import { Check, ClipboardCheck, Download, FileSpreadsheet, Trash2, TriangleAlert } from "lucide-react";

import { deleteBonusAdjustmentAction, deleteWeeklyOccurrenceAction, importWeeklyWorkbookAction } from "@/app/actions/evaluations";
import { FinancialAdjustmentForm } from "@/components/financial-adjustment-form";
import { Notice } from "@/components/notice";
import { OccurrenceForm } from "@/components/occurrence-form";
import { PageHeader } from "@/components/page-header";
import { ScoreEditor } from "@/components/score-editor";
import { SubmitButton } from "@/components/submit-button";
import { requireUser } from "@/lib/auth";
import { dateBr, normalizeMonday, todayBrazil } from "@/lib/dates";
import { getWeeklyEvaluation, listActiveEmployees, listEvaluators, listWeeklyBonusAdjustments, listWeeklyErrors, listWeeklyEvaluations } from "@/lib/data";
import { brl, financialAdjustmentTotal, weeklyPaymentBreakdown } from "@/lib/money";
import { canEditEvaluationsRole, isTeamScopedRole, userRoleLabel } from "@/lib/permissions";
import { aggregateOccurrenceQuantities, getEvaluationRule, monthlyOccurrenceImpact, weeklyOccurrenceImpact } from "@/lib/rules";
import { employeesVisibleTo } from "@/lib/employee-access";

function safeWeek(value?: string): string {
  try { return normalizeMonday(value || todayBrazil()); } catch { return normalizeMonday(todayBrazil()); }
}

export default async function EvaluationsPage({
  searchParams,
}: {
  searchParams: Promise<{ week?: string; employee?: string; success?: string; error?: string }>;
}) {
  const [user, params] = await Promise.all([requireUser(), searchParams]);
  const canEditEvaluations = canEditEvaluationsRole(user.role);
  const [allEmployees, evaluators] = await Promise.all([
    listActiveEmployees(),
    user.role === "admin" ? listEvaluators() : Promise.resolve([]),
  ]);
  const employees = employeesVisibleTo(user, allEmployees).filter((employee) => !employee.is_leadership);
  const employeeIds = employees.map((employee) => employee.id);
  const week = safeWeek(params.week);
  const requestedEmployee = Number(params.employee);
  const selected = employees.find((employee) => employee.id === requestedEmployee) || employees[0];
  const employeeId = selected?.id || 0;
  const [evaluation, occurrences, adjustments, weekEvaluations] = employeeId
    ? await Promise.all([getWeeklyEvaluation(employeeId, week), listWeeklyErrors(employeeId, week), listWeeklyBonusAdjustments(employeeId, week), listWeeklyEvaluations([week], employeeIds)])
    : [null, [], [], []];
  const evaluatorNames = isTeamScopedRole(user.role) ? (user.evaluator_name ? [user.evaluator_name] : []) : evaluators.map((employee) => employee.name);
  const selectedEvaluator = isTeamScopedRole(user.role)
    ? user.evaluator_name
    : String(evaluation?.evaluator || evaluatorNames[0] || "");
  const evaluatedByEmployee = new Map(weekEvaluations.map((item) => [item.employee_id, item]));
  const selectedIndex = Math.max(0, employees.findIndex((item) => item.id === employeeId));
  const afterSelected = [...employees.slice(selectedIndex + 1), ...employees.slice(0, selectedIndex)];
  const nextEmployee = afterSelected.find((item) => !evaluatedByEmployee.has(item.id)) || afterSelected[0];
  const scoreRow: Record<string, unknown> = { week_start: week };
  const preview = weeklyPaymentBreakdown(evaluation || scoreRow, occurrences);
  const weeklyImpact = weeklyOccurrenceImpact(occurrences);
  const weeklyPenalties = [...aggregateOccurrenceQuantities(occurrences)].map(([code, quantity]) => ({
    code,
    quantity,
    rule: getEvaluationRule(code),
  }));
  const monthlyImpact = monthlyOccurrenceImpact(occurrences);
  const adjustmentTotal = financialAdjustmentTotal(adjustments);
  const completed = weekEvaluations.length;

  return (
    <>
      <PageHeader step="Operação semanal" title={canEditEvaluations ? "Cockpit de avaliações" : "Consulta de avaliações"} subtitle={canEditEvaluations ? "Avalie, aplique regras e acompanhe o impacto sem sair da mesma tela." : "Consulte notas, justificativas, ocorrências e valores consolidados, sem alterar os lançamentos."} icon={ClipboardCheck} user={`${user.username} · ${userRoleLabel(user.role)}`} />
      <Notice success={params.success} error={params.error} />

      <form method="get" className="filter-bar">
        <div className="field compact"><label>Semana operacional</label><input type="date" name="week" defaultValue={week} /></div>
        <div className="field compact grow"><label>Colaborador</label><select name="employee" defaultValue={employeeId}>{employees.map((employee) => <option value={employee.id} key={employee.id}>{employee.name} · {employee.sector}</option>)}</select></div>
        <button className="button secondary" type="submit">Carregar</button>
        <Link className="button ghost" href={`/api/export/avaliacoes?week=${week}`}><Download size={16} /> Planilha</Link>
        <span className="filter-context">{completed}/{employees.length} concluídas</span>
      </form>

      {!selected ? <div className="notice info">{isTeamScopedRole(user.role) ? "Nenhum funcionário ativo está vinculado à sua liderança." : "Cadastre ao menos um funcionário operacional ativo."}</div> : (
        <>
          <section className="employee-focus-bar">
            <span className="user-avatar large">{selected.name.slice(0, 2).toUpperCase()}</span>
            <div><p className="eyebrow">Em avaliação</p><h2>{selected.name}</h2><span>{selected.sector} · {selected.role}</span></div>
            <div className="focus-meta"><span><small>Semana</small><strong>{dateBr(week)}</strong></span><span><small>Status</small><strong className={evaluation ? "success-text" : "warning-text"}>{evaluation ? "Avaliado" : "Pendente"}</strong></span><span><small>Ocorrências</small><strong>{occurrences.reduce((sum, item) => sum + Number(item.qty), 0)}</strong></span></div>
          </section>

          <div className="evaluation-layout">
            <aside className="panel employee-queue">
              <div className="panel-head"><div><p className="eyebrow">Fila da semana</p><h2>{employees.length} pessoas</h2></div><span className="badge success">{completed} feitas</span></div>
              <div className="queue-progress"><span style={{ width: `${employees.length ? (completed / employees.length) * 100 : 0}%` }} /></div>
              <div className="queue-list">
                {employees.map((employee) => {
                  const done = evaluatedByEmployee.has(employee.id);
                  return <Link className={employee.id === selected.id ? "active" : ""} href={`/avaliacoes?week=${week}&employee=${employee.id}`} key={employee.id}><span className={`queue-status ${done ? "done" : ""}`}>{done ? <Check size={14} /> : null}</span><div><strong>{employee.name}</strong><small>{employee.sector}</small></div><span className={`status-chip ${done ? "success" : "warning"}`}>{done ? "Feito" : "Pendente"}</span></Link>;
                })}
              </div>
            </aside>

            {!canEditEvaluations && !evaluation ? <section className="panel evaluation-score-panel"><div className="empty-state"><ClipboardCheck size={28} /><strong>Nenhuma avaliação registrada</strong><span>Este colaborador ainda não possui avaliação na semana selecionada.</span></div></section> : <ScoreEditor key={`${selected.id}:${week}`} employeeId={selected.id} week={week} evaluation={evaluation} occurrences={occurrences} evaluatorNames={evaluatorNames} selectedEvaluator={selectedEvaluator} nextEmployeeId={nextEmployee?.id} adjustmentTotal={adjustmentTotal} readOnly={!canEditEvaluations} />}
          </div>

          <section className="section occurrence-workspace">
            <div className="section-head"><div><p className="eyebrow">Regras e valores avulsos</p><h2 className="section-title">Ocorrências, descontos e ajustes</h2><p className="muted">As ocorrências seguem a tabela corporativa; ajustes manuais alteram apenas o valor financeiro e exigem descrição.</p></div><Link className="button ghost" href="/regras">Consultar tabela completa</Link></div>
            <div className={canEditEvaluations ? "grid two occurrence-grid" : "occurrence-grid"}>
              {canEditEvaluations ? <OccurrenceForm key={`${selected.id}:${week}`} employeeId={selected.id} weekStart={week} /> : null}
              <div className="panel occurrence-log">
                <div className="panel-head"><div><h3>Registros da semana</h3><p>{occurrences.length ? `${weeklyImpact.recognizedQuantity} ocorrência(s) reconhecida(s)` : "Nenhum desconto aplicado"}</p></div><strong className={preview.discount ? "danger-text" : "success-text"}>-{brl(preview.discount)}</strong></div>
                {weeklyPenalties.length ? <div className="penalty-totals" aria-label="Penalidades somadas por código">{weeklyPenalties.map(({ code, quantity, rule }) => <span key={code}><b>{code}</b>{quantity} × {(rule?.points || 0).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} = <strong>{((rule?.points || 0) * quantity).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} pts</strong></span>)}</div> : null}
                {occurrences.length ? <div className="occurrence-items">{occurrences.map((item) => {
                  const rule = getEvaluationRule(item.error_type);
                  return <article key={item.id}><span className={`rule-code ${item.severity === "CRITICO" ? "danger" : item.severity === "ALTO" ? "warning" : ""}`}>{item.error_type}</span><div><strong>{rule?.occurrence || item.error_type}</strong><p>{item.qty} × {(rule?.points || 0).toLocaleString("pt-BR")} pts{item.notes ? ` · ${item.notes}` : ""}</p></div>{canEditEvaluations ? <form action={deleteWeeklyOccurrenceAction}><input type="hidden" name="id" value={item.id} /><input type="hidden" name="employee_id" value={selected.id} /><input type="hidden" name="week_start" value={week} /><button className="icon-button danger" type="submit" aria-label="Remover ocorrência"><Trash2 size={15} /></button></form> : null}</article>;
                })}</div> : <div className="empty-state compact"><Check size={25} /><strong>Semana sem ocorrências</strong><span>A bonificação depende apenas das notas.</span></div>}
                {monthlyImpact.a01Quantity ? <div className="impact-callout warning"><TriangleAlert size={17} /><div><strong>A01 no mês: {monthlyImpact.a01Quantity}</strong><span>{monthlyImpact.blocksMonthlyBase ? "Reincidência: bônus-base mensal bloqueado." : "Assiduidade mensal afetada; nova A01 bloqueia o bônus-base."}</span></div></div> : null}
              </div>
            </div>
            <div className={canEditEvaluations ? "grid two occurrence-grid adjustment-grid" : "occurrence-grid adjustment-grid"}>
              {canEditEvaluations ? <FinancialAdjustmentForm key={`adjustment:${selected.id}:${week}`} employeeId={selected.id} weekStart={week} /> : null}
              <div className="panel occurrence-log adjustment-log">
                <div className="panel-head"><div><h3>Ajustes da semana</h3><p>{adjustments.length ? `${adjustments.length} lançamento(s) com descrição` : "Nenhum valor avulso lançado"}</p></div><strong className={adjustmentTotal > 0 ? "success-text" : adjustmentTotal < 0 ? "danger-text" : "muted"}>{adjustmentTotal > 0 ? "+" : adjustmentTotal < 0 ? "−" : ""}{brl(Math.abs(adjustmentTotal))}</strong></div>
                {adjustments.length ? <div className="occurrence-items adjustment-items">{adjustments.map((item) => {
                  const amount = Number(item.amount);
                  return <article key={item.id}><span className={`adjustment-sign ${amount > 0 ? "addition" : "deduction"}`}>{amount > 0 ? "+" : "−"}</span><div><strong>{item.description}</strong><p>{amount > 0 ? "Adicional" : "Desconto"} de {brl(Math.abs(amount))} · por {item.created_by_username || "sistema"}</p></div>{canEditEvaluations ? <form action={deleteBonusAdjustmentAction}><input type="hidden" name="id" value={item.id} /><input type="hidden" name="employee_id" value={selected.id} /><input type="hidden" name="week_start" value={week} /><button className="icon-button danger" type="submit" aria-label="Remover ajuste"><Trash2 size={15} /></button></form> : null}</article>;
                })}</div> : <div className="empty-state compact"><Check size={25} /><strong>Sem ajustes manuais</strong><span>O total usa somente avaliação, regras e adicionais fixos.</span></div>}
              </div>
            </div>
          </section>

          {canEditEvaluations ? <section className="section">
            <details className="panel import-panel">
              <summary><span className="metric-icon blue"><FileSpreadsheet size={18} /></span><span><strong>Importação em lote</strong><small>Use o modelo XLSX para avaliar várias pessoas de uma vez.</small></span></summary>
              <form action={importWeeklyWorkbookAction} className="import-form">
                <input type="hidden" name="week_start" value={week} />
                <div className="field"><label>Arquivo XLSX *</label><input type="file" name="workbook" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" required /></div>
                <label className="check"><input type="checkbox" name="confirm" required /> Revisei todas as linhas</label>
                <SubmitButton>Validar e importar</SubmitButton>
              </form>
            </details>
          </section> : null}
        </>
      )}
    </>
  );
}
