"use client";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="auth-panel" style={{ minHeight: "100vh" }}>
      <div className="auth-card">
        <p className="eyebrow">Falha inesperada</p>
        <h2>Não foi possível carregar esta etapa</h2>
        <p className="muted">Confira a conexão com o banco e tente novamente.</p>
        <button className="button primary" onClick={reset}>Tentar novamente</button>
      </div>
    </div>
  );
}
