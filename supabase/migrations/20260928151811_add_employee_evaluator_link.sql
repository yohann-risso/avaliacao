ALTER TABLE employees
ADD COLUMN IF NOT EXISTS evaluator_employee_id INTEGER REFERENCES employees(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_employees_evaluator_employee
ON employees(evaluator_employee_id, active, is_leadership);
