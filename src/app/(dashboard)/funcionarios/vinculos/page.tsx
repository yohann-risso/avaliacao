import { Network, Unlink } from "lucide-react";

import { deleteEmployeeEvaluatorLinkAction, saveEmployeeEvaluatorLinkAction } from "@/app/actions/employees";
import { EmployeesTabs } from "@/components/employees-tabs";
import { Notice } from "@/components/notice";
import { PageHeader } from "@/components/page-header";
import { SubmitButton } from "@/components/submit-button";
import { requirePeopleManager } from "@/lib/auth";
import { listEmployees } from "@/lib/data";
import { employeesVisibleTo, evaluatorsVisibleTo } from "@/lib/employee-access";
import { userRoleLabel } from "@/lib/permissions";

export default async function EmployeeLinksPage({
  searchParams,
}: {
  searchParams: Promise<{ success?: string; error?: string }>;
}) {
  const [user, params] = await Promise.all([requirePeopleManager(), searchParams]);
  const allEmployees = await listEmployees(true);
  const employees = employeesVisibleTo(user, allEmployees);
  const evaluators = evaluatorsVisibleTo(user, allEmployees);
  const active = employees.filter((employee) => employee.active);
  const unlinked = user.role === "admin" ? active.filter((employee) => !employee.evaluator_employee_id) : [];
  const linked = active.filter((employee) => employee.evaluator_employee_id);

  return (
    <>
      <PageHeader step="Base organizacional" title="Vínculos de equipe" subtitle="Defina quais funcionários e lideranças pertencem a cada avaliador ou coordenador." icon={Network} user={`${userRoleLabel(user.role)} · ${user.username}`} />
      <EmployeesTabs active="links" />
      <Notice success={params.success} error={params.error} />

      <section className="section panel flush-panel">
        <div className="panel-head padded"><div><p className="eyebrow">Hierarquia de avaliação</p><h2>Vínculos cadastrados</h2><p>Associe funcionários e lideranças ao avaliador ou coordenador responsável.</p></div><span className="badge">{linked.length} vínculo(s)</span></div>
        {unlinked.length ? <form action={saveEmployeeEvaluatorLinkAction} className="filter-bar embedded">
          <div className="field compact grow"><label>Pessoa sem vínculo</label><select name="employee_id" required>{unlinked.map((employee) => <option key={employee.id} value={employee.id}>{employee.name} · {employee.is_leadership ? "Liderança" : employee.role}</option>)}</select></div>
          <div className="field compact grow"><label>Avaliador / coordenador</label><select name="evaluator_employee_id" required><option value="">Selecione</option>{evaluators.map((evaluator) => <option key={evaluator.id} value={evaluator.id}>{evaluator.name} · {evaluator.role}</option>)}</select></div>
          <SubmitButton className="button primary compact-button"><Network size={15} /> Criar vínculo</SubmitButton>
        </form> : <div className="notice info">{user.role === "admin" ? "Não há pessoas ativas sem vínculo." : "Você pode alterar os responsáveis das pessoas que já pertencem à sua equipe."}</div>}
        <div className="table-wrap borderless">
          <table className="dense-table"><thead><tr><th>Pessoa</th><th>Perfil</th><th>Responsável atual</th><th>Alterar vínculo</th>{user.role === "admin" ? <th /> : null}</tr></thead><tbody>{linked.map((employee) => <tr key={employee.id}>
            <td><strong>{employee.name}</strong><br /><small className="muted">{employee.sector} · {employee.role}</small></td>
            <td><span className={`status-chip ${employee.is_leadership ? "warning" : "neutral"}`}>{employee.is_leadership ? "Liderança" : "Operação"}</span></td>
            <td><strong>{employee.evaluator_name}</strong></td>
            <td><form action={saveEmployeeEvaluatorLinkAction} className="row-actions"><input type="hidden" name="employee_id" value={employee.id} /><select name="evaluator_employee_id" defaultValue={employee.evaluator_employee_id || ""} required>{evaluators.filter((evaluator) => evaluator.id !== employee.id).map((evaluator) => <option key={evaluator.id} value={evaluator.id}>{evaluator.name}</option>)}</select><SubmitButton className="button ghost compact-button">Atualizar</SubmitButton></form></td>
            {user.role === "admin" ? <td><form action={deleteEmployeeEvaluatorLinkAction}><input type="hidden" name="employee_id" value={employee.id} /><button className="icon-button danger" type="submit" aria-label={`Remover vínculo de ${employee.name}`}><Unlink size={15} /></button></form></td> : null}
          </tr>)}</tbody></table>
          {!linked.length ? <div className="empty-state compact"><Network size={26} /><strong>Nenhum vínculo cadastrado</strong><span>Crie o primeiro vínculo acima.</span></div> : null}
        </div>
      </section>
    </>
  );
}
