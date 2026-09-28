import Link from "next/link";
import { ClipboardCheck, Download, Trash2 } from "lucide-react";

import { deleteWeeklyOccurrenceAction, importWeeklyWorkbookAction, saveWeeklyEvaluationAction } from "@/app/actions/evaluations";
import { Notice } from "@/components/notice";
import { OccurrenceForm } from "@/components/occurrence-form";
import { PageHeader } from "@/components/page-header";
import { SubmitButton } from "@/components/submit-button";
import { requireUser } from "@/lib/auth";
import { WEEKLY_CRITERIA } from "@/lib/constants";
import { dateBr, normalizeMonday, todayBrazil } from "@/lib/dates";
import { getWeeklyEvaluation, listActiveEmployees, listEvaluators, listWeeklyErrors, listWeeklyEvaluations } from "@/lib/data";
import { brl, pct, weeklyPaymentBreakdown } from "@/lib/money";
import { EVALUATION_RULES, getEvaluationRule, monthlyOccurrenceImpact, weeklyOccurrenceImpact } from "@/lib/rules";

export default async function EvaluationsPage({
  searchParams,
}: {
  searchParams: Promise<{ week?: string; employee?: string; success?: string; error?: string }>;
}) {
  const [user, params, allEmployees, evaluators] = await Promise.all([
    requireUser(), searchParams, listActiveEmployees(), listEvaluators(),
  ]);
  const employees = allEmployees.filter((employee) => !employee.is_leadership);
  const week = normalizeMonday(params.week || todayBrazil());
  const requestedEmployee = Number(params.employee);
  const selected = employees.find((employee) => employee.id === requestedEmployee) || employees[0];
  const employeeId = selected?.id || 0;
  const [evaluation, occurrences, weekEvaluations] = employeeId
    ? await Promise.all([
        getWeeklyEvaluation(employeeId, week),
        listWeeklyErrors(employeeId, week),
        listWeeklyEvaluations([week]),
      ])
    : [null, [], []];
  const evaluatorNames = user.role === "avaliador"
    ? (user.evaluator_name ? [user.evaluator_name] : [])
    : evaluators.map((employee) => employee.name);
  const selectedEvaluator = String(evaluation?.evaluator || user.evaluator_name || evaluatorNames[0] || "");
  const scoreRow: Record<string, unknown> = { week_start: week };
  for (const criterion of WEEKLY_CRITERIA) scoreRow[`${criterion.key}_pct`] = Number(evaluation?.[`${criterion.key}_pct`] ?? 100);
  const preview = weeklyPaymentBreakdown(scoreRow, occurrences);
  const weeklyImpact = weeklyOccurrenceImpact(occurrences);
  const monthlyImpact = monthlyOccurrenceImpact(occurrences);

  return (
    <>
      <PageHeader step="Etapa 3" title="Avaliação semanal" subtitle="Notas, ocorrências corporativas e desconto automático da bonificação." icon={ClipboardCheck} user={`${user.username} · ${user.role}`} />
      <Notice success={params.success} error={params.error} />

      <form method="get" className="card toolbar">
        <div className="field"><label>Semana operacional</label><input type="date" name="week" defaultValue={week} /></div>
        <div className="field" style={{ minWidth: 280 }}><label>Funcionário</label><select name="employee" defaultValue={employeeId}>{employees.map((employee) => <option value={employee.id} key={employee.id}>{employee.name} · {employee.sector}</option>)}</select></div>
        <button className="button secondary" type="submit">Carregar</button>
        <Link className="button secondary" href={`/api/export/avaliacoes?week=${week}`}><Download size={16} /> Planilha da semana</Link>
      </form>

      {!selected ? <div className="notice info">Cadastre ao menos um funcionário operacional ativo.</div> : (
        <>
          <div className="grid four section">
            <div className="card metric"><span>Colaborador</span><strong style={{ fontSize: "1.2rem" }}>{selected.name}</strong><small className="muted">{selected.role}</small></div>
            <div className="card metric"><span>Semana</span><strong style={{ fontSize: "1.35rem" }}>{dateBr(week)}</strong><small className="muted">Segunda a sexta</small></div>
            <div className={`card metric ${evaluation ? "success" : "warning"}`}><span>Status</span><strong style={{ fontSize: "1.35rem" }}>{evaluation ? "Avaliado" : "Pendente"}</strong><small className="muted">{evaluation ? `por ${evaluation.evaluator}` : "Sem registro"}</small></div>
            <div className={`card metric ${preview.discount > 0 ? "danger" : "success"}`}><span>Desconto por ocorrências</span><strong>{brl(preview.discount)}</strong><small className="muted">{weeklyImpact.points.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} pontos de referência</small></div>
          </div>

          {weeklyImpact.recognizedQuantity ? (
            <div className="card section">
              <div className="section-head"><div><p className="eyebrow">Cálculo automático</p><h2 className="section-title">Impacto das ocorrências</h2></div><span className="badge danger">Semana: {brl(preview.total)}</span></div>
              <div className="actions">
                {WEEKLY_CRITERIA.map((criterion) => {
                  const item = preview.byCriterion[criterion.key];
                  return item.gross > item.paid ? <span className="badge warning" key={criterion.key}>{criterion.label}: -{brl(item.gross - item.paid)}</span> : null;
                })}
              </div>
              {monthlyImpact.assiduidadeDiscount ? <p className="muted" style={{ marginBottom: 0 }}>Efeito mensal iniciado nesta semana: assiduidade -{monthlyImpact.assiduidadeDiscount}%. {monthlyImpact.blocksMonthlyBase ? "Reincidência A01: bônus-base mensal bloqueado." : "O fechamento consolida todas as semanas da competência."}</p> : null}
            </div>
          ) : null}

          <section className="section">
            <div className="section-head"><div><p className="eyebrow">Avaliação</p><h2 className="section-title">Resultado por quesito</h2><p className="muted">A nota define a faixa de pagamento; as ocorrências são descontadas depois, sem alterar a nota informada.</p></div></div>
            <form action={saveWeeklyEvaluationAction} className="card">
              <input type="hidden" name="employee_id" value={selected.id} />
              <input type="hidden" name="week_start" value={week} />
              <div className="criteria-grid">
                {WEEKLY_CRITERIA.map((criterion) => {
                  const value = Number(evaluation?.[`${criterion.key}_pct`] ?? 100);
                  const payment = preview.byCriterion[criterion.key];
                  return (
                    <div className="criterion" key={criterion.key}>
                      <div className="section-head"><strong>{criterion.label}</strong><span className={`badge ${payment.gross > payment.paid ? "danger" : "success"}`}>{brl(payment.paid)}</span></div>
                      <div className="field"><label>Resultado atingido (%)</label><input type="number" name={`${criterion.key}_pct`} min="0" max="100" step="0.1" defaultValue={value} required /></div>
                      <div className="field" style={{ marginTop: 10 }}><label>Justificativa da nota</label><textarea name={`${criterion.key}_just`} defaultValue={String(evaluation?.[`${criterion.key}_just`] || "")} placeholder="Obrigatória quando o resultado for menor que 100%" /></div>
                      {payment.gross > payment.paid ? <small className="muted">Faixa antes da ocorrência: {brl(payment.gross)} · desconto: {brl(payment.gross - payment.paid)}</small> : null}
                    </div>
                  );
                })}
              </div>
              <div className="form-grid" style={{ marginTop: 18 }}>
                <div className="field span-3"><label>Itens executados</label><input type="number" name="items_count" min="0" defaultValue={Number(evaluation?.items_count || 0)} required /></div>
                <div className="field span-3"><label>Avaliador *</label><select name="evaluator" defaultValue={selectedEvaluator} required>{evaluatorNames.map((name) => <option key={name} value={name}>{name}</option>)}</select></div>
                <div className="field span-6"><label>Observações gerais</label><textarea name="notes" defaultValue={String(evaluation?.notes || "")} /></div>
              </div>
              {!evaluatorNames.length ? <div className="notice error" style={{ marginTop: 16 }}>Nenhum avaliador disponível. Vincule o usuário a uma coordenação/supervisão ativa.</div> : null}
              <div className="actions" style={{ marginTop: 18 }}><SubmitButton>Salvar avaliação semanal</SubmitButton></div>
            </form>
          </section>

          <section className="section">
            <div className="section-head"><div><p className="eyebrow">Lote</p><h2 className="section-title">Importar avaliações do Excel</h2></div><Link className="button secondary" href={`/api/export/avaliacoes?week=${week}`}><Download size={16} /> Baixar modelo preenchível</Link></div>
            <form action={importWeeklyWorkbookAction} className="card">
              <input type="hidden" name="week_start" value={week} />
              <div className="form-grid">
                <div className="field span-8"><label>Arquivo XLSX *</label><input type="file" name="workbook" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" required /></div>
                <div className="field span-4"><label className="check"><input type="checkbox" name="confirm" required /> Revisei todas as linhas</label></div>
              </div>
              <p className="muted">A importação valida o lote inteiro antes de gravar e atualiza registros com a mesma combinação de funcionário e semana.</p>
              <div className="actions"><SubmitButton>Validar e importar lote</SubmitButton></div>
            </form>
          </section>

          <section className="section grid two">
            <div>
              <div className="section-head"><div><p className="eyebrow">Ocorrências</p><h2 className="section-title">Registrar pelo código da regra</h2></div></div>
              <OccurrenceForm employeeId={selected.id} weekStart={week} />
            </div>
            <div>
              <div className="section-head"><div><p className="eyebrow">Log</p><h2 className="section-title">Ocorrências da semana</h2></div><span className="badge">{occurrences.reduce((sum, item) => sum + Number(item.qty), 0)} ocorrência(s)</span></div>
              <div className="card">
                {occurrences.length ? occurrences.map((item) => {
                  const rule = getEvaluationRule(item.error_type);
                  return (
                    <div key={item.id} style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 12, padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
                      <div>
                        <strong>{rule ? `${rule.code} · ${rule.occurrence}` : item.error_type}</strong> <span className={`badge ${item.severity === "CRITICO" ? "danger" : item.severity === "ALTO" ? "warning" : ""}`}>{item.severity}</span><br />
                        <small className="muted">Qtd. {item.qty} · {rule ? `${rule.points.toLocaleString("pt-BR")} ponto(s) cada · ${rule.directive}` : "Registro legado, sem regra automática"}{item.notes ? ` · ${item.notes}` : ""}</small>
                      </div>
                      <form action={deleteWeeklyOccurrenceAction}><input type="hidden" name="id" value={item.id} /><input type="hidden" name="employee_id" value={selected.id} /><input type="hidden" name="week_start" value={week} /><button className="button danger" type="submit" aria-label="Remover ocorrência"><Trash2 size={15} /></button></form>
                    </div>
                  );
                }) : <div className="empty">Nenhuma ocorrência registrada nesta semana.</div>}
              </div>
            </div>
          </section>

          <section className="section">
            <details className="card">
              <summary><strong>Tabela de regras corporativas</strong> <span className="muted">· {EVALUATION_RULES.length} códigos</span></summary>
              <div className="table-wrap" style={{ marginTop: 16 }}><table><thead><tr><th>Código</th><th>Categoria</th><th>Ocorrência</th><th>Pontos</th><th>Diretriz</th></tr></thead><tbody>{EVALUATION_RULES.map((rule) => <tr key={rule.code}><td><strong>{rule.code}</strong></td><td>{rule.category}</td><td>{rule.occurrence}</td><td>{rule.points.toLocaleString("pt-BR")}</td><td>{rule.directive}</td></tr>)}</tbody></table></div>
            </details>
          </section>

          <section className="section">
            <div className="section-head"><div><p className="eyebrow">Cobertura</p><h2 className="section-title">Avaliações registradas na semana</h2></div><span className="badge">{weekEvaluations.length}/{employees.length}</span></div>
            <div className="table-wrap"><table><thead><tr><th>Funcionário</th><th>Setor / função</th><th>Avaliador</th><th>Média</th></tr></thead><tbody>{weekEvaluations.map((row) => {
              const average = WEEKLY_CRITERIA.reduce((sum, criterion) => sum + Number(row[`${criterion.key}_pct`] || 0), 0) / WEEKLY_CRITERIA.length;
              return <tr key={row.id}><td><strong>{String(row.employee_name)}</strong></td><td>{String(row.sector)}<br /><span className="muted">{String(row.role)}</span></td><td>{row.evaluator}</td><td><span className={`badge ${average > 90 ? "success" : average > 70 ? "warning" : "danger"}`}>{pct(average)}</span></td></tr>;
            })}</tbody></table></div>
          </section>
        </>
      )}
    </>
  );
}
