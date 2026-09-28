import type { Employee } from "@/lib/types";

export function EvaluatorSelect({ evaluators, defaultValue, required = false }: { evaluators: Employee[]; defaultValue?: number | null; required?: boolean }) {
  return (
    <select name="evaluator_employee_id" defaultValue={defaultValue || ""} required={required}>
      <option value="">Sem vínculo</option>
      {evaluators.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.role}</option>)}
    </select>
  );
}
