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
  amber: "#FFF3CD",
  required: "#B04557",
  requiredFill: "#FCE8E8",
  optional: "#347DA5",
  formulaFill: "#E5E7EB",
  greenFill: "#E4F4EB",
  greenText: "#146C43",
  redFill: "#FCE8E8",
  redText: "#B04557",
};

const headers = [
  "Funcionário *",
  "ID (opcional)",
  "Data do ocorrido *",
  "Tipo do erro *",
  "Gravidade *",
  "Quantidade",
  "Observação",
  "Função (opcional)",
  "Criado em (opcional)",
  "Status da linha",
  "Orientação",
];

const errorTypes = [
  "Erro de Picking",
  "Produto sem Estoque (venda sem estoque)",
  "Divergencia de Enderecamento",
  "Pedido enviado errado",
  "Etiqueta/Documento incorreto",
  "Avaria",
  "Outro",
];

const severities = ["BAIXO", "MEDIO", "ALTO", "CRITICO"];

function title(sheet, main, sub, range = "A1:K1") {
  const r = sheet.getRange(range);
  r.merge();
  r.values = [[main]];
  r.format = {
    fill: COLORS.navy,
    font: { bold: true, color: "#FFFFFF" },
  };
  r.format.rowHeight = 30;

  const s = sheet.getRange("A2:K2");
  s.merge();
  s.values = [[sub]];
  s.format = {
    fill: COLORS.lightBlue,
    font: { color: COLORS.text },
  };
  s.format.rowHeight = 24;
}

function setWidths(sheet, maxRow = 305) {
  const widths = {
    A: 30,
    B: 13,
    C: 14,
    D: 34,
    E: 12,
    F: 8,
    G: 46,
    H: 24,
    I: 22,
    J: 16,
    K: 42,
  };
  for (const [col, width] of Object.entries(widths)) {
    sheet.getRange(`${col}1:${col}${maxRow}`).format.columnWidth = width;
  }
}

function styleImport(sheet, maxRow = 305) {
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(5);
  setWidths(sheet, maxRow);

  sheet.getRange("A4:K4").merge();
  sheet.getRange("A4:K4").values = [[
    "Campos em vermelho sao obrigatorios. Informe a data real em que o erro aconteceu; o sistema calcula a semana automaticamente.",
  ]];
  sheet.getRange("A4:K4").format = {
    fill: COLORS.amber,
    font: { color: COLORS.text },
  };

  sheet.getRange("A5:K5").values = [headers];
  sheet.getRange("A5:K5").format = {
    fill: COLORS.blue,
    font: { bold: true, color: "#FFFFFF" },
  };
  sheet.getRange("A5:A5").format = {
    fill: COLORS.required,
    font: { bold: true, color: "#FFFFFF" },
  };
  sheet.getRange("C5:E5").format = {
    fill: COLORS.required,
    font: { bold: true, color: "#FFFFFF" },
  };
  sheet.getRange("J5:K5").format = {
    fill: "#475569",
    font: { bold: true, color: "#FFFFFF" },
  };
  sheet.getRange(`A5:K${maxRow}`).format.borders = {
    preset: "outside",
    style: "thin",
    color: COLORS.line,
  };
  sheet.getRange(`A6:K${maxRow}`).format = { fill: "#FFFFFF" };
  sheet.getRange(`A6:A${maxRow}`).format = { fill: COLORS.requiredFill };
  sheet.getRange(`C6:E${maxRow}`).format = { fill: COLORS.requiredFill };
  sheet.getRange(`B6:B${maxRow}`).format = { fill: COLORS.surface };
  sheet.getRange(`F6:I${maxRow}`).format = { fill: "#FFFFFF" };
  sheet.getRange(`H6:I${maxRow}`).format = { fill: COLORS.surface };
  sheet.getRange(`J6:K${maxRow}`).format = { fill: COLORS.formulaFill, font: { color: "#475569" } };
  sheet.getRange(`A5:K${maxRow}`).format.wrapText = true;

  sheet.getRange(`B6:B${maxRow}`).setNumberFormat("0");
  sheet.getRange(`C6:C${maxRow}`).setNumberFormat("yyyy-mm-dd");
  sheet.getRange(`F6:F${maxRow}`).setNumberFormat("0");
  sheet.getRange(`I6:I${maxRow}`).setNumberFormat("@");
}

