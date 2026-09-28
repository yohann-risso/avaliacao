import { Users } from "lucide-react";

import { createEmployeeAction, toggleEmployeeAction, updateEmployeeAction } from "@/app/actions/employees";
import { EmployeeFields } from "@/components/employee-fields";
import { Notice } from "@/components/notice";
import { PageHeader } from "@/components/page-header";
import { SubmitButton } from "@/components/submit-button";
import { requireAdmin } from "@/lib/auth";
import { dateBr } from "@/lib/dates";
import { listEmployees } from "@/lib/data";

export default async function EmployeesPage({
  searchParams,
}: {
  searchParams: Promise<{ success?: string; error?: string }>;
}) {
  const [user, employees, params] = await Promise.all([requireAdmin(), listEmployees(true), searchParams]);
  return (
    <>
      <PageHeader step="Etapa 1" title="Funcionários" subtitle="Cadastro administrativo com trilha de auditoria." icon={Users} user={`Admin: ${user.username}`} />
      <Notice success={params.success} error={params.error} />

      <section className="section">
        <div className="section-head"><div><p className="eyebrow">Cadastro</p><h2 className="section-title">Novo funcionário</h2></div></div>
        <form action={createEmployeeAction} className="card">
          <EmployeeFields />
          <div className="actions" style={{ marginTop: 18 }}><SubmitButton>Cadastrar funcionário</SubmitButton></div>
        </form>
      </section>

      <section className="section">
        <div className="section-head"><div><p className="eyebrow">Gestão</p><h2 className="section-title">Pessoas cadastradas</h2></div><span className="badge">{employees.length} registros</span></div>
        <div className="table-wrap">
          {employees.length ? (
            <table>
              <thead><tr><th>Funcionário</th><th>Setor / função</th><th>Datas</th><th>Perfil</th><th>Status e edição</th></tr></thead>
              <tbody>
                {employees.map((employee) => (
                  <tr key={employee.id}>
                    <td><strong>{employee.name}</strong><br /><small className="muted">#{employee.id}</small></td>
                    <td>{employee.sector}<br /><span className="muted">{employee.role}</span></td>
                    <td>Admissão: {dateBr(employee.hire_date)}<br /><span className="muted">Deslig.: {dateBr(employee.termination_date)}</span></td>
                    <td>{employee.is_leadership ? <span className="badge warning">Coord./Sup.</span> : employee.is_monitor ? <span className="badge success">Monitor</span> : <span className="badge">Operação</span>}</td>
                    <td>
                      <span className={`badge ${employee.active ? "success" : "danger"}`}>{employee.active ? "Ativo" : "Inativo"}</span>
                      <details className="edit-row">
                        <summary>Editar cadastro</summary>
                        <form action={updateEmployeeAction} className="inline-form">
                          <EmployeeFields employee={employee} />
                          <div className="actions" style={{ marginTop: 16 }}><SubmitButton>Salvar alterações</SubmitButton></div>
                        </form>
                        <form action={toggleEmployeeAction} style={{ marginTop: 10 }}>
                          <input type="hidden" name="id" value={employee.id} />
                          <input type="hidden" name="active" value={employee.active ? 0 : 1} />
                          <SubmitButton className={employee.active ? "button danger" : "button secondary"}>{employee.active ? "Desativar" : "Reativar"}</SubmitButton>
                        </form>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <div className="empty">Nenhum funcionário cadastrado.</div>}
        </div>
      </section>
    </>
  );
}
