"use server";

import ExcelJS from "exceljs";
import { revalidatePath } from "next/cache";

import { integer, percentage, publicError, redirectWith, text } from "@/lib/action-utils";
import { requireUser } from "@/lib/auth";
import { WEEKLY_CRITERIA } from "@/lib/constants";
import { normalizeMonday } from "@/lib/dates";
import { sql } from "@/lib/db";
import { getEvaluationRule } from "@/lib/rules";

async function authorizedEvaluatorName(requested: string): Promise<string> {
  const user = await requireUser();
  if (user.role === "avaliador") {
    if (!user.evaluator_name) throw new Error("Seu usuário não está vinculado a um avaliador ativo.");
    return user.evaluator_name;
  }
  const evaluator = requested.trim();
  if (!evaluator) throw new Error("Selecione o avaliador.");
  const rows = await sql<{ name: string }[]>`
    select name from employees
    where active = 1 and coalesce(is_leadership, 0) = 1 and lower(name) = ${evaluator.toLowerCase()}
    limit 1
  `;
  if (!rows[0]) throw new Error("Avaliador inválido.");
  return rows[0].name;
}

export async function saveWeeklyEvaluationAction(formData: FormData): Promise<void> {
  await requireUser();
  const week = text(formData, "week_start");
  const employeeId = integer(formData, "employee_id");
  const path = `/avaliacoes?week=${encodeURIComponent(week)}&employee=${employeeId}`;
  try {
    if (!employeeId) throw new Error("Selecione o funcionário.");
    const weekStart = normalizeMonday(week);
    const employees = await sql<{ id: number }[]>`
      select id from employees where id = ${employeeId} and active = 1 and coalesce(is_leadership, 0) = 0 limit 1
    `;
    if (!employees[0]) throw new Error("Funcionário inativo ou não avaliável.");
    const evaluator = await authorizedEvaluatorName(text(formData, "evaluator"));
    const values = Object.fromEntries(WEEKLY_CRITERIA.map((criterion) => [criterion.key, percentage(formData, `${criterion.key}_pct`)]));
    const justifications = Object.fromEntries(WEEKLY_CRITERIA.map((criterion) => [criterion.key, text(formData, `${criterion.key}_just`)]));
    for (const criterion of WEEKLY_CRITERIA) {
      if (Number(values[criterion.key]) < 100 && !justifications[criterion.key]) {
        throw new Error(`Justifique o desconto em ${criterion.label}.`);
      }
    }
    const itemsCount = integer(formData, "items_count", -1);
    if (itemsCount < 0) throw new Error("Itens deve ser zero ou um número positivo.");
    const now = new Date().toISOString();
    await sql`
      insert into weekly_evaluations (
        employee_id, week_start, evaluator, notes, assiduidade_pct, qualidade_pct,
        taxa_erros_pct, produtividade_pct, comportamento_pct, efficiency_pct, items_count,
        created_at, assiduidade_just, qualidade_just, taxa_erros_just,
        produtividade_just, comportamento_just
      ) values (
        ${employeeId}, ${weekStart}, ${evaluator}, ${text(formData, "notes")},
        ${values.assiduidade}, ${values.qualidade}, ${values.taxa_erros},
        ${values.produtividade}, ${values.comportamento}, ${values.produtividade},
        ${itemsCount}, ${now}, ${justifications.assiduidade}, ${justifications.qualidade},
        ${justifications.taxa_erros}, ${justifications.produtividade}, ${justifications.comportamento}
      )
      on conflict (employee_id, week_start) do update set
        evaluator = excluded.evaluator, notes = excluded.notes,
        assiduidade_pct = excluded.assiduidade_pct, qualidade_pct = excluded.qualidade_pct,
        taxa_erros_pct = excluded.taxa_erros_pct, produtividade_pct = excluded.produtividade_pct,
        comportamento_pct = excluded.comportamento_pct, efficiency_pct = excluded.efficiency_pct,
        items_count = excluded.items_count, created_at = excluded.created_at,
        assiduidade_just = excluded.assiduidade_just, qualidade_just = excluded.qualidade_just,
        taxa_erros_just = excluded.taxa_erros_just, produtividade_just = excluded.produtividade_just,
        comportamento_just = excluded.comportamento_just
    `;
  } catch (error) {
    redirectWith(path, "error", publicError(error));
  }
  revalidatePath("/avaliacoes");
  redirectWith(path, "success", "Avaliação semanal salva.");
}

function workbookCell(row: ExcelJS.Row, headers: Map<string, number>, name: string): ExcelJS.CellValue {
  const column = headers.get(name.toLocaleLowerCase("pt-BR"));
  return column ? row.getCell(column).value : null;
}