function addValidations(sheet, maxRow = 305) {
  sheet.getRange(`B6:B${maxRow}`).dataValidation = {
    rule: { type: "whole", operator: "between", formula1: 1, formula2: 999999 },
  };
  sheet.getRange(`D6:D${maxRow}`).dataValidation = {
    rule: { type: "list", formula1: "Listas!$A$4:$A$10" },
  };
  sheet.getRange(`E6:E${maxRow}`).dataValidation = {
    rule: { type: "list", formula1: "Listas!$B$4:$B$7" },
  };
  sheet.getRange(`F6:F${maxRow}`).dataValidation = {
    rule: { type: "whole", operator: "between", formula1: 1, formula2: 9999 },
  };
}

function addChecks(sheet, maxRow = 305) {
  sheet.getRange("J6").formulas = [[
    '=IF(COUNTA(A6:I6)=0,"",IF(AND(OR(A6<>"",AND(ISNUMBER(B6),B6>=1)),ISNUMBER(C6),D6<>"",E6<>"",OR(F6="",AND(ISNUMBER(F6),F6>=1))),"OK","REVISAR"))',
  ]];
  sheet.getRange("K6").formulas = [[
    '=IF(J6="","",IF(J6="OK","Pronto para pre-visualizar no app","Preencha funcionario, data do ocorrido, tipo do erro e gravidade"))',
  ]];
  sheet.getRange(`J6:J${maxRow}`).fillDown();
  sheet.getRange(`K6:K${maxRow}`).fillDown();

  const statusRange = sheet.getRange(`J6:J${maxRow}`);
  statusRange.conditionalFormats.add("containsText", {
    text: "OK",
    format: { fill: COLORS.greenFill, font: { bold: true, color: COLORS.greenText } },
  });
  statusRange.conditionalFormats.add("containsText", {
    text: "REVISAR",
    format: { fill: COLORS.redFill, font: { bold: true, color: COLORS.redText } },
  });
}

function addTable(sheet, range, name) {
  const table = sheet.tables.add(range, true, name);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
}

const importSheet = workbook.worksheets.add("Importacao_Erros");
title(
  importSheet,
  "Modelo para importar erros",
  "Preencha apenas a aba Importacao_Erros. O app calcula a semana pela data do ocorrido e mostra uma previa antes de gravar."
);
styleImport(importSheet);
addValidations(importSheet);
addChecks(importSheet);
addTable(importSheet, "A5:K305", "ImportacaoErrosOtimizada");

const lists = workbook.worksheets.add("Listas");
lists.showGridLines = false;
title(lists, "Listas", "Valores aceitos nos campos de selecao.");
lists.getRange("A3:C3").values = [["Tipo do erro", "Gravidade", "Uso"]];
lists.getRange("A3:C3").format = {
  fill: COLORS.blue,
  font: { bold: true, color: "#FFFFFF" },
};
const listRows = Array.from({ length: errorTypes.length }, (_, index) => [
  errorTypes[index],
  severities[index] ?? null,
  index === 0 ? "Use os dropdowns da aba Importacao_Erros." : null,
]);
lists.getRange(`A4:C${3 + listRows.length}`).values = listRows;
lists.getRange(`A3:C${3 + listRows.length}`).format.borders = {
  preset: "outside",
  style: "thin",
  color: COLORS.line,
};
lists.getRange("A1:A20").format.columnWidth = 38;
lists.getRange("B1:B20").format.columnWidth = 16;
lists.getRange("C1:C20").format.columnWidth = 44;
addTable(lists, `A3:C${3 + listRows.length}`, "ListasImportacaoErros");

