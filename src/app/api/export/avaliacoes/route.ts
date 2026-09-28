import ExcelJS from "exceljs";

import { requireUser } from "@/lib/auth";
import { normalizeMonday, todayBrazil } from "@/lib/dates";
import { listActiveEmployees, listWeeklyEvaluations } from "@/lib/data";
import { employeesVisibleTo } from "@/lib/employee-access";
import { EVALUATION_RULES } from "@/lib/rules";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const user = await requireUser();
  const requested = new URL(request.url).searchParams.get("week") || todayBrazil();
  const week = normalizeMonday(requested);
  const allEmployees = await listActiveEmployees();
  const employees = employeesVisibleTo(user, allEmployees).filter((item) => !item.is_leadership);
  const evaluations = await listWeeklyEvaluations([week], employees.map((employee) => employee.id));
  const byEmployee = new Map(evaluations.map((item) => [item.employee_id, item]));
  const workbook = new ExcelJS.Workbook();
  workbook.creator = "Avaliação & Bonificação";
  workbook.created = new Date();
  const sheet = workbook.addWorksheet("Avaliacoes", { views: [{ state: "frozen", ySplit: 1 }] });
  sheet.columns = [
    { header: "employee_id", key: "employee_id", width: 13 },
    { header: "Funcionário", key: "name", width: 30 },
    { header: "Setor", key: "sector", width: 22 },
    { header: "Função", key: "role", width: 24 },
    { header: "Semana", key: "week", width: 14 },
    { header: "Itens", key: "items", width: 11 },
    { header: "Assiduidade (%)", key: "assiduidade", width: 18 },
    { header: "Qualidade (%)", key: "qualidade", width: 16 },
    { header: "Taxa erros (%)", key: "taxa", width: 17 },
    { header: "Produtividade (%)", key: "produtividade", width: 20 },
    { header: "Comportamento (%)", key: "comportamento", width: 21 },
    { header: "Avaliador", key: "evaluator", width: 28 },
    { header: "Observações", key: "notes", width: 34 },
  ];
  for (const employee of employees) {
    const row = byEmployee.get(employee.id);
    sheet.addRow({
      employee_id: employee.id, name: employee.name, sector: employee.sector, role: employee.role,
      week, items: Number(row?.items_count || 0), assiduidade: Number(row?.assiduidade_pct ?? 100),
      qualidade: Number(row?.qualidade_pct ?? 100), taxa: Number(row?.taxa_erros_pct ?? 100),
      produtividade: Number(row?.produtividade_pct ?? 100), comportamento: Number(row?.comportamento_pct ?? 100),
      evaluator: String(row?.evaluator || ""), notes: String(row?.notes || ""),
    });
  }
  const header = sheet.getRow(1);
  header.font = { bold: true, color: { argb: "FFFFFFFF" } };
  header.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF173452" } };
  header.alignment = { vertical: "middle" };
  header.height = 24;
  sheet.autoFilter = { from: "A1", to: "M1" };
  for (let rowIndex = 2; rowIndex <= sheet.rowCount; rowIndex += 1) {
    for (const column of [7, 8, 9, 10, 11]) {
      sheet.getCell(rowIndex, column).dataValidation = { type: "decimal", operator: "between", formulae: [0, 100], allowBlank: false };
    }
  }
  const instructions = workbook.addWorksheet("Instrucoes");
  instructions.addRows([
    ["Planilha de avaliação semanal"],
    ["A semana está normalizada para segunda-feira."],
    ["Percentuais aceitam valores de 0 a 100. Revise os dados na aplicação antes de salvar."],
    ["Ocorrências não alteram a nota: o sistema aplica os descontos da aba Regras depois da faixa de pagamento."],
    ["Esta exportação é destinada à conferência e preenchimento assistido."],
  ]);
  instructions.getCell("A1").font = { bold: true, size: 16, color: { argb: "FF173452" } };
  instructions.getColumn(1).width = 100;
  const rules = workbook.addWorksheet("Regras", { views: [{ state: "frozen", ySplit: 1 }] });
  rules.columns = [
    { header: "Código", key: "code", width: 12 },
    { header: "Categoria", key: "category", width: 20 },
    { header: "Ocorrência", key: "occurrence", width: 42 },
    { header: "Pontos", key: "points", width: 12 },
    { header: "Diretriz", key: "directive", width: 90 },
  ];
  for (const rule of EVALUATION_RULES) rules.addRow(rule);
  rules.getRow(1).font = { bold: true, color: { argb: "FFFFFFFF" } };
  rules.getRow(1).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF173452" } };
  rules.getColumn(5).alignment = { wrapText: true, vertical: "top" };
  const buffer = await workbook.xlsx.writeBuffer();
  return new Response(buffer, {
    headers: {
      "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "Content-Disposition": `attachment; filename="avaliacoes-${week}.xlsx"`,
      "Cache-Control": "private, no-store",
    },
  });
}
