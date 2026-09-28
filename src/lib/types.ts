export type UserRole = "admin" | "avaliador";

export type AppUser = {
  id: number;
  username: string;
  role: UserRole;
  evaluator_employee_id: number | null;
  evaluator_name: string;
};

export type Employee = {
  id: number;
  name: string;
  sector: string;
  role: string;
  hire_date: string;
  monitor_start_date: string;
  leadership_start_date: string;
  termination_date: string;
  is_monitor: number;
  is_leadership: number;
  active: number;
  created_at: string;
  updated_at: string;
};

export type WeeklyEvaluation = Record<string, string | number | null> & {
  id: number;
  employee_id: number;
  week_start: string;
  evaluator: string;
};

export type WeeklyError = {
  id: number;
  employee_id: number;
  week_start: string;
  role_snapshot: string;
  error_type: string;
  severity: string;
  qty: number;
  notes: string;
  created_at: string;
};

export type WeeklyErrorWithEmployee = WeeklyError & {
  employee_name: string;
  employee_sector: string;
  employee_role: string;
};
