import { Star } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { requireUser } from "@/lib/auth";
import { MONITOR_FIXED_VALUE } from "@/lib/constants";
import { currentMonth, dateBr, isWeekAfterStart, monthBr, weeksForCompetencia } from "@/lib/dates";
import { listActiveEmployees } from "@/lib/data";
import { brl } from "@/lib/money";

export default async function MonitoringPage({
  searchParams,
}: {
  searchParams: Promise<{ month?: string }>;
}) {
  const [user, params, activeEmployees] = await Promise.all([requireUser(), searchParams, listActiveEmployees()]);
  const month = /^\d{4}-\d{2}$/.test(params.month || "") ? String(params.month) : currentMonth();
  const weeks = weeksForCompetencia(month);
  const monitors = activeEmployees.filter(
    (employee) => employee.is_monitor && !employee.is_leadership && weeks.some((week) => isWeekAfterStart(employee.monitor_start_date, week)),
  );

  return (
    <>
      <PageHeader
        step="Etapa 4"
        title="Adicional fixo de monitoria"
        subtitle="A monitoria não possui avaliação: todo monitor elegível recebe o valor fixo na competência."
        icon={Star}
        user={`${user.username} · ${user.role}`}
      />
      <form method="get" className="card toolbar">
        <div className="field"><label>Competência</label><input type="month" name="month" defaultValue={month} /></div>
        <button className="button secondary" type="submit">Carregar</button>
      </form>

      <div className="grid four section">
        <div className="card metric"><span>Competência</span><strong style={{ fontSize: "1.35rem" }}>{monthBr(month)}</strong><small className="muted">{weeks.length} semanas</small></div>
        <div className="card metric success"><span>Valor por monitor</span><strong>{brl(MONITOR_FIXED_VALUE)}</strong><small className="muted">Sem avaliação mensal</small></div>
        <div className="card metric"><span>Monitores elegíveis</span><strong>{monitors.length}</strong><small className="muted">Ativos na competência</small></div>
        <div className="card metric success"><span>Total de monitoria</span><strong>{brl(monitors.length * MONITOR_FIXED_VALUE)}</strong><small className="muted">Lançado no fechamento</small></div>
      </div>

      <section className="section">
        <div className="section-head">
          <div><p className="eyebrow">Elegibilidade</p><h2 className="section-title">Monitores de {monthBr(month)}</h2></div>
          <span className="badge success">Valor automático</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Monitor</th><th>Setor / função</th><th>Início da monitoria</th><th>Regra</th><th>Valor</th></tr></thead>
            <tbody>{monitors.map((employee) => (
              <tr key={employee.id}>
                <td><strong>{employee.name}</strong></td>
                <td>{employee.sector}<br /><span className="muted">{employee.role}</span></td>
                <td>{employee.monitor_start_date ? dateBr(employee.monitor_start_date) : "Desde o cadastro"}</td>
                <td><span className="badge success">Fixo · sem avaliação</span></td>
                <td><strong>{brl(MONITOR_FIXED_VALUE)}</strong></td>
              </tr>
            ))}</tbody>
          </table>
          {!monitors.length ? <div className="empty">Nenhum monitor ativo e elegível para esta competência.</div> : null}
        </div>
      </section>
    </>
  );
}
