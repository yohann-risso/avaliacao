import Link from "next/link";
import { Download, FileBarChart, FileText } from "lucide-react";

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

  return (
    <>
      <PageHeader step="Etapa 5" title="Relatório mensal" subtitle="Fechamento financeiro, cobertura e exportações para conferência." icon={FileBarChart} user={`Admin: ${user.username}`} />
      <form method="get" className="card toolbar">
        <div className="field"><label>Competência</label><input type="month" name="month" defaultValue={month} /></div>
        <div className="field"><label>Buscar</label><input name="q" defaultValue={params.q} placeholder="Nome, função ou setor" /></div>
        <div className="field"><label>Setor</label><select name="sector" defaultValue={sector}><option value="">Todos</option>{sectors.map((item) => <option key={item}>{item}</option>)}</select></div>
        <button className="button secondary" type="submit">Aplicar filtros</button>
      </form>

      <div className="grid four section">
        <div className={`card metric ${report.coverage === 100 ? "success" : "warning"}`}><span>Cobertura semanal</span><strong>{pct(report.coverage)}</strong><small className="muted">{report.weeklyDone}/{report.weeklyExpected} avaliações</small></div>
        <div className={`card metric ${report.pending ? "danger" : "success"}`}><span>Pessoas com pendência</span><strong>{report.pending}</strong><small className="muted">Checklist da competência</small></div>
        <div className="card metric"><span>Total do filtro</span><strong>{brl(filteredTotal)}</strong><small className="muted">{rows.length} pessoas</small></div>
        <div className="card metric success"><span>Total geral</span><strong>{brl(report.total)}</strong><small className="muted">Inclui monitoria fixa elegível</small></div>
      </div>

      <section className="section">
        <div className="section-head">
          <div><p className="eyebrow">Fechamento</p><h2 className="section-title">Consolidado de {monthBr(month)}</h2><p className="muted">Semanas: {report.weeks.map(dateBr).join(" · ")}</p></div>
          <div className="actions">
            <Link className="button secondary" href={`/api/export/relatorio.csv?month=${month}`}><Download size={16} /> CSV</Link>
            <Link className="button primary" href={`/api/export/relatorio-pdf?month=${month}`}><FileText size={16} /> PDF executivo</Link>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Funcionário</th><th>Grupo</th><th>Cobertura</th><th>Média / ocorrências</th><th>Regras</th><th>Base</th><th>Monitoria fixa</th><th>Tempo</th><th>Total</th><th>Status</th></tr></thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.employeeId}>
                  <td><strong>{row.name}</strong><br /><span className="muted">{row.sector} · {row.role}</span></td>
                  <td><span className={`badge ${row.group === "Coord./Sup." ? "warning" : ""}`}>{row.group}</span></td>
                  <td>{row.group === "Coord./Sup." ? "Base mensal" : `${row.evaluatedWeeks}/${row.eligibleWeeks} semanas`}</td>
                  <td>{row.average === null ? "—" : pct(row.average)}<br /><small className="muted">{row.errors} ocorrência(s)</small></td>
                  <td>{row.rulePoints.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} pts<br /><small className="muted">-{brl(row.ruleDiscount)} · {row.ruleImpact}</small></td>
                  <td>{brl(row.basePayment)}</td><td>{brl(row.monitorPayment)}</td><td>{brl(row.tenurePayment)}</td>
                  <td><strong>{brl(row.total)}</strong></td>
                  <td><span className={`badge ${row.status === "OK" ? "success" : "danger"}`}>{row.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length ? <div className="empty">Nenhum registro encontrado com os filtros atuais.</div> : null}
        </div>
      </section>
    </>
  );
}
