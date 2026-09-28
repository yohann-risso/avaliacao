import { ShieldCheck } from "lucide-react";

import { createUserAction, updateUserAction } from "@/app/actions/users";
import { EvaluatorSelect } from "@/components/evaluator-select";
import { Notice } from "@/components/notice";
import { PageHeader } from "@/components/page-header";
import { SubmitButton } from "@/components/submit-button";
import { requireAdmin } from "@/lib/auth";
import { listEvaluators, listLoginUsers } from "@/lib/data";

export default async function UsersPage({ searchParams }: { searchParams: Promise<{ success?: string; error?: string }> }) {
  const [actor, users, evaluators, params] = await Promise.all([requireAdmin(), listLoginUsers(), listEvaluators(), searchParams]);
  return (
    <>
      <PageHeader step="Etapa 2" title="Usuários" subtitle="Acessos, perfis e vínculo com o avaliador da operação." icon={ShieldCheck} user={`Admin: ${actor.username}`} />
      <Notice success={params.success} error={params.error} />

      <section className="section">
        <div className="section-head"><div><p className="eyebrow">Acesso</p><h2 className="section-title">Novo usuário</h2></div></div>
        <form action={createUserAction} className="card">
          <div className="form-grid">
            <div className="field span-3"><label>Usuário *</label><input name="username" minLength={3} required /></div>
            <div className="field span-3"><label>Senha inicial *</label><input name="password" type="password" minLength={8} required /></div>
            <div className="field span-2"><label>Perfil *</label><select name="role" defaultValue="avaliador"><option value="avaliador">Avaliador</option><option value="admin">Administrador</option></select></div>
            <div className="field span-4"><label>Avaliador vinculado</label><EvaluatorSelect evaluators={evaluators} /></div>
          </div>
          <div className="actions" style={{ marginTop: 18 }}><SubmitButton>Cadastrar usuário</SubmitButton></div>
        </form>
      </section>

      <section className="section">
        <div className="section-head"><div><p className="eyebrow">Permissões</p><h2 className="section-title">Acessos cadastrados</h2></div><span className="badge">{users.length} usuários</span></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Usuário</th><th>Perfil</th><th>Avaliador</th><th>Status</th><th>Gerenciar</th></tr></thead>
            <tbody>
              {users.map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.username}</strong>{item.id === actor.id ? <><br /><small className="muted">Sessão atual</small></> : null}</td>
                  <td><span className="badge">{item.role === "admin" ? "Administrador" : "Avaliador"}</span></td>
                  <td>{item.evaluator_name || <span className="muted">Não vinculado</span>}<br /><small className="muted">{item.evaluator_sector}</small></td>
                  <td><span className={`badge ${item.active ? "success" : "danger"}`}>{item.active ? "Ativo" : "Inativo"}</span></td>
                  <td>
                    <details className="edit-row"><summary>Editar acesso</summary>
                      <form action={updateUserAction} className="inline-form">
                        <input type="hidden" name="id" value={item.id} />
                        <div className="form-grid">
                          <div className="field span-3"><label>Usuário</label><input name="username" defaultValue={item.username} required /></div>
                          <div className="field span-2"><label>Perfil</label><select name="role" defaultValue={item.role}><option value="avaliador">Avaliador</option><option value="admin">Administrador</option></select></div>
                          <div className="field span-3"><label>Avaliador</label><EvaluatorSelect evaluators={evaluators} defaultValue={item.evaluator_employee_id} /></div>
                          <div className="field span-2"><label>Nova senha</label><input name="password" type="password" placeholder="Manter atual" /></div>
                          <div className="field span-2"><label className="check"><input type="checkbox" name="active" defaultChecked={Boolean(item.active)} /> Acesso ativo</label></div>
                        </div>
                        <div className="actions" style={{ marginTop: 14 }}><SubmitButton>Salvar acesso</SubmitButton></div>
                      </form>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
