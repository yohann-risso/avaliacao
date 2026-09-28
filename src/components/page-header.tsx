import type { LucideIcon } from "lucide-react";

export function PageHeader({
  step,
  title,
  subtitle,
  icon: Icon,
  user,
}: {
  step: string;
  title: string;
  subtitle: string;
  icon: LucideIcon;
  user: string;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{step}</p>
        <div className="page-title-row">
          <span className="page-icon"><Icon size={22} /></span>
          <div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
        </div>
      </div>
      <span className="user-pill"><span className="status-dot" />{user}</span>
    </header>
  );
}
