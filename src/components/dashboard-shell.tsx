"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ComponentType, type ReactNode } from "react";
import {
  BookOpenCheck,
  ChevronRight,
  ClipboardCheck,
  FileCheck2,
  LayoutDashboard,
  LogOut,
  Menu,
  ShieldCheck,
  TriangleAlert,
  Users,
  X,
} from "lucide-react";

import { logoutAction } from "@/app/actions/auth";
import type { DashboardStats } from "@/lib/data";
import { canManagePeopleRole, userRoleLabel } from "@/lib/permissions";
import type { AppUser } from "@/lib/types";

type NavItem = {
  href: string;
  label: string;
  detail: string;
  icon: ComponentType<{ size?: number; strokeWidth?: number }>;
  adminOnly?: boolean;
  peopleManagerOnly?: boolean;
};

const mainNavigation: NavItem[] = [
  { href: "/visao-geral", label: "Visão geral", detail: "Ritmo da competência", icon: LayoutDashboard },
  { href: "/avaliacoes", label: "Avaliações", detail: "Cockpit semanal", icon: ClipboardCheck },
  { href: "/ocorrencias", label: "Ocorrências", detail: "Regras e impactos", icon: TriangleAlert },
  { href: "/funcionarios", label: "Pessoas", detail: "Cadastro e histórico", icon: Users, peopleManagerOnly: true },
  { href: "/relatorios", label: "Fechamento", detail: "Conferência mensal", icon: FileCheck2, adminOnly: true },
];

const adminNavigation: NavItem[] = [
  { href: "/usuarios", label: "Usuários", detail: "Acessos e perfis", icon: ShieldCheck, adminOnly: true },
  { href: "/regras", label: "Regras", detail: "Tabela corporativa", icon: BookOpenCheck, adminOnly: true },
];

export function DashboardShell({
  user,
  monthLabel,
  stats,
  children,
}: {
  user: AppUser;
  monthLabel: string;
  stats: DashboardStats;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const coverage = stats.weeklyExpected ? Math.round((stats.weeklyDone / stats.weeklyExpected) * 100) : 0;
  const visibleMain = mainNavigation.filter((item) => (
    (!item.adminOnly || user.role === "admin")
    && (!item.peopleManagerOnly || canManagePeopleRole(user.role))
  ));
  const visibleAdmin = adminNavigation.filter((item) => !item.adminOnly || user.role === "admin");

  function navLink(item: NavItem) {
    const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
    const Icon = item.icon;
    return (
      <Link className={`nav-item ${active ? "active" : ""}`} href={item.href} key={item.href} onClick={() => setMobileOpen(false)}>
        <span className="nav-icon"><Icon size={18} strokeWidth={2} /></span>
        <span className="nav-copy"><strong>{item.label}</strong><small>{item.detail}</small></span>
        <ChevronRight className="nav-chevron" size={15} />
      </Link>
    );
  }

  return (
    <div className="dashboard">
      <button className={`sidebar-backdrop ${mobileOpen ? "visible" : ""}`} type="button" onClick={() => setMobileOpen(false)} aria-label="Fechar menu" />
      <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <div className="sidebar-brand">
          <span className="brand-mark">K</span>
          <div><strong>Kaisan</strong><span>Gestão de performance</span></div>
          <button className="icon-button sidebar-close" type="button" onClick={() => setMobileOpen(false)} aria-label="Fechar menu"><X size={18} /></button>
        </div>

        <div className="period-card">
          <div><span>Competência</span><strong>{monthLabel}</strong></div>
          <span className={`coverage-pill ${coverage === 100 ? "complete" : ""}`}>{coverage}%</span>
          <div className="progress-track"><span style={{ width: `${Math.min(100, coverage)}%` }} /></div>
          <small>{stats.weeklyDone} de {stats.weeklyExpected} avaliações concluídas</small>
        </div>

        <nav aria-label="Navegação principal">
          <p className="nav-label">Operação</p>
          <div className="nav-list">{visibleMain.map(navLink)}</div>
          {visibleAdmin.length ? <><p className="nav-label nav-label-spaced">Administração</p><div className="nav-list">{visibleAdmin.map(navLink)}</div></> : null}
        </nav>

        <div className="sidebar-signal">
          <span className={`signal-icon ${stats.issues ? "warning" : "success"}`}><TriangleAlert size={16} /></span>
          <div><strong>{stats.issues ? `${stats.issues} pendência(s)` : "Operação em dia"}</strong><small>{stats.issues ? "Acompanhe antes do fechamento" : "Nenhuma pendência crítica"}</small></div>
        </div>

        <div className="user-block">
          <span className="user-avatar">{user.username.slice(0, 2).toUpperCase()}</span>
          <div><strong>{user.username}</strong><small>{userRoleLabel(user.role)}</small></div>
          <form action={logoutAction}><button className="icon-button" type="submit" aria-label="Sair"><LogOut size={17} /></button></form>
        </div>
      </aside>

      <main className="main">
        <div className="mobile-topbar">
          <button className="icon-button" type="button" onClick={() => setMobileOpen(true)} aria-label="Abrir menu"><Menu size={20} /></button>
          <span><strong>Kaisan</strong><small>{monthLabel}</small></span>
          <span className={`coverage-pill ${coverage === 100 ? "complete" : ""}`}>{coverage}%</span>
        </div>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