function workbookText(value: ExcelJS.CellValue): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object" && "text" in value) return String(value.text || "").trim();
  return String(value).trim();
}

function workbookNumber(value: ExcelJS.CellValue, label: string, min: number, max: number): number {
  const parsed = Number(workbookText(value).replace(",", "."));
  if (!Number.isFinite(parsed) || parsed < min || parsed > max) throw new Error(`${label}: valor inválido.`);
  return parsed;
}

function workbookDate(value: ExcelJS.CellValue): string {
  if (value instanceof Date) return normalizeMonday(value.toISOString().slice(0, 10));
  return normalizeMonday(workbookText(value));
}

export async function importWeeklyWorkbookAction(formData: FormData): Promise<void> {
  await requireUser();
  const fallbackWeek = text(formData, "week_start");
  const path = `/avaliacoes?week=${encodeURIComponent(fallbackWeek)}`;
  try {
    if (formData.get("confirm") !== "on") throw new Error("Confirme que revisou a planilha antes de importar.");
    const file = formData.get("workbook");
    if (!(file instanceof File) || !file.size) throw new Error("Selecione um arquivo XLSX.");
    if (file.size > 10 * 1024 * 1024) throw new Error("O arquivo deve ter no máximo 10 MB.");
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.load(await file.arrayBuffer());
    const sheet = workbook.getWorksheet("Avaliacoes") || workbook.worksheets[0];
    if (!sheet) throw new Error("A planilha não contém uma aba de avaliações.");
    const headers = new Map<string, number>();
    sheet.getRow(1).eachCell((cell, column) => headers.set(workbookText(cell.value).toLocaleLowerCase("pt-BR"), column));
    const requiredHeaders = ["employee_id", "semana", "itens", "assiduidade (%)", "qualidade (%)", "taxa erros (%)", "produtividade (%)", "comportamento (%)"];
    if (requiredHeaders.some((header) => !headers.has(header))) throw new Error("O XLSX não corresponde ao modelo de avaliações exportado pelo sistema.");

    const parsedRows: Array<{
      employeeId: number; weekStart: string; items: number; evaluator: string; notes: string;
      assiduidade: number; qualidade: number; taxa: number; produtividade: number; comportamento: number;
    }> = [];
    sheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return;
      const idValue = workbookText(workbookCell(row, headers, "employee_id"));
      if (!idValue) return;
      const employeeId = Number(idValue);
      if (!Number.isInteger(employeeId) || employeeId < 1) throw new Error(`Linha ${rowNumber}: employee_id inválido.`);
      parsedRows.push({
        employeeId,
        weekStart: workbookDate(workbookCell(row, headers, "semana")),
        items: workbookNumber(workbookCell(row, headers, "itens"), `Linha ${rowNumber}, itens`, 0, 100_000_000),
        assiduidade: workbookNumber(workbookCell(row, headers, "assiduidade (%)"), `Linha ${rowNumber}, assiduidade`, 0, 100),
        qualidade: workbookNumber(workbookCell(row, headers, "qualidade (%)"), `Linha ${rowNumber}, qualidade`, 0, 100),
        taxa: workbookNumber(workbookCell(row, headers, "taxa erros (%)"), `Linha ${rowNumber}, taxa de erros`, 0, 100),
        produtividade: workbookNumber(workbookCell(row, headers, "produtividade (%)"), `Linha ${rowNumber}, produtividade`, 0, 100),
        comportamento: workbookNumber(workbookCell(row, headers, "comportamento (%)"), `Linha ${rowNumber}, comportamento`, 0, 100),
        evaluator: workbookText(workbookCell(row, headers, "avaliador")),
        notes: workbookText(workbookCell(row, headers, "observações")),
      });
    });
    if (!parsedRows.length) throw new Error("Nenhuma linha preenchida foi encontrada.");
    const duplicateKeys = new Set<string>();
    for (const row of parsedRows) {
      const key = `${row.employeeId}:${row.weekStart}`;
      if (duplicateKeys.has(key)) throw new Error(`Há linhas duplicadas para o funcionário #${row.employeeId} na semana ${row.weekStart}.`);
      duplicateKeys.add(key);
    }
    const employeeIds = [...new Set(parsedRows.map((row) => row.employeeId))];
    const validEmployees = await sql<{ id: number }[]>`
      select id from employees where id in ${sql(employeeIds)} and active = 1 and coalesce(is_leadership, 0) = 0
    `;
    const validIds = new Set(validEmployees.map((item) => item.id));
    const invalid = employeeIds.find((id) => !validIds.has(id));
    if (invalid) throw new Error(`O funcionário #${invalid} está inativo, não existe ou pertence à liderança.`);
    const resolvedRows: typeof parsedRows = [];
    for (const row of parsedRows) resolvedRows.push({ ...row, evaluator: await authorizedEvaluatorName(row.evaluator) });
    const now = new Date().toISOString();
    await sql.begin(async (transaction) => {
      for (const row of resolvedRows) {
        const justification = (value: number, label: string) => value < 100 ? `${label}: resultado importado da planilha; revisar com o colaborador.` : "Resultado dentro do esperado.";
        await transaction`
          insert into weekly_evaluations (
            employee_id, week_start, evaluator, notes, assiduidade_pct, qualidade_pct,
            taxa_erros_pct, produtividade_pct, comportamento_pct, efficiency_pct, items_count,
            created_at, assiduidade_just, qualidade_just, taxa_erros_just,
            produtividade_just, comportamento_just
          ) values (
            ${row.employeeId}, ${row.weekStart}, ${row.evaluator}, ${row.notes}, ${row.assiduidade},
            ${row.qualidade}, ${row.taxa}, ${row.produtividade}, ${row.comportamento},
            ${row.produtividade}, ${row.items}, ${now},
            ${justification(row.assiduidade, "Assiduidade")}, ${justification(row.qualidade, "Qualidade")},
            ${justification(row.taxa, "Taxa de erros")}, ${justification(row.produtividade, "Produtividade")},
            ${justification(row.comportamento, "Comportamento")}
          )
          on conflict (employee_id, week_start) do update set
            evaluator = excluded.evaluator, notes = excluded.notes,
            assiduidade_pct = excluded.assiduidade_pct, qualidade_pct = excluded.qualidade_pct,
            taxa_erros_pct = excluded.taxa_erros_pct, produtividade_pct = excluded.produtividade_pct,
            comportamento_pct = excluded.comportamento_pct, efficiency_pct = excluded.efficiency_pct,
            items_count = excluded.items_count, created_at = excluded.created_at,
            assiduidade_just = excluded.assiduidade_just, qualidade_just = excluded.qualidade_just,
            taxa_erros_just = excluded.taxa_erros_just, produtividade_just = excluded.produtividade_just,
            comportamento_just = excluded.comportamento_just
        `;
      }
    });
    revalidatePath("/avaliacoes");
    redirectWith(path, "success", `${resolvedRows.length} avaliação(ões) importada(s).`);
  } catch (error) {
    redirectWith(path, "error", publicError(error));
  }
}

