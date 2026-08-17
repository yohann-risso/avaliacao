import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = path.dirname(fileURLToPath(import.meta.url));
const workbook = Workbook.create();

const COLORS = {
  navy: "#173452",
  blue: "#347DA5",
  lightBlue: "#D9E9F2",
  surface: "#F4F9FC",
  line: "#C9D6DF",
  text: "#1F2D3D",
  muted: "#5B6B7A",
  greenFill: "#E4F4EB",
  greenText: "#146C43",
  redFill: "#FCE8E8",
  redText: "#B04557",
  amberFill: "#FFF3CD",
};

const errorTypes = [
  "Erro de Picking",
  "Produto sem Estoque (venda sem estoque)",
  "Divergencia de Enderecamento",
  "Pedido enviado errado",
  "Etiqueta/Documento incorreto",
  "Avaria",
  "Outro",
];

const severities = [
  ["BAIXO", "Baixo"],
  ["MEDIO", "Medio"],
  ["ALTO", "Alto"],
  ["CRITICO", "Critico"],
];

const headers = [
  "employee_id",
  "week_start",
  "role_snapshot",
  "error_type",
  "severity",
  "qty",
  "notes",
  "created_at",
  "funcionario_nome_conferencia",
  "status_validacao",
  "mensagem_validacao",
];

function styleTitle(sheet, rangeAddress, title, subtitle) {
  const titleRange = sheet.getRange(rangeAddress);
  titleRange.merge();
  titleRange.values = [[title]];
  titleRange.format = {
    fill: COLORS.navy,
    font: { bold: true, color: "#FFFFFF" },
  };
  titleRange.format.rowHeight = 30;

  const subtitleRange = sheet.getRange("A2:K2");
  subtitleRange.merge();
  subtitleRange.values = [[subtitle]];
  subtitleRange.format = {
    fill: COLORS.lightBlue,
    font: { color: COLORS.text },
  };
  subtitleRange.format.rowHeight = 24;
}

function setImportColumnWidths(sheet, lastRow = 505) {
  const widths = {
    A: 13,
    B: 14,
    C: 24,
    D: 34,
    E: 13,
    F: 8,
    G: 42,
    H: 22,
    I: 28,
    J: 17,
    K: 48,
  };
  for (const [col, width] of Object.entries(widths)) {
    sheet.getRange(`${col}1:${col}${lastRow}`).format.columnWidth = width;
  }
}

function styleImportSheet(sheet, totalRows = 505) {
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(5);
  setImportColumnWidths(sheet, totalRows);

  sheet.getRange("A5:K5").format = {
    fill: COLORS.blue,
    font: { bold: true, color: "#FFFFFF" },
  };
  sheet.getRange(`A5:K${totalRows}`).format.borders = {
    preset: "outside",
    style: "thin",
    color: COLORS.line,
  };
  sheet.getRange(`A6:F${totalRows}`).format = { fill: "#FFFFFF" };
  sheet.getRange(`G6:I${totalRows}`).format = { fill: COLORS.surface };
  sheet.getRange(`J6:K${totalRows}`).format = { fill: "#F8FAFC" };
  sheet.getRange(`A5:K${totalRows}`).format.wrapText = true;

  sheet.getRange(`A6:A${totalRows}`).setNumberFormat("0");
  sheet.getRange(`B6:B${totalRows}`).setNumberFormat("yyyy-mm-dd");
  sheet.getRange(`F6:F${totalRows}`).setNumberFormat("0");
  sheet.getRange(`H6:I${totalRows}`).setNumberFormat("@");
}

function addImportValidations(sheet, totalRows = 505) {
  sheet.getRange(`A6:A${totalRows}`).dataValidation = {
    rule: { type: "whole", operator: "between", formula1: 1, formula2: 999999 },
  };
  sheet.getRange(`D6:D${totalRows}`).dataValidation = {
    rule: { type: "list", formula1: "Listas!$A$5:$A$11" },
  };
  sheet.getRange(`E6:E${totalRows}`).dataValidation = {
    rule: { type: "list", formula1: "Listas!$B$5:$B$8" },
  };
  sheet.getRange(`F6:F${totalRows}`).dataValidation = {
    rule: { type: "whole", operator: "between", formula1: 1, formula2: 9999 },
  };
}

