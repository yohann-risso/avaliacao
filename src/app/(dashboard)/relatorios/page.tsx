import Link from "next/link";
import { Banknote, Check, CircleAlert, Download, FileCheck2, FileText, Search, Star, TriangleAlert, Users } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { requireAdmin } from "@/lib/auth";
import { currentMonth, dateBr, monthBr } from "@/lib/dates";
import { brl, pct } from "@/lib/money";
import { buildMonthlyReport } from "@/lib/report";

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<{ month?: string; q?: string; sector?: string }>;
}) {
  const [user, params] = await Promise.all([requireAdmin(), searchParams]);
  const month = /^\d{4}-\d{2}$/.test(params.month || "") ? String(params.month) : currentMonth();
  const report = await buildMonthlyReport(month);
  const sectors = [...new Set(report.rows.map((row) => row.sector))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const query = String(params.q || "").trim().toLocaleLowerCase("pt-BR");
  const sector = String(params.sector || "");
  const rows = report.rows.filter((row) => (!query || `${row.name} ${row.role} ${row.sector}`.toLocaleLowerCase("pt-BR").includes(query)) && (!sector || row.sector === sector));
  const filteredTotal = rows.reduce((sum, row) => sum + row.total, 0);
  const monitorTotal = report.rows.reduce((sum, row) => sum + row.monitorPayment, 0);
  const ruleDiscount = report.rows.reduce((sum, row) => sum + row.ruleDiscount, 0);
  const recurrenceBlocks = report.rows.filter((row) => row.ruleImpact.includes("bloqueado")).length;
  const ready = report.pending === 0 && report.coverage >= 100;

  return (
    <>
      <PageHeader step="Conferência mensal" title="Fechamento" subtitle="Valide cobertura, descontos e adicionais antes de exportar a folha de bonificação." icon={FileCheck2} user={`Admin · ${user.username}`} />

      <form method="get" className="filter-bar">
        <div className="field compact"><label>Competência</label><input type="month" name="month" defaultValue={month} /></div>
        <div className="field compact grow with-icon"><label>Buscar</label><Search size={16} /><input name="q" defaultValue={params.q} placeholder="Nome, função ou setor" /></div>
        <div className="field compact"><label>Setor</label><select name="sector" defaultValue={sector}><option value="">Todos</option>{sectors.map((item) => <option key={item}>{item}</option>)}</select></div>
        <button className="button secondary" type="submit">Aplicar filtros</button>
      </form>

      <section className={`closing-banner ${ready ? "ready" : "pending"}`}>
        <span className="closing-banner-icon">{ready ? <Check size={25} /> : <CircleAlert size={25} />}</span>
        <div><p className="eyebrow">Status de {monthBr(month)}</p><h2>{ready ? "Competência pronta para exportação" : "Competência ainda requer atenção"}</h2><p>{ready ? "As quatro semanas estão cobertas. Faça a conferência final e gere os arquivos." : `${report.pending} pessoa(s) têm semanas pendentes. Complete as avaliações antes da conferência final.`}</p></div>
        <div className="actions"><Link className="button secondary" href={`/api/export/relatorio.csv?month=${month}`}><Download size={16} /> CSV</Link><Link className="button primary" href={`/api/export/relatorio-pdf?month=${month}`}><FileText size={16} /> PDF executivo</Link></div>
      </section>

      <div className="closing-steps section">
        <article className={report.coverage >= 100 ? "done" : "active"}><span>{report.coverage >= 100 ? <Check size={16} /> : "1"}</span><div><strong>Cobertura</strong><small>{report.weeklyDone}/{report.weeklyExpected} avaliações</small></div></article>
        <article className={recurrenceBlocks ? "active" : "done"}><span>{recurrenceBlocks ? "2" : <Check size={16} />}</span><div><strong>Ocorrências</strong><small>{recurrenceBlocks ? `${recurrenceBlocks} bloqueio(s) A01` : "Regras consolidadas"}</small></div></article>
        <article className="done"><span><Check size={16} /></span><div><strong>Adicionais</strong><small>Monitoria fixa e tempo</small></div></article>
        <article className={ready ? "active" : "locked"}><span>4</span><div><strong>Exportação</strong><small>{ready ? "Pronta para gerar" : "Aguardando cobertura"}</small></div></article>
      </div>

      <div className="metric-grid section">
        <article className="metric-card"><span className={`metric-icon ${report.coverage >= 100 ? "green" : "amber"}`}><Users size={19} /></span><div><small>Cobertura semanal</small><strong>{pct(report.coverage)}</strong><p>4 semanas fixas</p></div></article>
        <article className="metric-card"><span className="metric-icon amber"><TriangleAlert size={19} /></span><div><small>Descontos por regras</small><strong>{brl(ruleDiscount)}</strong><p>Valor efetivamente aplicado</p></div></article>
        <article className="metric-card"><span className="metric-icon green"><Star size={19} /></span><div><small>Monitoria fixa</small><strong>{brl(monitorTotal)}</strong><p>Sem avaliação mensal</p></div></article>
        <article className="metric-card"><span className="metric-icon blue"><Banknote size={19} /></span><div><small>Total {sector || query ? "filtrado" : "da competência"}</small><strong>{brl(sector || query ? filteredTotal : report.total)}</strong><p>{rows.length} pessoas na visão</p></div></article>
      </div>

      {report.pending ? <section className="section panel attention-panel"><div><span className="metric-icon amber"><CircleAlert size={19} /></span><div><p className="eyebrow">Pendências antes de exportar</p><h2>{report.pending} pessoa(s) precisam de avaliação</h2></div></div><div className="pending-chips">{report.rows.filter((row) => row.status === "Pendente").slice(0, 10).map((row) => <Link href={`/avaliacoes?employee=${row.employeeId}`} key={row.employeeId}>{row.name}<span>{row.missingWeeks} semana(s)</span></Link>)}</div></section> : null}

      <section className="section panel flush-panel">
        <div className="panel-head padded"><div><p className="eyebrow">Memória de cálculo</p><h2>Consolidado de {monthBr(month)}</h2><p>Semanas: {report.weeks.map((week, index) => `S${index + 1} ${dateBr(week)}`).join(" · ")}</p></div><span className="badge">{rows.length} pessoas</span></div>
        <div className="table-wrap borderless"><table className="dense-table"><thead><tr><th>Colaborador</th><th>Grupo</th><th>Cobertura</th><th>Média / ocorrências</th><th>Aplicação das regras</th><th>Base</th><th>Monitoria</th><th>Tempo</th><th>Total</th><th>Status</th></tr></thead><tbody>{rows.map((row) => <tr key={row.employeeId}><td><Link className="text-link" href={`/funcionarios/${row.employeeId}`}>{row.name}</Link><br /><small className="muted">{row.sector} · {row.role}</small></td><td><span className={`status-chip ${row.group === "Coord./Sup." ? "warning" : "neutral"}`}>{row.group}</span></td><td>{row.group === "Coord./Sup." ? "Base mensal" : `${row.evaluatedWeeks}/${row.eligibleWeeks} semanas`}</td><td>{row.average === null ? "—" : pct(row.average)}<br /><small className="muted">{row.errors} ocorrência(s)</small></td><td><strong>{row.rulePoints.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} pts</strong><br /><small className={row.ruleDiscount ? "danger-text" : "muted"}>-{brl(row.ruleDiscount)} · {row.ruleImpact}</small></td><td>{brl(row.basePayment)}</td><td>{brl(row.monitorPayment)}</td><td>{brl(row.tenurePayment)}</td><td><strong>{brl(row.total)}</strong></td><td><span className={`status-chip ${row.status === "OK" ? "success" : "danger"}`}>{row.status}</span></td></tr>)}</tbody></table>{!rows.length ? <div className="empty-state"><FileCheck2 size={28} /><strong>Nenhum registro encontrado</strong><span>Ajuste os filtros de conferência.</span></div> : null}</div>
      </section>
    </>
  );
}
