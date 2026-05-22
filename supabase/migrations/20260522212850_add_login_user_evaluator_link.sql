ALTER TABLE login_users ADD COLUMN IF NOT EXISTS evaluator_employee_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_login_users_evaluator_employee ON login_users(evaluator_employee_id);
