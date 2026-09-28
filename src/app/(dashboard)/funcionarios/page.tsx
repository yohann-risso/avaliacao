import Link from "next/link";
import { ArrowRight, BadgeCheck, Network, Plus, Search, Shield, Star, Unlink, UserRoundX, Users } from "lucide-react";

import { createEmployeeAction, deleteEmployeeEvaluatorLinkAction, saveEmployeeEvaluatorLinkAction } from "@/app/actions/employees";
import { EmployeeFields } from "@/components/employee-fields";
import { Notice } from "@/components/notice";
import { PageHeader } from "@/components/page-header";
import { SubmitButton } from "@/components/submit-button";
import { requireAdmin } from "@/lib/auth";
import { dateBr } from "@/lib/dates";
import { listEmployees, listEvaluators } from "@/lib/data";

export default async function EmployeesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; sector?: string; status?: string; success?: string; error?: string }>;
}) {
  const [user, employees, evaluators, params] = await Promise.all([requireAdmin(), listEmployees(true), listEvaluators(), searchParams]);
  const query = String(params.q || "").trim().toLocaleLowerCase("pt-BR");
  const sector = String(params.sector || "");
  const status = String(params.status || "active");
  const sectors = [...new Set(employees.map((item) => item.sector))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const rows = employees.filter((employee) => (!query || `${employee.name} ${employee.role} ${employee.sector}`.toLocaleLowerCase("pt-BR").includes(query)) && (!sector || employee.sector === sector) && (status === "all" || (status === "active" ? employee.active : !employee.active)));
  const active = employees.filter((item) => item.active);
  const unlinked = active.filter((item) => !item.evaluator_employee_id);
  const linked = active.filter((item) => item.evaluator_employee_id);

  return (
    <>
      <PageHeader step="Base organizacional" title="Pessoas" subtitle="Cadastros, elegibilidade, perfis e histórico de performance." icon={Users} user={`Admin · ${user.username}`} />
      <Notice success={params.success} error={params.error} />

      <div className="metric-grid section">
        <article className="metric-card"><span className="metric-icon blue"><BadgeCheck size={19} /></span><div><small>Ativos</small><strong>{active.length}</strong><p>{active.filter((item) => !item.is_leadership).length} na operação</p></div></article>
        <article className="metric-card"><span className="metric-icon green"><Star size={19} /></span><div><small>Monitores</small><strong>{active.filter((item) => item.is_monitor).length}</strong><p>Adicional fixo automático</p></div></article>
        <article className="metric-card"><span className="metric-icon amber"><Shield size={19} /></span><div><small>Coord. / supervisão</small><strong>{active.filter((item) => item.is_leadership).length}</strong><p>Elegíveis como avaliadores</p></div></article>
        <article className="metric-card"><span className="metric-icon red"><UserRoundX size={19} /></span><div><small>Inativos</small><strong>{employees.length - active.length}</strong><p>Histórico preservado</p></div></article>
      </div>

      <section className="section">
        <details className="panel add-person-panel">
          <summary><span className="metric-icon blue"><Plus size={18} /></span><span><strong>Novo colaborador</strong><small>Abra para cadastrar e definir a elegibilidade.</small></span></summary>
          <form action={createEmployeeAction} className="details-form"><EmployeeFields evaluators={evaluators} /><div className="actions"><SubmitButton>Cadastrar colaborador</SubmitButton></div></form>
        </details>
      </section>

      <section className="section panel flush-panel">
        <div className="panel-head padded"><div><p className="eyebrow">Hierarquia de avaliação</p><h2>Vínculos de equipe</h2><p>Associe funcionários e lideranças ao avaliador ou coordenador responsável.</p></div><span className="badge">{linked.length} vínculo(s)</span></div>
        {unlinked.length ? <form action={saveEmployeeEvaluatorLinkAction} className="filter-bar embedded">
          <div className="field compact grow"><label>Pessoa sem vínculo</label><select name="employee_id" required>{unlinked.map((employee) => <option key={employee.id} value={employee.id}>{employee.name} · {employee.is_leadership ? "Liderança" : employee.role}</option>)}</select></div>
          <div className="field compact grow"><label>Avaliador / coordenador</label><select name="evaluator_employee_id" required><option value="">Selecione</option>{evaluators.map((evaluator) => <option key={evaluator.id} value={evaluator.id}>{evaluator.name} · {evaluator.role}</option>)}</select></div>
          <SubmitButton className="button primary compact-button"><Network size={15} /> Criar vínculo</SubmitButton>
        </form> : <div className="notice info">Não há pessoas ativas sem vínculo.</div>}
        <div className="table-wrap borderless">
          <table className="dense-table"><thead><tr><th>Pessoa</th><th>Perfil</th><th>Responsável atual</th><th>Alterar vínculo</th><th /></tr></thead><tbody>{linked.map((employee) => <tr key={employee.id}>
            <td><strong>{employee.name}</strong><br /><small className="muted">{employee.sector} · {employee.role}</small></td>
            <td><span className={`status-chip ${employee.is_leadership ? "warning" : "neutral"}`}>{employee.is_leadership ? "Liderança" : "Operação"}</span></td>
            <td><strong>{employee.evaluator_name}</strong></td>
            <td><form action={saveEmployeeEvaluatorLinkAction} className="row-actions"><input type="hidden" name="employee_id" value={employee.id} /><select name="evaluator_employee_id" defaultValue={employee.evaluator_employee_id || ""} required>{evaluators.filter((evaluator) => evaluator.id !== employee.id).map((evaluator) => <option key={evaluator.id} value={evaluator.id}>{evaluator.name}</option>)}</select><SubmitButton className="button ghost compact-button">Atualizar</SubmitButton></form></td>
            <td><form action={deleteEmployeeEvaluatorLinkAction}><input type="hidden" name="employee_id" value={employee.id} /><button className="icon-button danger" type="submit" aria-label={`Remover vínculo de ${employee.name}`}><Unlink size={15} /></button></form></td>
          </tr>)}</tbody></table>
          {!linked.length ? <div className="empty-state compact"><Network size={26} /><strong>Nenhum vínculo cadastrado</strong><span>Crie o primeiro vínculo acima.</span></div> : null}
        </div>
      </section>

      <section className="section panel flush-panel">
        <div className="panel-head padded"><div><p className="eyebrow">Diretório</p><h2>{rows.length} pessoa(s)</h2><p>Abra um perfil para consultar histórico e editar o cadastro.</p></div></div>
        <form method="get" className="filter-bar embedded">
          <div className="field compact grow with-icon"><label>Buscar</label><Search size={16} /><input name="q" defaultValue={params.q} placeholder="Nome, setor ou função" /></div>
          <div className="field compact"><label>Setor</label><select name="sector" defaultValue={sector}><option value="">Todos</option>{sectors.map((item) => <option key={item}>{item}</option>)}</select></div>
          <div className="field compact"><label>Status</label><select name="status" defaultValue={status}><option value="active">Ativos</option><option value="inactive">Inativos</option><option value="all">Todos</option></select></div>
          <button className="button secondary" type="submit">Aplicar</button>
        </form>
        <div className="table-wrap borderless">
          <table className="dense-table"><thead><tr><th>Colaborador</th><th>Setor / função</th><th>Avaliador / coord.</th><th>Admissão</th><th>Perfil</th><th>Status</th><th /></tr></thead><tbody>{rows.map((employee) => <tr key={employee.id}><td><div className="person-cell"><span className="user-avatar pale">{employee.name.slice(0, 2).toUpperCase()}</span><div><strong>{employee.name}</strong><small>#{employee.id}</small></div></div></td><td>{employee.sector}<br /><small className="muted">{employee.role}</small></td><td>{employee.evaluator_name || (employee.is_leadership ? <span className="muted">Coordenação geral</span> : <span className="status-chip danger">Sem vínculo</span>)}</td><td>{dateBr(employee.hire_date)}{employee.termination_date ? <><br /><small className="muted">Saída: {dateBr(employee.termination_date)}</small></> : null}</td><td>{employee.is_leadership ? <span className="status-chip warning">Coord./Sup.</span> : employee.is_monitor ? <span className="status-chip success">Monitor</span> : <span className="status-chip neutral">Operação</span>}</td><td><span className={`status-chip ${employee.active ? "success" : "danger"}`}>{employee.active ? "Ativo" : "Inativo"}</span></td><td><Link className="button ghost compact-button" href={`/funcionarios/${employee.id}`}>Abrir perfil <ArrowRight size={15} /></Link></td></tr>)}</tbody></table>
          {!rows.length ? <div className="empty-state"><Users size={28} /><strong>Nenhuma pessoa encontrada</strong><span>Ajuste os filtros de busca.</span></div> : null}
        </div>
      </section>
    </>
  );
}
