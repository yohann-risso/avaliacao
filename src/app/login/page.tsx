import { redirect } from "next/navigation";
import { AuthForm } from "@/components/auth-form";
import { currentUser } from "@/lib/auth";
import { loginUserCount } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  const user = await currentUser();
  if (user) redirect(user.role === "admin" ? "/funcionarios" : "/avaliacoes");

  let firstAccess = false;
  let configurationError = "";
  try {
    firstAccess = (await loginUserCount()) === 0;
  } catch (error) {
    configurationError = error instanceof Error ? error.message : "Não foi possível conectar ao banco.";
  }

  return (
    <div className="auth-shell">
      <section className="auth-brand">
        <span className="brand-mark">kaisan</span>
        <div>
          <p className="eyebrow">Operação · Estoque e expedição</p>
          <h1>Avaliação<br />& Bonificação</h1>
          <p>Controle semanal, monitoria e fechamento mensal em uma única rotina operacional.</p>
        </div>
        <small>Aplicação interna · acesso restrito</small>
      </section>
      <section className="auth-panel">
        <div className="auth-card">
          <p className="eyebrow">{firstAccess ? "Configuração inicial" : "Acesso seguro"}</p>
          <h2>{firstAccess ? "Crie o primeiro administrador" : "Bem-vindo de volta"}</h2>
          <p className="muted">{firstAccess ? "Este acesso terá permissão para cadastrar pessoas e novos usuários." : "Entre com as credenciais da operação."}</p>
          {configurationError ? <div className="notice error">{configurationError}</div> : <AuthForm firstAccess={firstAccess} />}
        </div>
      </section>
    </div>
  );
}
