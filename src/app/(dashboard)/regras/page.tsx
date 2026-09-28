import { BookOpenCheck, CalendarRange, Coins, LockKeyhole } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { requireUser } from "@/lib/auth";
import { MONITOR_FIXED_VALUE } from "@/lib/constants";
import { brl } from "@/lib/money";
import { EVALUATION_RULES } from "@/lib/rules";

export default async function RulesPage() {
  const user = await requireUser();
  return (
    <>
      <PageHeader step="Referência corporativa" title="Regras de bonificação" subtitle="Fonte única para códigos, ocorrências e descontos usados pelo cálculo." icon={BookOpenCheck} user={`${user.username} · ${user.role}`} />
      <div className="metric-grid section">
        <article className="metric-card"><span className="metric-icon blue"><BookOpenCheck size={19} /></span><div><small>Regras ativas</small><strong>{EVALUATION_RULES.length}</strong><p>A01–A08, Q, P e C</p></div></article>
        <article className="metric-card"><span className="metric-icon amber"><Coins size={19} /></span><div><small>Interpretação de pontos</small><strong>Desconto</strong><p>Referência monetária por semana</p></div></article>
        <article className="metric-card"><span className="metric-icon green"><CalendarRange size={19} /></span><div><small>Competência</small><strong>4 semanas</strong><p>Divisor fixo no cálculo</p></div></article>
        <article className="metric-card"><span className="metric-icon green"><LockKeyhole size={19} /></span><div><small>Monitoria</small><strong>{brl(MONITOR_FIXED_VALUE)}</strong><p>Valor fixo, sem avaliação</p></div></article>
      </div>
      <section className="section panel flush-panel">
        <div className="panel-head padded"><div><p className="eyebrow">Tabela vigente</p><h2>Ocorrências e diretrizes</h2><p>O sistema limita o desconto ao valor efetivamente disponível em cada quesito.</p></div><span className="badge success">Documento implementado</span></div>
        <div className="table-wrap borderless"><table className="dense-table"><thead><tr><th>Código</th><th>Categoria</th><th>Motivo / ocorrência</th><th>Nível</th><th>Pontos</th><th>Diretriz corporativa</th></tr></thead><tbody>{EVALUATION_RULES.map((rule) => <tr key={rule.code}><td><span className={`rule-code ${rule.level === "CRITICO" ? "danger" : rule.level === "ALTO" ? "warning" : ""}`}>{rule.code}</span></td><td>{rule.category}</td><td><strong>{rule.occurrence}</strong></td><td><span className={`status-chip ${rule.level === "CRITICO" ? "danger" : rule.level === "ALTO" ? "warning" : "neutral"}`}>{rule.level}</span></td><td><strong>{rule.points.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}</strong></td><td>{rule.directive}</td></tr>)}</tbody></table></div>
      </section>
    </>
  );
}
