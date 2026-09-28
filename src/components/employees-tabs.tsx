import Link from "next/link";
import { Network, Users } from "lucide-react";

export function EmployeesTabs({ active }: { active: "people" | "links" }) {
  return (
    <nav className="page-tabs" aria-label="Cadastros de pessoas">
      <Link className={`page-tab ${active === "people" ? "active" : ""}`} href="/funcionarios" aria-current={active === "people" ? "page" : undefined}>
        <Users size={16} /> Pessoas
      </Link>
      <Link className={`page-tab ${active === "links" ? "active" : ""}`} href="/funcionarios/vinculos" aria-current={active === "links" ? "page" : undefined}>
        <Network size={16} /> Vínculos de equipe
      </Link>
    </nav>
  );
}
