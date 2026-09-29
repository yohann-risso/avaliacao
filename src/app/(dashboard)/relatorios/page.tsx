import Link from "next/link";
import { Banknote, Check, ChevronDown, CircleAlert, Download, FileCheck2, FileText, Search, Star, TriangleAlert, Users } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { requireAdmin } from "@/lib/auth";
import { currentMonth, dateBr, monthBr } from "@/lib/dates";
import { brl, pct } from "@/lib/money";
import { filterReportRows, firstSearchParam, normalizeSectorSelection, reportExportQuery, summarizeReportRows } from "@/lib/report-selection";
import { buildMonthlyReport } from "@/lib/report";

type ReportSearchParams = {
  month?: string | string[];
  q?: string | string[];
  sector?: string | string[];
  inactive?: string | string[];
};

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<ReportSearchParams>;
}) {
  const [user, params] = await Promise.all([requireAdmin(), searchParams]);
  const requestedMonth = firstSearchParam(params.month);
  const month = /^\d{4}-\d{2}$/.test(requestedMonth) ? requestedMonth : currentMonth();
  const includeInactive = firstSearchParam(params.inactive) === "1";
  const report = await buildMonthlyReport(month, { includeInactive });
  const sectors = [...new Set(report.rows.map((row) => row.sector))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const selectedSectors = normalizeSectorSelection(params.sector).filter((sector) => sectors.includes(sector));
  const query = firstSearchParam(params.q).trim();
  const rows = filterReportRows(report.rows, selectedSectors, query);
  const summary = summarizeReportRows(rows);
  const hasFilters = Boolean(selectedSectors.length || query || includeInactive);
  const exportQuery = reportExportQuery(month, selectedSectors, query, includeInactive);
  const sectorSelectionLabel = selectedSectors.length === 0
    ? "Todos os setores"
    : selectedSectors.length === 1 ? selectedSectors[0] : `${selectedSectors.length} setores selecionados`;
  const ready = rows.length > 0 && summary.pending === 0 && (summary.weeklyExpected === 0 || summary.coverage >= 100);
  const pendingDescription = summary.pending === 1
    ? "1 pessoa da seleção tem semanas pendentes. Complete a avaliação antes da conferência final."
    : `${summary.pending} pessoas da seleção têm semanas pendentes. Complete as avaliações antes da conferência final.`;
  const pendingTitle = summary.pending === 1 ? "1 pessoa precisa de avaliação" : `${summary.pending} pessoas precisam de avaliação`;
  const recurrenceLabel = summary.recurrenceBlocks === 1 ? "1 bloqueio A01" : `${summary.recurrenceBlocks} bloqueios A01`;
  const closingTitle = !rows.length
    ? "Nenhuma pessoa nos filtros selecionados"
    : ready ? "Competência pronta para exportação" : "Competência ainda requer atenção";
  const closingDescription = !rows.length
    ? "Altere os setores ou a busca para gerar o fechamento."
    : ready
      ? "As semanas elegíveis da seleção estão cobertas. Faça a conferência final e gere os arquivos."
      : pendingDescription;

  return (
    <>
      <PageHeader step="Conferência mensal" title="Fechamento" subtitle="Valide cobertura, descontos e adicionais antes de exportar a folha de bonificação." icon={FileCheck2} user={`Admin · ${user.username}`} />

      <form method="get" className="filter-bar wrap">
        <div className="field compact"><label>Competência</label><input type="month" name="month" defaultValue={month} /></div>
        <div className="field compact grow with-icon"><label>Buscar</label><Search size={16} /><input name="q" defaultValue={query} placeholder="Nome, função ou setor" /></div>
        <div className="field compact sector-filter"><label>Setores</label><details className="multi-select-control"><summary>{sectorSelectionLabel}<ChevronDown size={15} /></summary><div className="multi-select-menu">{sectors.map((item) => <label className="check" key={item}><input type="checkbox" name="sector" value={item} defaultChecked={selectedSectors.includes(item)} /><span>{item}</span></label>)}<small>Sem seleção, todos os setores serão incluídos.</small></div></details></div>
        <div className="field compact"><label>Funcionários</label><select name="inactive" defaultValue={includeInactive ? "1" : "0"}><option value="0">Somente ativos</option><option value="1">Ativos e inativos</option></select></div>
        <button className="button secondary" type="submit">Aplicar filtros</button>
      </form>

      <section className={`closing-banner ${ready ? "ready" : "pending"}`}>
        <span className="closing-banner-icon">{ready ? <Check size={25} /> : <CircleAlert size={25} />}</span>
        <div><p className="eyebrow">Status de {monthBr(month)} · {sectorSelectionLabel} · {includeInactive ? "ativos e inativos" : "somente ativos"}</p><h2>{closingTitle}</h2><p>{closingDescription}</p></div>
        <div className="actions"><a className="button secondary" href={`/api/export/relatorio.csv?${exportQuery}`}><Download size={16} /> CSV</a><a className="button primary" href={`/api/export/relatorio-pdf?${exportQuery}`}><FileText size={16} /> PDF executivo</a></div>
      </section>

      <div className="closing-steps section">
        <article className={summary.weeklyExpected === 0 || summary.coverage >= 100 ? "done" : "active"}><span>{summary.weeklyExpected === 0 || summary.coverage >= 100 ? <Check size={16} /> : "1"}</span><div><strong>Cobertura</strong><small>{summary.weeklyDone}/{summary.weeklyExpected} avaliações</small></div></article>
        <article className={summary.recurrenceBlocks ? "active" : "done"}><span>{summary.recurrenceBlocks ? "2" : <Check size={16} />}</span><div><strong>Ocorrências</strong><small>{summary.recurrenceBlocks ? recurrenceLabel : "Regras consolidadas"}</small></div></article>
        <article className="done"><span><Check size={16} /></span><div><strong>Adicionais</strong><small>Monitoria, tempo e ajustes manuais</small></div></article>
        <article className={ready ? "active" : "locked"}><span>4</span><div><strong>Exportação</strong><small>{ready ? "Pronta para gerar" : "Aguardando cobertura"}</small></div></article>
      </div>

      <div className="metric-grid section">
        <article className="metric-card"><span className={`metric-icon ${summary.weeklyExpected === 0 || summary.coverage >= 100 ? "green" : "amber"}`}><Users size={19} /></span><div><small>Cobertura semanal</small><strong>{pct(summary.coverage)}</strong><p>Seleção atual</p></div></article>
        <article className="metric-card"><span className="metric-icon amber"><TriangleAlert size={19} /></span><div><small>Descontos por regras</small><strong>{brl(summary.ruleDiscount)}</strong><p>Valor efetivamente aplicado</p></div></article>
        <article className="metric-card"><span className={`metric-icon ${summary.adjustmentTotal < 0 ? "amber" : "green"}`}><Star size={19} /></span><div><small>Ajustes manuais</small><strong className={summary.adjustmentTotal < 0 ? "danger-text" : "success-text"}>{summary.adjustmentTotal > 0 ? "+" : summary.adjustmentTotal < 0 ? "−" : ""}{brl(Math.abs(summary.adjustmentTotal))}</strong><p>Monitoria fixa à parte: {brl(summary.monitorTotal)}</p></div></article>
        <article className="metric-card"><span className="metric-icon blue"><Banknote size={19} /></span><div><small>Total {hasFilters ? "filtrado" : "da competência"}</small><strong>{brl(summary.total)}</strong><p>{rows.length} pessoas na visão</p></div></article>
      </div>

      {summary.pending ? <section className="section panel attention-panel"><div><span className="metric-icon amber"><CircleAlert size={19} /></span><div><p className="eyebrow">Pendências antes de exportar</p><h2>{pendingTitle}</h2></div></div><div className="pending-chips">{rows.filter((row) => row.status === "Pendente").slice(0, 10).map((row) => <Link href={`/avaliacoes?employee=${row.employeeId}`} key={row.employeeId}>{row.name}<span>{row.missingWeeks} {row.missingWeeks === 1 ? "semana" : "semanas"}</span></Link>)}</div></section> : null}

      <section className="section panel flush-panel">
        <div className="panel-head padded"><div><p className="eyebrow">Memória de cálculo</p><h2>Consolidado de {monthBr(month)}</h2><p>Semanas: {report.weeks.map((week, index) => `S${index + 1} ${dateBr(week)}`).join(" · ")}</p></div><span className="badge">{rows.length} pessoas</span></div>
        <div className="table-wrap borderless"><table className="dense-table"><thead><tr><th>Colaborador</th><th>Grupo</th><th>Cobertura</th><th>Média / ocorrências</th><th>Aplicação das regras</th><th>Base</th><th>Monitoria</th><th>Tempo de casa</th><th>Ajustes</th><th>Total</th><th>Status</th></tr></thead><tbody>{rows.map((row) => <tr key={row.employeeId}><td><Link className="text-link" href={`/funcionarios/${row.employeeId}`}>{row.name}</Link><br /><small className="muted">{row.sector} · {row.role}</small></td><td><span className={`status-chip ${row.group === "Coord./Sup." ? "warning" : "neutral"}`}>{row.group}</span></td><td>{row.group === "Coord./Sup." ? "Base mensal" : `${row.evaluatedWeeks}/${row.eligibleWeeks} semanas`}</td><td>{row.average === null ? "—" : pct(row.average)}<br /><small className="muted">{row.errors} {row.errors === 1 ? "ocorrência" : "ocorrências"}</small></td><td><strong>{row.rulePoints.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} pts</strong><br /><small className={row.ruleDiscount ? "danger-text" : "muted"}>{row.ruleDiscount ? `-${brl(row.ruleDiscount)}` : brl(0)} · {row.ruleImpact}</small></td><td>{brl(row.basePayment)}</td><td>{brl(row.monitorPayment)}</td><td>{brl(row.tenurePayment)}</td><td><strong className={row.adjustmentTotal > 0 ? "success-text" : row.adjustmentTotal < 0 ? "danger-text" : "muted"}>{row.adjustmentTotal > 0 ? "+" : row.adjustmentTotal < 0 ? "−" : ""}{brl(Math.abs(row.adjustmentTotal))}</strong></td><td><strong>{brl(row.total)}</strong></td><td><span className={`status-chip ${row.status === "OK" ? "success" : "danger"}`}>{row.status}</span></td></tr>)}</tbody></table>{!rows.length ? <div className="empty-state"><FileCheck2 size={28} /><strong>Nenhum registro encontrado</strong><span>Ajuste os filtros de conferência.</span></div> : null}</div>
      </section>
    </>
  );
}