function addValidationFormulas(sheet, totalRows = 505) {
  sheet.getRange("J6").formulas = [[
    '=IF(COUNTA(A6:I6)=0,"",IF(AND(ISNUMBER(A6),A6>=1,ISNUMBER(B6),WEEKDAY(B6,2)=1,C6<>"",D6<>"",E6<>"",ISNUMBER(F6),F6>=1),"OK","REVISAR"))',
  ]];
  sheet.getRange("K6").formulas = [[
    '=IF(J6="","",IF(J6="OK","Pronto para importar","Confira employee_id, week_start em uma segunda-feira, role_snapshot, error_type, severity e qty >= 1"))',
  ]];
  sheet.getRange(`J6:J${totalRows}`).fillDown();
  sheet.getRange(`K6:K${totalRows}`).fillDown();

  const statusRange = sheet.getRange(`J6:J${totalRows}`);
  statusRange.conditionalFormats.add("containsText", {
    text: "OK",
    format: { fill: COLORS.greenFill, font: { bold: true, color: COLORS.greenText } },
  });
  statusRange.conditionalFormats.add("containsText", {
    text: "REVISAR",
    format: { fill: COLORS.redFill, font: { bold: true, color: COLORS.redText } },
  });
}

function addImportTable(sheet, rangeAddress, tableName) {
  const table = sheet.tables.add(rangeAddress, true, tableName);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
}

const importSheet = workbook.worksheets.add("Importacao_Erros");
styleTitle(
  importSheet,
  "A1:K1",
  "Modelo XLSX para Importacao de Erros",
  "Preencha uma linha por ocorrencia semanal. As colunas A:H seguem o log weekly_errors; I:K sao auxiliares."
);
importSheet.getRange("A4:K4").merge();
importSheet.getRange("A4:K4").values = [[
  "Use as listas nas colunas error_type e severity. Deixe created_at em branco para o importador preencher com a data/hora da carga.",
]];
importSheet.getRange("A4:K4").format = {
  fill: COLORS.amberFill,
  font: { color: COLORS.text },
};
importSheet.getRange("A5:K5").values = [headers];
styleImportSheet(importSheet);
addValidationFormulas(importSheet);
addImportValidations(importSheet);
addImportTable(importSheet, "A5:K505", "ErrosImportacao");

const listsSheet = workbook.worksheets.add("Listas");
listsSheet.showGridLines = false;
styleTitle(
  listsSheet,
  "A1:K1",
  "Listas de Validacao",
  "Valores aceitos pelo app para tipos de erro e gravidade."
);
listsSheet.getRange("A4:C4").values = [["error_type", "severity", "severity_label"]];
const maxRows = Math.max(errorTypes.length, severities.length);
const listRows = Array.from({ length: maxRows }, (_, idx) => [
  errorTypes[idx] ?? null,
  severities[idx]?.[0] ?? null,
  severities[idx]?.[1] ?? null,
]);
listsSheet.getRange(`A5:C${4 + maxRows}`).values = listRows;
listsSheet.getRange("A4:C4").format = {
  fill: COLORS.blue,
  font: { bold: true, color: "#FFFFFF" },
};
listsSheet.getRange(`A4:C${4 + maxRows}`).format.borders = {
  preset: "outside",
  style: "thin",
  color: COLORS.line,
};
listsSheet.getRange("A1:A20").format.columnWidth = 38;
listsSheet.getRange("B1:C20").format.columnWidth = 18;
addImportTable(listsSheet, `A4:C${4 + maxRows}`, "ListasValidacao");

