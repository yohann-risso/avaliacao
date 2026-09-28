import Link from "next/link";
import { AlertOctagon, Banknote, ClipboardCheck, Repeat2, Trash2, TriangleAlert } from "lucide-react";

import { deleteWeeklyOccurrenceAction } from "@/app/actions/evaluations";
import { Notice } from "@/components/notice";
import { PageHeader } from "@/components/page-header";
import { QuickOccurrenceForm } from "@/components/quick-occurrence-form";
import { requireUser } from "@/lib/auth";
import { currentMonth, dateBr, monthBr, weeksForCompetencia } from "@/lib/dates";
import { listActiveEmployees, listOccurrenceRowsForWeeks } from "@/lib/data";
import { employeesVisibleTo } from "@/lib/employee-access";
import { brl } from "@/lib/money";
import { userRoleLabel } from "@/lib/permissions";
import { getEvaluationRule, type RuleCategory } from "@/lib/rules";

export default async function OccurrencesPage({
  searchParams,
}: {
  searchParams: Promise<{ month?: string; week?: string; category?: string; severity?: string; q?: string; success?: string; error?: string }>;
}) {
  const [user, params] = await Promise.all([requireUser(), searchParams]);
  const month = /^\d{4}-\d{2}$/.test(params.month || "") ? String(params.month) : currentMonth();
  const weeks = weeksForCompetencia(month);
  const allEmployees = await listActiveEmployees();
  const employees = employeesVisibleTo(user, allEmployees);
  const operators = employees.filter((employee) => !employee.is_leadership);
  const occurrences = await listOccurrenceRowsForWeeks(weeks, operators.map((employee) => employee.id));
  const query = String(params.q || "").trim().toLocaleLowerCase("pt-BR");
  const week = weeks.includes(String(params.week)) ? String(params.week) : "";
  const category = String(params.category || "") as RuleCategory | "";
  const severity = String(params.severity || "");
  const rows = occurrences.filter((item) => {
    const rule = getEvaluationRule(item.error_type);
    return (!query || `${item.employee_name} ${item.employee_sector} ${item.error_type} ${item.notes}`.toLocaleLowerCase("pt-BR").includes(query))
      && (!week || item.week_start === week)
      && (!category || rule?.category === category)
      && (!severity || item.severity === severity);
  });
  const quantity = rows.reduce((sum, item) => sum + Number(item.qty || 0), 0);
  const referenceDiscount = rows.reduce((sum, item) => sum + (getEvaluationRule(item.error_type)?.points || 0) * Number(item.qty || 0), 0);
  const critical = rows.reduce((sum, item) => sum + (item.severity === "CRITICO" ? Number(item.qty || 0) : 0), 0);
  const a01ByEmployee = new Map<number, number>();
  for (const item of occurrences) if (item.error_type === "A01") a01ByEmployee.set(item.employee_id, (a01ByEmployee.get(item.employee_id) || 0) + Number(item.qty || 0));
  const recurrences = [...a01ByEmployee.values()].filter((value) => value >= 2).length;
  const returnTo = `/ocorrencias?month=${encodeURIComponent(month)}`;

  return (
    <>
      <PageHeader step="Controle de impacto" title="Central de ocorrências" subtitle="Registre, investigue e acompanhe todas as regras que afetam a bonificação." icon={TriangleAlert} user={`${user.username} · ${userRoleLabel(user.role)}`} />
      <Notice success={params.success} error={params.error} />

      <form method="get" className="filter-bar wrap">
        <div className="field compact"><label>Competência</label><input type="month" name="month" defaultValue={month} /></div>
        <div className="field compact"><label>Semana</label><select name="week" defaultValue={week}><option value="">Todas</option>{weeks.map((item, index) => <option key={item} value={item}>S{index + 1} · {dateBr(item)}</option>)}</select></div>
        <div className="field compact"><label>Categoria</label><select name="category" defaultValue={category}><option value="">Todas</option>{["ASSIDUIDADE", "QUALIDADE", "PRODUTIVIDADE", "COMPORTAMENTO"].map((item) => <option key={item}>{item}</option>)}</select></div>
        <div className="field compact"><label>Gravidade</label><select name="severity" defaultValue={severity}><option value="">Todas</option><option value="CRITICO">Crítico</option><option value="ALTO">Alto</option><option value="MEDIO">Médio</option><option value="BAIXO">Baixo</option></select></div>
        <div className="field compact grow"><label>Buscar</label><input name="q" defaultValue={params.q} placeholder="Pessoa, setor, código ou observação" /></div>
        <button className="button secondary" type="submit">Filtrar</button>
      </form>

      <div className="metric-grid section">
        <article className="metric-card"><span className="metric-icon blue"><TriangleAlert size={19} /></span><div><small>Ocorrências filtradas</small><strong>{quantity}</strong><p>{rows.length} lançamentos em {monthBr(month)}</p></div></article>
        <article className="metric-card"><span className="metric-icon amber"><Banknote size={19} /></span><div><small>Referência de desconto</small><strong>{brl(referenceDiscount)}</strong><p>Limitada ao bônus disponível</p></div></article>
        <article className="metric-card"><span className={`metric-icon ${critical ? "red" : "green"}`}><AlertOctagon size={19} /></span><div><small>Nível crítico</small><strong>{critical}</strong><p>{critical ? "Requer tratativa" : "Sem registros críticos"}</p></div></article>
        <article className="metric-card"><span className={`metric-icon ${recurrences ? "red" : "green"}`}><Repeat2 size={19} /></span><div><small>Reincidências A01</small><strong>{recurrences}</strong><p>{recurrences ? "Bônus-base mensal bloqueado" : "Nenhum bloqueio mensal"}</p></div></article>
      </div>

      {operators.length ? <section className="section"><QuickOccurrenceForm employees={operators.map(({ id, name, sector }) => ({ id, name, sector }))} weeks={weeks} returnTo={returnTo} /></section> : null}

      <section className="section panel flush-panel">
        <div className="panel-head padded"><div><p className="eyebrow">Histórico da competência</p><h2>{rows.length} lançamento(s) encontrado(s)</h2><p>Os pontos abaixo representam o teto de desconto definido no documento corporativo.</p></div><Link className="button ghost" href="/regras">Ver regras</Link></div>
        <div className="table-wrap borderless">
          <table className="dense-table">
            <thead><tr><th>Regra</th><th>Colaborador</th><th>Semana</th><th>Qtd.</th><th>Referência</th><th>Impacto</th><th>Contexto</th><th /></tr></thead>
            <tbody>{rows.map((item) => {
              const rule = getEvaluationRule(item.error_type);
              const recurrence = item.error_type === "A01" && (a01ByEmployee.get(item.employee_id) || 0) >= 2;
              return <tr key={item.id}>
                <td><span className={`rule-code ${item.severity === "CRITICO" ? "danger" : item.severity === "ALTO" ? "warning" : ""}`}>{item.error_type}</span><br /><small className="muted">{rule?.category || item.severity}</small></td>
                <td><strong>{item.employee_name}</strong><br /><small className="muted">{item.employee_sector} · {item.employee_role}</small></td>
                <td>{dateBr(item.week_start)}</td><td>{item.qty}</td>
                <td><strong>{brl((rule?.points || 0) * item.qty)}</strong><br /><small className="muted">{rule?.points.toLocaleString("pt-BR")} por ocorrência</small></td>
                <td><span className={`status-chip ${recurrence || item.severity === "CRITICO" ? "danger" : item.severity === "ALTO" ? "warning" : "neutral"}`}>{recurrence ? "Reincidência" : item.severity}</span><br /><small className="muted">{rule?.directive || "Regra legada"}</small></td>
                <td>{item.notes || <span className="muted">Sem observação</span>}</td>
                <td><div className="row-actions"><Link className="icon-button" href={`/avaliacoes?week=${item.week_start}&employee=${item.employee_id}`} aria-label="Abrir avaliação"><ClipboardCheck size={15} /></Link><form action={deleteWeeklyOccurrenceAction}><input type="hidden" name="id" value={item.id} /><input type="hidden" name="employee_id" value={item.employee_id} /><input type="hidden" name="week_start" value={item.week_start} /><input type="hidden" name="return_to" value={returnTo} /><button className="icon-button danger" type="submit" aria-label="Remover ocorrência"><Trash2 size={15} /></button></form></div></td>
              </tr>;
            })}</tbody>
          </table>
          {!rows.length ? <div className="empty-state"><TriangleAlert size={28} /><strong>Nenhuma ocorrência encontrada</strong><span>Ajuste os filtros ou registre o primeiro lançamento.</span></div> : null}
        </div>
      </section>
    </>
  );
}
