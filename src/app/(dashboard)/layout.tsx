import { DashboardShell } from "@/components/dashboard-shell";
import { requireUser } from "@/lib/auth";
import { currentMonth, monthBr } from "@/lib/dates";
import { getDashboardStats } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser();
  const month = currentMonth();
  const stats = await getDashboardStats(month, user);
  return <DashboardShell user={user} monthLabel={monthBr(month)} stats={stats}>{children}</DashboardShell>;
}