const guide = workbook.worksheets.add("Guia_Rapido");
guide.showGridLines = false;
title(guide, "Guia rapido", "O importador mostra uma previa tratada antes de gravar.");
guide.getRange("A4:D4").values = [["Campo", "Preencher?", "Como o app trata", "Dica"]];
guide.getRange("A4:D4").format = {
  fill: COLORS.blue,
  font: { bold: true, color: "#FFFFFF" },
};
const guideRows = [
  ["Funcionário *", "Obrigatorio", "Busca exata, parcial ou aproximada no cadastro ativo.", "Use nome mais completo quando houver homonimos."],
  ["ID (opcional)", "Opcional", "Tem prioridade sobre o nome. Se invalido, tenta fallback pelo nome.", "Melhor campo para importacao sem ambiguidade."],
  ["Data do ocorrido *", "Obrigatorio", "O sistema calcula a segunda-feira da semana a partir desta data.", "Use a data real em que o erro aconteceu."],
  ["Tipo do erro *", "Obrigatorio", "Normaliza para os tipos padrao do sistema.", "Use o dropdown."],
  ["Gravidade *", "Obrigatorio", "Aceita BAIXO, MEDIO, ALTO ou CRITICO.", "Use codigo sem acento."],
  ["Quantidade", "Opcional", "Se vazio, assume 1. Se preenchido, precisa ser inteiro maior que zero.", "Agrupe ocorrencias iguais na mesma linha."],
  ["Observação", "Opcional", "Entra como observacao do log.", "Inclua pedido, romaneio, causa raiz ou acao."],
  ["Função (opcional)", "Opcional", "Se vazio, o app usa a funcao atual do funcionario.", "Preencha apenas se precisar congelar outra funcao."],
  ["Criado em (opcional)", "Opcional", "Se vazio ou invalido, o app preenche no momento da importacao.", "Use yyyy-mm-ddTHH:MM:SS se precisar."],
  ["Status da linha / Orientação", "Nao precisa preencher", "Sao formulas locais; o importador ignora essas colunas.", "Se apagar sem querer, baixe o modelo novamente."],
];
guide.getRange(`A5:D${4 + guideRows.length}`).values = guideRows;
guide.getRange(`A4:D${4 + guideRows.length}`).format.borders = {
  preset: "outside",
  style: "thin",
  color: COLORS.line,
};
guide.getRange(`A5:D${4 + guideRows.length}`).format.wrapText = true;
guide.getRange("A1:A20").format.columnWidth = 30;
guide.getRange("B1:B20").format.columnWidth = 22;
guide.getRange("C1:C20").format.columnWidth = 50;
guide.getRange("D1:D20").format.columnWidth = 46;
addTable(guide, `A4:D${4 + guideRows.length}`, "GuiaImportacaoErros");

const examples = workbook.worksheets.add("Exemplos");
title(examples, "Exemplos", "Copie para a aba Importacao_Erros se quiser testar. Nao importe esta aba.");
styleImport(examples, 30);
examples.getRange("A6:I8").values = [
  ["Ana Expedicao", null, new Date(2026, 5, 3), "Pedido enviado errado", "CRITICO", 1, "Pedido 123 enviado para cliente incorreto.", null, null],
  ["Joao Santos", 102, new Date(2026, 5, 1), "Erro de Picking", "MEDIO", 2, "SKU divergente em separacao.", "Operador de Picking", null],
  ["Maria Souza", null, new Date(2026, 5, 12), "Avaria", "BAIXO", null, "Avaria leve identificada na conferencia.", null, "2026-06-23T09:30:00"],
];
addValidations(examples, 30);
addChecks(examples, 30);
addTable(examples, "A5:K30", "ExemplosImportacaoErros");

const inspect = await workbook.inspect({
  kind: "table",
  range: "Importacao_Erros!A1:K14",
  include: "values,formulas",
  tableMaxRows: 14,
  tableMaxCols: 11,
});
console.log(inspect.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

for (const sheetName of ["Importacao_Erros", "Listas", "Guia_Rapido", "Exemplos"]) {
  const preview = await workbook.render({
    sheetName,
    range: sheetName === "Guia_Rapido" ? "A1:D18" : "A1:K18",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    path.join(outputDir, `preview_${sheetName}.png`),
    new Uint8Array(await preview.arrayBuffer())
  );
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(outputDir, "modelo_importacao_erros_otimizado.xlsx"));
