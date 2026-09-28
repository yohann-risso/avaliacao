import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Banknote, CalendarClock, ClipboardCheck, Pencil, Star, TriangleAlert, UserRound } from "lucide-react";

import { toggleEmployeeAction, updateEmployeeAction } from "@/app/actions/employees";
import { EmployeeFields } from "@/components/employee-fields";
import { PageHeader } from "@/components/page-header";
import { SubmitButton } from "@/components/submit-button";
import { requirePeopleManager } from "@/lib/auth";
import { WEEKLY_CRITERIA } from "@/lib/constants";
import { currentMonth, dateBr, monthBr } from "@/lib/dates";
import { getEmployee, listEmployees, listRecentBonusAdjustments, listRecentWeeklyErrors, listRecentWeeklyEvaluations } from "@/lib/data";
import { evaluatorsVisibleTo, requireManagedEmployeeAccess } from "@/lib/employee-access";
import { brl, pct, totalAfterFinancialAdjustments, weeklyPaymentBreakdown } from "@/lib/money";
import { userRoleLabel } from "@/lib/permissions";
import { buildMonthlyReport } from "@/lib/report";
import { getEvaluationRule } from "@/lib/rules";

export default async function EmployeeProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const employeeId = Number(id);
  if (!Number.isInteger(employeeId) || employeeId < 1) notFound();
  const month = currentMonth();
  const user = await requirePeopleManager();
  await requireManagedEmployeeAccess(user, employeeId);
  const [employee, allEmployees, evaluations, occurrences, adjustments, report] = await Promise.all([
    getEmployee(employeeId), listEmployees(true), listRecentWeeklyEvaluations(employeeId), listRecentWeeklyErrors(employeeId), listRecentBonusAdjustments(employeeId), buildMonthlyReport(month),
  ]);
  if (!employee) notFound();
  const evaluators = evaluatorsVisibleTo(user, allEmployees);
  const reportRow = report.rows.find((row) => row.employeeId === employee.id);
  const errorsByWeek = new Map<string, typeof occurrences>();
  for (const item of occurrences) {
    const current = errorsByWeek.get(item.week_start) || [];
    current.push(item);
    errorsByWeek.set(item.week_start, current);
  }
  const adjustmentsByWeek = new Map<string, typeof adjustments>();
  for (const item of adjustments) {
    const current = adjustmentsByWeek.get(item.week_start) || [];
    current.push(item);
    adjustmentsByWeek.set(item.week_start, current);
  }
  const averages = evaluations.map((evaluation) => WEEKLY_CRITERIA.reduce((sum, criterion) => sum + Number(evaluation[`${criterion.key}_pct`] || 0), 0) / WEEKLY_CRITERIA.length);
  const historicalAverage = averages.length ? averages.reduce((sum, item) => sum + item, 0) / averages.length : null;

  return (
    <>
      <Link className="back-link" href="/funcionarios"><ArrowLeft size={15} /> Voltar para pessoas</Link>
      <PageHeader step={`Perfil #${employee.id}`} title={employee.name} subtitle={`${employee.sector} · ${employee.role}`} icon={UserRound} user={`${userRoleLabel(user.role)} · ${user.username}`} />

      <section className="profile-hero">
        <span className="profile-avatar">{employee.name.slice(0, 2).toUpperCase()}</span>
        <div><div className="actions"><span className={`status-chip ${employee.active ? "success" : "danger"}`}>{employee.active ? "Ativo" : "Inativo"}</span>{employee.is_monitor ? <span className="status-chip success">Monitor</span> : null}{employee.is_leadership ? <span className="status-chip warning">Coord./Sup.</span> : null}</div><h2>{employee.name}</h2><p>Admissão em {dateBr(employee.hire_date)} · {employee.sector}</p></div>
        <div className="profile-quick-action"><Link className="button primary" href={`/avaliacoes?employee=${employee.id}`}><ClipboardCheck size={16} /> Abrir avaliação</Link></div>
      </section>

      <div className="metric-grid section">
        <article className="metric-card"><span className="metric-icon blue"><ClipboardCheck size={19} /></span><div><small>Média histórica</small><strong>{historicalAverage === null ? "—" : pct(historicalAverage)}</strong><p>{evaluations.length} semanas registradas</p></div></article>
        <article className="metric-card"><span className={`metric-icon ${occurrences.length ? "amber" : "green"}`}><TriangleAlert size={19} /></span><div><small>Ocorrências recentes</small><strong>{occurrences.reduce((sum, item) => sum + item.qty, 0)}</strong><p>{occurrences.length} lançamentos</p></div></article>
        <article className="metric-card"><span className="metric-icon green"><Banknote size={19} /></span><div><small>Prévia de {monthBr(month)}</small><strong>{brl(reportRow?.total || 0)}</strong><p>{reportRow?.status || "Fora da competência"}</p></div></article>
        <article className="metric-card"><span className="metric-icon green"><Star size={19} /></span><div><small>Monitoria fixa</small><strong>{brl(reportRow?.monitorPayment || 0)}</strong><p>{employee.is_monitor ? "Elegibilidade pelo início" : "Não elegível"}</p></div></article>
      </div>

      <div className="profile-grid section">
        <section className="panel span-2">
          <div className="panel-head"><div><p className="eyebrow">Histórico semanal</p><h2>Desempenho e pagamento</h2></div><span className="badge">Últimas {evaluations.length} avaliações</span></div>
          <div className="table-wrap borderless"><table className="dense-table"><thead><tr><th>Semana</th><th>Avaliador</th><th>Média</th><th>Ocorrências</th><th>Prévia</th></tr></thead><tbody>{evaluations.map((evaluation) => {
            const average = WEEKLY_CRITERIA.reduce((sum, criterion) => sum + Number(evaluation[`${criterion.key}_pct`] || 0), 0) / WEEKLY_CRITERIA.length;
            const errors = errorsByWeek.get(String(evaluation.week_start).trim()) || [];
            const weeklyAdjustments = adjustmentsByWeek.get(String(evaluation.week_start).trim()) || [];
            const payment = weeklyPaymentBreakdown(evaluation, errors);
            const adjustedTotal = totalAfterFinancialAdjustments(payment.total, weeklyAdjustments);
            const adjustment = weeklyAdjustments.reduce((sum, item) => sum + Number(item.amount), 0);
            return <tr key={evaluation.id}><td><Link className="text-link" href={`/avaliacoes?week=${evaluation.week_start}&employee=${employee.id}`}>{dateBr(String(evaluation.week_start))}</Link></td><td>{evaluation.evaluator}</td><td><span className={`status-chip ${average >= 90 ? "success" : average >= 70 ? "warning" : "danger"}`}>{pct(average)}</span></td><td>{errors.reduce((sum, item) => sum + item.qty, 0)}</td><td><strong>{brl(adjustedTotal)}</strong>{payment.discount ? <><br /><small className="danger-text">-{brl(payment.discount)} em regras</small></> : null}{adjustment ? <><br /><small className={adjustment > 0 ? "success-text" : "danger-text"}>{adjustment > 0 ? "+" : "−"}{brl(Math.abs(adjustment))} em ajustes</small></> : null}</td></tr>;
          })}</tbody></table>{!evaluations.length ? <div className="empty-state compact"><CalendarClock size={26} /><strong>Sem histórico</strong><span>A primeira avaliação aparecerá aqui.</span></div> : null}</div>
        </section>

        <section className="panel">
          <div className="panel-head"><div><p className="eyebrow">Ocorrências</p><h2>Registros recentes</h2></div></div>
          <div className="timeline-list">{occurrences.slice(0, 10).map((item) => {
            const rule = getEvaluationRule(item.error_type);
            return <article key={item.id}><span className={`timeline-dot ${item.severity === "CRITICO" ? "danger" : item.severity === "ALTO" ? "warning" : ""}`} /><div><strong>{item.error_type} · {rule?.occurrence || item.severity}</strong><small>{dateBr(item.week_start)} · {item.qty} × {rule?.points.toLocaleString("pt-BR") || 0} pts</small>{item.notes ? <p>{item.notes}</p> : null}</div></article>;
          })}{!occurrences.length ? <div className="empty-state compact"><TriangleAlert size={25} /><strong>Sem ocorrências</strong><span>Nenhum registro recente.</span></div> : null}</div>
        </section>
      </div>

      <section className="section">
        <details className="panel profile-edit-panel">
          <summary><span className="metric-icon blue"><Pencil size={18} /></span><span><strong>Editar dados e elegibilidade</strong><small>Altere função, datas, monitoria ou liderança.</small></span></summary>
          <form action={updateEmployeeAction} className="details-form"><EmployeeFields employee={employee} evaluators={evaluators} allowUnlinked={user.role === "admin"} /><div className="actions"><SubmitButton>Salvar alterações</SubmitButton></div></form>
          <form action={toggleEmployeeAction} className="danger-zone"><input type="hidden" name="id" value={employee.id} /><input type="hidden" name="active" value={employee.active ? 0 : 1} /><div><strong>{employee.active ? "Desativar colaborador" : "Reativar colaborador"}</strong><p>{employee.active ? "O histórico será preservado e o colaborador sairá das filas futuras." : "O colaborador voltará às filas de avaliação."}</p></div><SubmitButton className={employee.active ? "button danger" : "button secondary"}>{employee.active ? "Desativar" : "Reativar"}</SubmitButton></form>
        </details>
      </section>
    </>
  );
}
