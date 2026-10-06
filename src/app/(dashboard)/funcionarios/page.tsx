import Link from "next/link";
import { ArrowRight, BadgeCheck, Plus, Search, Shield, Star, UserRoundX, Users } from "lucide-react";

import { createEmployeeAction } from "@/app/actions/employees";
import { EmployeeFields } from "@/components/employee-fields";
import { EmployeesTabs } from "@/components/employees-tabs";
import { Notice } from "@/components/notice";
import { PageHeader } from "@/components/page-header";
import { SubmitButton } from "@/components/submit-button";
import { requirePeopleManager } from "@/lib/auth";
import { dateBr } from "@/lib/dates";
import { listEmployees } from "@/lib/data";
import { employeesVisibleTo, evaluatorsVisibleTo } from "@/lib/employee-access";
import { canManageOrganizationRole, userRoleLabel } from "@/lib/permissions";

export default async function EmployeesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; sector?: string; status?: string; success?: string; error?: string }>;
}) {
  const [user, params] = await Promise.all([requirePeopleManager(), searchParams]);
  const allEmployees = await listEmployees(true);
  const employees = employeesVisibleTo(user, allEmployees);
  const evaluators = evaluatorsVisibleTo(user, allEmployees);
  const query = String(params.q || "").trim().toLocaleLowerCase("pt-BR");
  const sector = String(params.sector || "");
  const status = String(params.status || "active");
  const sectors = [...new Set(employees.map((item) => item.sector))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const rows = employees.filter((employee) => (!query || `${employee.name} ${employee.role} ${employee.sector}`.toLocaleLowerCase("pt-BR").includes(query)) && (!sector || employee.sector === sector) && (status === "all" || (status === "active" ? employee.active : !employee.active)));
  const active = employees.filter((item) => item.active);

  return (
    <>
      <PageHeader step="Base organizacional" title="Pessoas" subtitle="Cadastros, elegibilidade, perfis e histórico de performance." icon={Users} user={`${userRoleLabel(user.role)} · ${user.username}`} />
      <EmployeesTabs active="people" />
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
          <form action={createEmployeeAction} className="details-form"><EmployeeFields evaluators={evaluators} allowUnlinked={canManageOrganizationRole(user.role)} /><div className="actions"><SubmitButton>Cadastrar colaborador</SubmitButton></div></form>
        </details>
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
