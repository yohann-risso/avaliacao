import type { Employee } from "@/lib/types";

export function EmployeeFields({ employee }: { employee?: Employee }) {
  return (
    <div className="form-grid">
      {employee ? <input type="hidden" name="id" value={employee.id} /> : null}
      <div className="field span-4"><label>Nome *</label><input name="name" defaultValue={employee?.name} required /></div>
      <div className="field span-4"><label>Setor *</label><input name="sector" defaultValue={employee?.sector} required /></div>
      <div className="field span-4"><label>Função *</label><input name="role" defaultValue={employee?.role} required /></div>
      <div className="field span-3"><label>Contratação *</label><input name="hire_date" type="date" defaultValue={employee?.hire_date} required /></div>
      <div className="field span-3"><label>Desligamento</label><input name="termination_date" type="date" defaultValue={employee?.termination_date} /></div>
      <div className="field span-3"><label className="check"><input name="is_monitor" type="checkbox" defaultChecked={Boolean(employee?.is_monitor)} /> É monitor?</label></div>
      <div className="field span-3"><label>Monitor desde</label><input name="monitor_start_date" type="date" defaultValue={employee?.monitor_start_date} /></div>
      <div className="field span-3"><label className="check"><input name="is_leadership" type="checkbox" defaultChecked={Boolean(employee?.is_leadership)} /> Coord./Supervisão?</label></div>
      <div className="field span-3"><label>Coord./Sup. desde</label><input name="leadership_start_date" type="date" defaultValue={employee?.leadership_start_date} /></div>
    </div>
  );
}