export async function addWeeklyOccurrenceAction(formData: FormData): Promise<void> {
  await requireUser();
  const week = text(formData, "week_start");
  const employeeId = integer(formData, "employee_id");
  const path = `/avaliacoes?week=${encodeURIComponent(week)}&employee=${employeeId}`;
  try {
    if (!employeeId) throw new Error("Selecione o funcionário.");
    const weekStart = normalizeMonday(week);
    const rows = await sql<{ role: string }[]>`
      select role from employees where id = ${employeeId} and active = 1 limit 1
    `;
    if (!rows[0]) throw new Error("Funcionário inválido.");
    const rule = getEvaluationRule(text(formData, "occurrence_code"));
    const quantity = integer(formData, "qty", -1);
    if (!rule) throw new Error("Código de ocorrência inválido.");
    if (quantity < 1) throw new Error("A quantidade deve ser maior que zero.");
    if (quantity > 31) throw new Error("A quantidade máxima por lançamento é 31.");
    await sql`
      insert into weekly_errors (employee_id, week_start, role_snapshot, error_type, severity, qty, notes, created_at)
      values (${employeeId}, ${weekStart}, ${rows[0].role}, ${rule.code}, ${rule.level}, ${quantity},
        ${text(formData, "occurrence_notes")}, ${new Date().toISOString()})
    `;
  } catch (error) {
    redirectWith(path, "error", publicError(error));
  }
  revalidatePath("/avaliacoes");
  redirectWith(path, "success", "Ocorrência registrada e desconto recalculado.");
}

export async function deleteWeeklyOccurrenceAction(formData: FormData): Promise<void> {
  await requireUser();
  const week = text(formData, "week_start");
  const employeeId = integer(formData, "employee_id");
  const path = `/avaliacoes?week=${encodeURIComponent(week)}&employee=${employeeId}`;
  try {
    const id = integer(formData, "id");
    if (!id) throw new Error("Registro inválido.");
    await sql`delete from weekly_errors where id = ${id} and employee_id = ${employeeId}`;
  } catch (error) {
    redirectWith(path, "error", publicError(error));
  }
  revalidatePath("/avaliacoes");
  redirectWith(path, "success", "Registro removido.");
}