const readmeSheet = workbook.worksheets.add("Leia_me");
readmeSheet.showGridLines = false;
styleTitle(
  readmeSheet,
  "A1:K1",
  "Leia_me",
  "Dicionario de campos do modelo de importacao de erros."
);
readmeSheet.getRange("A4:D4").values = [["Campo", "Obrigatorio", "Validacao", "Observacao"]];
readmeSheet.getRange("A4:D4").format = {
  fill: COLORS.blue,
  font: { bold: true, color: "#FFFFFF" },
};
const fieldRows = [
  ["employee_id", "Sim", "Inteiro maior que zero", "ID interno do funcionario no sistema. O id evita ambiguidade por nomes repetidos."],
  ["week_start", "Sim", "Data em uma segunda-feira", "Use formato yyyy-mm-dd. Exemplo: 2026-06-01."],
  ["role_snapshot", "Sim", "Texto", "Funcao do funcionario na semana do erro."],
  ["error_type", "Sim", "Lista da aba Listas", "Escolha um tipo padrao. Use Outro quando nao houver tipo melhor."],
  ["severity", "Sim", "BAIXO, MEDIO, ALTO ou CRITICO", "Use os codigos em maiusculas porque sao os valores salvos no app."],
  ["qty", "Sim", "Inteiro de 1 a 9999", "Quantidade de ocorrencias iguais na mesma semana."],
  ["notes", "Nao", "Texto livre", "Detalhe pedido, romaneio, causa raiz ou acao corretiva."],
  ["created_at", "Nao", "Texto ISO opcional", "Deixe em branco para o importador preencher; se usar, prefira yyyy-mm-ddTHH:MM:SS."],
  ["funcionario_nome_conferencia", "Nao", "Texto livre", "Apoio visual para conferencia. Nao substitui employee_id."],
  ["status_validacao", "Nao", "Formula", "Campo auxiliar; nao importar para a tabela weekly_errors."],
  ["mensagem_validacao", "Nao", "Formula", "Campo auxiliar; nao importar para a tabela weekly_errors."],
];
readmeSheet.getRange(`A5:D${4 + fieldRows.length}`).values = fieldRows;
readmeSheet.getRange(`A4:D${4 + fieldRows.length}`).format.borders = {
  preset: "outside",
  style: "thin",
  color: COLORS.line,
};
readmeSheet.getRange(`A5:D${4 + fieldRows.length}`).format.wrapText = true;
readmeSheet.getRange("A1:A20").format.columnWidth = 30;
readmeSheet.getRange("B1:B20").format.columnWidth = 14;
readmeSheet.getRange("C1:C20").format.columnWidth = 28;
readmeSheet.getRange("D1:D20").format.columnWidth = 64;
addImportTable(readmeSheet, `A4:D${4 + fieldRows.length}`, "DicionarioCampos");

readmeSheet.getRange("F4:I4").values = [["Resumo para importador", "", "", ""]];
readmeSheet.getRange("F4:I4").merge(true);
readmeSheet.getRange("F4:I4").format = {
  fill: COLORS.navy,
  font: { bold: true, color: "#FFFFFF" },
};
const importNotes = [
  ["Ler a aba", "Importacao_Erros"],
  ["Colunas de dados", "A:H"],
  ["Ignorar colunas", "I:K"],
  ["Tabela destino", "weekly_errors"],
  ["Nao importar", "id; e created_at se o processo gerar timestamp automatico"],
];
readmeSheet.getRange("F5:G9").values = importNotes;
readmeSheet.getRange("F5:G9").format.borders = {
  preset: "outside",
  style: "thin",
  color: COLORS.line,
};
readmeSheet.getRange("F1:F20").format.columnWidth = 20;
readmeSheet.getRange("G1:G20").format.columnWidth = 48;

const examplesSheet = workbook.worksheets.add("Exemplos");
styleTitle(
  examplesSheet,
  "A1:K1",
  "Exemplos",
  "Copie o padrao, mas nao importe esta aba."
);
examplesSheet.getRange("A5:K5").values = [headers];
examplesSheet.getRange("A6:I7").values = [
  [101, new Date(2026, 5, 1), "Auxiliar de Expedicao", "Pedido enviado errado", "CRITICO", 1, "Pedido 123 enviado para cliente incorreto.", "", "Maria Souza"],
  [102, new Date(2026, 5, 8), "Operador de Picking", "Erro de Picking", "MEDIO", 2, "SKU divergente em separacao.", "2026-06-23T09:30:00", "Joao Santos"],
];
styleImportSheet(examplesSheet, 20);
addValidationFormulas(examplesSheet, 20);
addImportValidations(examplesSheet, 20);
addImportTable(examplesSheet, "A5:K20", "ErrosExemplo");

const importInspect = await workbook.inspect({
  kind: "table",
  range: "Importacao_Erros!A1:K15",
  include: "values,formulas",
  tableMaxRows: 15,
  tableMaxCols: 11,
});
console.log(importInspect.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

for (const sheetName of ["Importacao_Erros", "Listas", "Leia_me", "Exemplos"]) {
  const preview = await workbook.render({
    sheetName,
    range: "A1:K18",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    path.join(outputDir, `preview_${sheetName}.png`),
    new Uint8Array(await preview.arrayBuffer())
  );
}

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(outputDir, "modelo_importacao_erros.xlsx"));
