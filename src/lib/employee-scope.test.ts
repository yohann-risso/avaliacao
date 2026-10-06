import { describe, expect, it } from "vitest";

import { employeesVisibleTo, evaluatorsVisibleTo } from "@/lib/employee-scope";
import type { AppUser, Employee } from "@/lib/types";

const employees = [
  { id: 1, evaluator_employee_id: 10, is_leadership: 0 },
  { id: 2, evaluator_employee_id: 20, is_leadership: 0 },
  { id: 3, evaluator_employee_id: null, is_leadership: 0 },
  { id: 4, evaluator_employee_id: 30, is_leadership: 0 },
  { id: 10, evaluator_employee_id: null, is_leadership: 1 },
  { id: 20, evaluator_employee_id: 10, is_leadership: 1 },
  { id: 30, evaluator_employee_id: 20, is_leadership: 1 },
] as Employee[];

function user(overrides: Partial<AppUser>): AppUser {
  return {
    id: 1,
    username: "usuario",
    role: "avaliador",
    evaluator_employee_id: 10,
    evaluator_name: "Liderança 10",
    ...overrides,
  };
}

describe("employeesVisibleTo", () => {
  it("mantém todos os funcionários para administradores", () => {
    expect(employeesVisibleTo(user({ role: "admin" }), employees)).toEqual(employees);
  });

  it("mantém todos os funcionários e lideranças disponíveis para o RH", () => {
    const activeEmployees = employees.map((employee) => ({ ...employee, active: 1 })) as Employee[];
    expect(employeesVisibleTo(user({ role: "rh", evaluator_employee_id: null, evaluator_name: "" }), activeEmployees)).toEqual(activeEmployees);
    expect(evaluatorsVisibleTo(user({ role: "rh", evaluator_employee_id: null, evaluator_name: "" }), activeEmployees).map((employee) => employee.id)).toEqual([10, 20, 30]);
  });

  it("mostra ao avaliador sua equipe direta e as equipes das lideranças subordinadas", () => {
    expect(employeesVisibleTo(user({}), employees).map((employee) => employee.id)).toEqual([1, 2, 4, 20, 30]);
  });

  it("mantém o supervisor restrito à própria árvore", () => {
    expect(employeesVisibleTo(user({ role: "supervisor", evaluator_employee_id: 20, evaluator_name: "Liderança 20" }), employees).map((employee) => employee.id)).toEqual([2, 4, 30]);
  });

  it("oferece ao supervisor somente as lideranças da própria árvore", () => {
    const activeEmployees = employees.map((employee) => ({ ...employee, active: 1 })) as Employee[];
    expect(evaluatorsVisibleTo(user({ role: "supervisor", evaluator_employee_id: 20, evaluator_name: "Liderança 20" }), activeEmployees).map((employee) => employee.id)).toEqual([20, 30]);
  });

  it("não mostra funcionários quando o vínculo do login está ausente ou inativo", () => {
    expect(employeesVisibleTo(user({ evaluator_employee_id: null, evaluator_name: "" }), employees)).toEqual([]);
    expect(employeesVisibleTo(user({ evaluator_name: "" }), employees)).toEqual([]);
  });
});
