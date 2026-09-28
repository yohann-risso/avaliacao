import Link from "next/link";

export default function NotFound() {
  return (
    <div className="auth-panel" style={{ minHeight: "100vh" }}>
      <div className="auth-card"><p className="eyebrow">404</p><h2>Página não encontrada</h2><p className="muted">O endereço informado não faz parte do fluxo.</p><Link className="button primary" href="/">Voltar ao início</Link></div>
    </div>
  );
}
