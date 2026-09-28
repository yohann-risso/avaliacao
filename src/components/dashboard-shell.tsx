"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ClipboardCheck, FileBarChart, LogOut, ShieldCheck, Star, Users } from "lucide-react";

import { logoutAction } from "@/app/actions/auth";
import type { DashboardStats } from "@/lib/data";
import type { AppUser } from "@/lib/types";

type NavItem = {
  href: string;
  label: string;
  detail: string;
  tone: "success" | "warning" | "danger";
  icon: React.ComponentType<{ size?: number }>;
};

export function DashboardShell({
  user,
  monthLabel,
  stats,
  children,
}: {
  user: AppUser;
  monthLabel: string;
  stats: DashboardStats;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const coverage = stats.weeklyExpected ? Math.round((stats.weeklyDone / stats.weeklyExpected) * 100) : 0;
  const adminItems: NavItem[] = [
    { href: "/funcionarios", label: "Funcionários", detail: `${stats.activeEmployees} ativos`, tone: stats.activeEmployees ? "success" : "warning", icon: Users },
    { href: "/usuarios", label: "Usuários", detail: `${stats.linkedUsers}/${stats.userCount} vinculados`, tone: stats.userCount && stats.linkedUsers === stats.userCount ? "success" : "warning", icon: ShieldCheck },
  ];
  const flowItems: NavItem[] = [
    { href: "/avaliacoes", label: "Avaliações", detail: `${coverage}% cobertura`, tone: coverage === 100 ? "success" : coverage ? "warning" : "danger", icon: ClipboardCheck },
    { href: "/monitoria", label: "Monitoria fixa", detail: `${stats.monitorCount} elegíveis`, tone: "success", icon: Star },
  ];
  const reportItems: NavItem[] = user.role === "admin"
    ? [{ href: "/relatorios", label: "Relatório", detail: `${stats.issues} pendências`, tone: stats.issues ? "danger" : "success", icon: FileBarChart }]
    : [];
  const items = [...(user.role === "admin" ? adminItems : []), ...flowItems, ...reportItems];

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-mark">kaisan</span>
          <div><strong>Avaliação &<br />Bonificação</strong><span>Estoque e expedição</span></div>
        </div>
        <div className="period-card"><span>Competência ativa</span><strong>{monthLabel}</strong></div>
        <nav className="nav-list" aria-label="Fluxo principal">
          {items.map((item, index) => {
            const active = pathname === item.href;
            return (
              <Link className={`nav-item ${active ? "active" : ""}`} href={item.href} key={item.href}>
                <span className="nav-number">{index + 1}</span>
                <span className="nav-copy"><strong>{item.label}</strong><small>{item.detail}</small></span>
                <span className={`status-dot ${item.tone}`} />
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-metrics">
          <div><span>Cobertura semanal</span><strong>{coverage}%</strong></div>
          <div><span>Pendências críticas</span><strong>{stats.issues}</strong></div>
          <div><span>Coord./Sup.</span><strong>{stats.leadershipCount}</strong></div>
        </div>
        <div className="user-block">
          <p>Logado como <strong>{user.username}</strong><br />({user.role})</p>
          <form action={logoutAction}><button className="button secondary" type="submit"><LogOut size={15} /> Sair</button></form>
        </div>
      </aside>
      <main className="main"><div className="content">{children}</div></main>
    </div>
  );
}
