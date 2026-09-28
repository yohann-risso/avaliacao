import Link from "next/link";
import type { CSSProperties } from "react";
import { ArrowRight, Banknote, CalendarDays, CheckCircle2, CircleAlert, ClipboardCheck, TriangleAlert, Users } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { requireUser } from "@/lib/auth";
import { currentMonth, dateBr, monthBr, normalizeMonday, todayBrazil, weeksForCompetencia } from "@/lib/dates";
import { listActiveEmployees, listOccurrenceRowsForWeeks, listWeeklyEvaluations } from "@/lib/data";
import { brl, pct } from "@/lib/money";
import { buildMonthlyReport } from "@/lib/report";
import { getEvaluationRule } from "@/lib/rules";

export default async function OverviewPage({ searchParams }: { searchParams: Promise<{ month?: string }> }) {
  const [user, params] = await Promise.all([requireUser(), searchParams]);
  const month = /^\d{4}-\d{2}$/.test(params.month || "") ? String(params.month) : currentMonth();
  const weeks = weeksForCompetencia(month);
  const monday = normalizeMonday(todayBrazil());
  const focusWeek = weeks.includes(monday) ? monday : weeks.at(-1) || monday;
  const [employees, evaluations, occurrences, report] = await Promise.all([
    listActiveEmployees(),
    listWeeklyEvaluations(weeks),
    listOccurrenceRowsForWeeks(weeks),
    user.role === "admin" ? buildMonthlyReport(month) : Promise.resolve(null),
  ]);
  const operators = employees.filter((employee) => !employee.is_leadership);
  const focusEvaluatedIds = new Set(evaluations.filter((item) => String(item.week_start).trim() === focusWeek).map((item) => item.employee_id));
  const pending = operators.filter((employee) => !focusEvaluatedIds.has(employee.id));
  const critical = occurrences.filter((item) => item.severity === "CRITICO" || item.error_type === "A01");
  const totalPoints = occurrences.reduce((sum, item) => sum + (getEvaluationRule(item.error_type)?.points || 0) * Number(item.qty || 0), 0);
  const coverage = report?.coverage ?? (operators.length * weeks.length ? (evaluations.length / (operators.length * weeks.length)) * 100 : 0);
  const weekCounts = weeks.map((week) => evaluations.filter((item) => String(item.week_start).trim() === week).length);

  return (
    <>
      <PageHeader step="Central operacional" title="Visão geral" subtitle="O que precisa de atenção agora para a competência fechar sem surpresas." icon={CalendarDays} user={`${user.username} · ${user.role}`} />

      <form method="get" className="filter-bar">
        <div className="field compact"><label>Competência</label><input type="month" name="month" defaultValue={month} /></div>
        <button className="button secondary" type="submit">Atualizar visão</button>
        <span className="filter-context">4 semanas operacionais · {monthBr(month)}</span>
      </form>

      <section className="overview-hero">
        <div>
          <p className="eyebrow">Ritmo da competência</p>
          <h2>{coverage >= 100 ? "Competência pronta para conferência" : `${Math.round(coverage)}% das avaliações concluídas`}</h2>
          <p>{pending.length ? `${pending.length} colaborador(es) ainda aguardam avaliação na semana de ${dateBr(focusWeek)}.` : `A semana de ${dateBr(focusWeek)} está coberta.`}</p>
          <div className="hero-actions">
            <Link className="button primary" href={`/avaliacoes?week=${focusWeek}`}><ClipboardCheck size={17} /> Continuar avaliações</Link>
            {user.role === "admin" ? <Link className="button ghost" href={`/relatorios?month=${month}`}>Revisar fechamento <ArrowRight size={16} /></Link> : null}
          </div>
        </div>
        <div className="coverage-gauge" style={{ "--coverage": `${Math.min(100, Math.max(0, coverage)) * 3.6}deg` } as CSSProperties}>
          <span><strong>{Math.round(coverage)}%</strong><small>cobertura</small></span>
        </div>
      </section>

      <div className="metric-grid section">
        <article className="metric-card"><span className="metric-icon blue"><Users size={19} /></span><div><small>Equipe operacional</small><strong>{operators.length}</strong><p>{employees.filter((item) => item.is_leadership).length} na liderança</p></div></article>
        <article className="metric-card"><span className={`metric-icon ${pending.length ? "amber" : "green"}`}>{pending.length ? <CircleAlert size={19} /> : <CheckCircle2 size={19} />}</span><div><small>Pendentes na semana</small><strong>{pending.length}</strong><p>{focusEvaluatedIds.size} avaliações concluídas</p></div></article>
        <article className="metric-card"><span className={`metric-icon ${critical.length ? "red" : "green"}`}><TriangleAlert size={19} /></span><div><small>Ocorrências críticas</small><strong>{critical.length}</strong><p>{totalPoints.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} pontos no mês</p></div></article>
        <article className="metric-card"><span className="metric-icon green"><Banknote size={19} /></span><div><small>{report ? "Prévia financeira" : "Avaliações do mês"}</small><strong>{report ? brl(report.total) : evaluations.length}</strong><p>{report ? "Inclui monitoria fixa" : `${weeks.length} semanas consideradas`}</p></div></article>
      </div>

      <div className="dashboard-grid section">
        <section className="panel span-2">
          <div className="panel-head"><div><p className="eyebrow">Progresso</p><h2>Cadência das 4 semanas</h2></div><span className="badge">{evaluations.length} avaliações</span></div>
          <div className="week-progress-list">
            {weeks.map((week, index) => {
              const value = operators.length ? Math.round((weekCounts[index] / operators.length) * 100) : 0;
              return <div className="week-progress" key={week}><span className="week-index">S{index + 1}</span><div><strong>{dateBr(week)}</strong><span className="progress-track light"><span style={{ width: `${Math.min(100, value)}%` }} /></span></div><b>{weekCounts[index]}/{operators.length}</b><em className={`status-chip ${value >= 100 ? "success" : value ? "warning" : "neutral"}`}>{value >= 100 ? "Concluída" : value ? "Em curso" : "A iniciar"}</em></div>;
            })}
          </div>
        </section>

        <section className="panel">
          <div className="panel-head"><div><p className="eyebrow">Fila atual</p><h2>Próximas avaliações</h2></div><Link className="text-link" href={`/avaliacoes?week=${focusWeek}`}>Ver fila</Link></div>
          <div className="compact-list">
            {pending.slice(0, 5).map((employee) => <Link href={`/avaliacoes?week=${focusWeek}&employee=${employee.id}`} key={employee.id}><span className="user-avatar pale">{employee.name.slice(0, 2).toUpperCase()}</span><div><strong>{employee.name}</strong><small>{employee.sector} · {employee.role}</small></div><ArrowRight size={15} /></Link>)}
            {!pending.length ? <div className="empty-state compact"><CheckCircle2 size={26} /><strong>Semana coberta</strong><span>Nenhuma avaliação pendente.</span></div> : null}
          </div>
        </section>

        <section className="panel span-2">
          <div className="panel-head"><div><p className="eyebrow">Atenção</p><h2>Ocorrências recentes</h2></div><Link className="text-link" href={`/ocorrencias?month=${month}`}>Abrir central</Link></div>
          <div className="table-list">
            {occurrences.slice(0, 6).map((item) => {
              const rule = getEvaluationRule(item.error_type);
              return <Link href={`/avaliacoes?week=${item.week_start}&employee=${item.employee_id}`} key={item.id}><span className={`rule-code ${item.severity === "CRITICO" ? "danger" : item.severity === "ALTO" ? "warning" : ""}`}>{item.error_type}</span><div><strong>{item.employee_name}</strong><small>{rule?.occurrence || "Ocorrência legada"} · {dateBr(item.week_start)}</small></div><b>{((rule?.points || 0) * item.qty).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} pts</b></Link>;
            })}
            {!occurrences.length ? <div className="empty-state compact"><CheckCircle2 size={26} /><strong>Sem ocorrências</strong><span>Nenhum registro nesta competência.</span></div> : null}
          </div>
        </section>

        <section className="panel closing-readiness">
          <div className="panel-head"><div><p className="eyebrow">Saúde do fechamento</p><h2>{report?.pending ? "Requer revisão" : "Dentro do esperado"}</h2></div></div>
          <div className="readiness-score"><strong>{pct(coverage)}</strong><span>cobertura consolidada</span></div>
          <ul className="check-list">
            <li className={coverage >= 100 ? "done" : ""}><CheckCircle2 size={16} /> Quatro semanas avaliadas</li>
            <li className={!critical.length ? "done" : ""}><CheckCircle2 size={16} /> Ocorrências críticas revisadas</li>
            <li className="done"><CheckCircle2 size={16} /> Monitoria fixa automática</li>
          </ul>
        </section>
      </div>
    </>
  );
}
