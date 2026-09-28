from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


SOURCE = Path(r"C:\Users\yohan\Downloads\Kaisan_Avaliacao_e_Bonificacao_Corte_Estoque doc esse (1).docx")
OUTPUT = Path(r"C:\Users\yohan\Desktop\Python\avaliacao\output\docx\KAISAN_Avaliacao_e_Bonificacao_Corte_Estoque_Corrigido.docx")

BLACK = "000000"
GRAY = "666666"
RED = "C0392B"
BLUE = "365F91"
LIGHT_BLUE = "D9EAF7"
LIGHT_ROW = "F7FAFC"
GRID = "D9D9D9"


def set_run_font(run, size: float, *, bold: bool = False, italic: bool = False, color: str = BLACK) -> None:
    run.font.name = "Arial"
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:ascii"), "Arial")
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), "Arial")
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def clear_paragraph(paragraph) -> None:
    for child in list(paragraph._p):
        if child.tag != qn("w:pPr"):
            paragraph._p.remove(child)


def set_paragraph_spacing(paragraph, before: float = 0, after: float = 0, line: float = 1.05) -> None:
    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing = line


def add_segment(paragraph, text: str, *, size: float = 10.5, bold: bool = False, italic: bool = False, color: str = BLACK):
    run = paragraph.add_run(text)
    set_run_font(run, size, bold=bold, italic=italic, color=color)
    return run


def add_line_break(paragraph) -> None:
    paragraph.add_run().add_break(WD_BREAK.LINE)


def add_page_break(paragraph) -> None:
    paragraph.add_run().add_break(WD_BREAK.PAGE)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top: int = 80, start: int = 90, bottom: int = 80, end: int = 90) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color: str = GRID, size: int = 8) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        element = borders.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), str(size))
        element.set(qn("w:color"), color)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    header = tr_pr.find(qn("w:tblHeader"))
    if header is None:
        header = OxmlElement("w:tblHeader")
        tr_pr.append(header)
    header.set(qn("w:val"), "true")


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = tr_pr.find(qn("w:cantSplit"))
    if cant_split is None:
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)


def set_cell_text(cell, text: str, *, size: float, bold: bool = False, color: str = BLACK, align=None) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    if align is not None:
        paragraph.alignment = align
    set_paragraph_spacing(paragraph, 0, 0, 1.0)
    add_segment(paragraph, text, size=size, bold=bold, color=color)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def style_table(table, widths: list[float], *, header_fill: str = LIGHT_BLUE, body_size: float = 9.2, header_size: float = 9.2, stripe: bool = True) -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    for col_index, width in enumerate(widths):
        for row in table.rows:
            row.cells[col_index].width = Inches(width)
    for row_index, row in enumerate(table.rows):
        # Remove alturas fixas herdadas do arquivo-base; elas podem criar
        # grandes vazios quando o texto da linha é substituído.
        tr_pr = row._tr.get_or_add_trPr()
        for row_height in list(tr_pr.findall(qn("w:trHeight"))):
            tr_pr.remove(row_height)
        prevent_row_split(row)
        if row_index == 0:
            set_repeat_table_header(row)
        for col_index, cell in enumerate(row.cells):
            set_cell_margins(cell)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if row_index == 0:
                set_cell_shading(cell, header_fill)
            elif stripe and row_index % 2 == 0:
                set_cell_shading(cell, LIGHT_ROW)
            for paragraph in cell.paragraphs:
                set_paragraph_spacing(paragraph, 0, 0, 1.0)
                if col_index in (0, len(row.cells) - 1) and len(row.cells) <= 3:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in paragraph.runs:
                    set_run_font(run, header_size if row_index == 0 else body_size, bold=row_index == 0)


def set_heading_with_body(paragraph, heading: str, body: str, *, heading_size: float = 15, after: float = 8) -> None:
    clear_paragraph(paragraph)
    paragraph.style = "Normal"
    add_segment(paragraph, heading, size=heading_size, bold=True)
    add_line_break(paragraph)
    add_segment(paragraph, body, size=10.5)
    set_paragraph_spacing(paragraph, 0, after, 1.12)


def set_criterion_paragraph(paragraph, title: str, description: str, examples: str) -> None:
    clear_paragraph(paragraph)
    paragraph.style = "Normal"
    paragraph.paragraph_format.left_indent = Inches(0)
    paragraph.paragraph_format.first_line_indent = Inches(0)
    add_segment(paragraph, f"• {title}: ", size=10.5, bold=True)
    add_segment(paragraph, description, size=10.5)
    add_segment(paragraph, " Exemplos práticos: ", size=10.5, italic=True, color=GRAY)
    add_segment(paragraph, examples, size=10.5, italic=True, color=GRAY)
    set_paragraph_spacing(paragraph, 0, 8, 1.12)


def insert_paragraph_before(reference_paragraph, text: str = ""):
    new_p = OxmlElement("w:p")
    reference_paragraph._p.addprevious(new_p)
    paragraph = reference_paragraph._parent.add_paragraph()
    paragraph._p.getparent().remove(paragraph._p)
    new_p.getparent().replace(new_p, paragraph._p)
    if text:
        paragraph.add_run(text)
    return paragraph


def insert_table_before(document, reference_paragraph, rows: int, cols: int):
    table = document.add_table(rows=rows, cols=cols)
    table._tbl.getparent().remove(table._tbl)
    reference_paragraph._p.addprevious(table._tbl)
    return table


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    doc = Document(str(SOURCE))
    doc.core_properties.title = "Avaliação e Bonificação - Corte e Estoque"
    doc.core_properties.subject = "Critérios, ocorrências, faixas de pagamento e regras vigentes"
    doc.core_properties.author = "KAISAN"
    doc.core_properties.comments = "Documento ajustado conforme as regras vigentes do sistema em 28/09/2026."

    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.78)
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.72)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(0, 0, 0)

    title_style = doc.styles["Title"]
    title_style.font.name = "Arial"
    title_style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    title_style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    title_style.font.color.rgb = RGBColor(0, 0, 0)
    title_style.paragraph_format.space_after = Pt(12)
    title_ppr = title_style._element.get_or_add_pPr()
    title_border = title_ppr.find(qn("w:pBdr"))
    if title_border is not None:
        title_ppr.remove(title_border)

    paragraphs = doc.paragraphs
    tables = doc.tables

    cover = paragraphs[0]
    clear_paragraph(cover)
    cover.style = "Title"
    cover.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cover_border = cover._p.get_or_add_pPr().find(qn("w:pBdr"))
    if cover_border is not None:
        cover._p.get_or_add_pPr().remove(cover_border)
    add_segment(cover, "KAISAN", size=28, bold=True)
    add_line_break(cover)
    add_segment(cover, "USO INTERNO | 2026", size=10, color="808080")
    add_line_break(cover)
    add_line_break(cover)
    add_segment(cover, "Avaliação e Bonificação", size=22, bold=True)
    add_line_break(cover)
    add_segment(cover, "Critérios, exemplos práticos, ocorrências e valores de referência para colaboradores de Corte e Estoque.", size=11, italic=True)
    set_paragraph_spacing(cover, 4, 18, 1.0)

    set_heading_with_body(
        paragraphs[1],
        "Objetivo da avaliação",
        "Reconhecer o bom desempenho, alinhar expectativas e orientar melhorias de forma clara. A avaliação considera atitudes, entregas e ocorrências verificáveis do período.",
    )
    set_heading_with_body(
        paragraphs[2],
        "Valores por quesito",
        "Cada quesito é avaliado separadamente e possui um valor máximo mensal. O bônus-base mensal considera quatro semanas fixas.",
    )

    criteria_rows = [
        ["Quesito", "O que é observado", "Valor máximo"],
        ["Assiduidade", "Presença, pontualidade e regularidade na rotina.", "R$ 150,00"],
        ["Qualidade", "Cuidado na execução, conferência, padrão de entrega e retrabalho.", "R$ 100,00"],
        ["Taxa de erros", "Erros registrados, considerando quantidade, gravidade e repetição.", "R$ 100,00"],
        ["Produtividade", "Ritmo de trabalho, cumprimento de metas, volume e eficiência.", "R$ 100,00"],
        ["Comportamento", "Postura, disciplina, colaboração e respeito aos procedimentos.", "R$ 100,00"],
        ["Total da avaliação base", "Soma máxima dos quesitos avaliados.", "R$ 550,00"],
    ]
    for row, values in zip(tables[0].rows, criteria_rows):
        for cell, value in zip(row.cells, values):
            set_cell_text(cell, value, size=9.4, bold=row is tables[0].rows[0] or row is tables[0].rows[-1])
    style_table(tables[0], [1.55, 3.70, 1.25], body_size=9.4, header_size=9.4)

    important = paragraphs[3]
    clear_paragraph(important)
    add_segment(important, "Importante:", size=10.5, bold=True, color=RED)
    add_line_break(important)
    add_segment(important, "Um bom resultado em um quesito não substitui automaticamente outro. Produtividade alta, por exemplo, não elimina uma falha grave de qualidade, taxa de erros, assiduidade ou comportamento.", size=10.5, italic=True)
    set_paragraph_spacing(important, 12, 0, 1.12)

    # Mantém a quebra que inicia a página de exemplos.
    set_heading_with_body(
        paragraphs[5],
        "O que significa cada quesito",
        "Exemplos aplicados aos setores de Corte e Estoque.",
        heading_size=17,
        after=12,
    )
    criteria_examples = [
        ("Assiduidade", "Compromisso com presença, horários e rotina.", "Chegar no horário; cumprir a jornada combinada; comunicar a liderança conforme a política; evitar faltas e atrasos sem justificativa."),
        ("Qualidade", "Executar corretamente, com cuidado e atenção, evitando retrabalho.", "Conferir produtos, quantidades e ordens de produção; realizar o enfesto com precisão; armazenar itens no endereço correto; revisar informações antes da liberação."),
        ("Taxa de erros", "Ocorrências registradas que geram impacto ou retrabalho.", "Contagem incorreta no estoque; erro de corte com desperdício; identificação errada de lotes; guarda em endereço trocado."),
        ("Produtividade", "Manter entrega constante, bom ritmo e atenção às metas.", "Cumprir a meta de corte, enfesto, guarda ou separação; concluir tarefas no prazo; sustentar volume compatível com a função."),
        ("Comportamento", "Atuar com postura profissional e colaboração.", "Respeitar colegas e lideranças; seguir procedimentos e normas de segurança; cuidar dos equipamentos, ferramentas e materiais."),
    ]
    for paragraph, values in zip(paragraphs[6:11], criteria_examples):
        set_criterion_paragraph(paragraph, *values)

    rules_heading = paragraphs[12]
    clear_paragraph(rules_heading)
    add_segment(rules_heading, "Tabela de regras, ocorrências e descontos", size=17, bold=True)
    set_paragraph_spacing(rules_heading, 0, 12, 1.0)

    rules_rows = [
        ["Código", "Categoria", "Motivo / ocorrência", "Pontos", "Diretriz corporativa"],
        ["A01", "Assiduidade", "Falta sem atestado / alto", "250", "Perde 100% da assiduidade mensal e 100% dos outros quesitos na semana. A segunda A01 bloqueia todo o bônus-base mensal."],
        ["A02", "Assiduidade", "Falta com atestado / baixo", "47,5", "Perde 100% da assiduidade semanal e 20% por dia nos outros quesitos. A reincidência repete o desconto."],
        ["A03", "Assiduidade", "Declaração de até 50% da carga / baixo", "87,5", "Perde 100% da assiduidade semanal e 50% dos outros quesitos."],
        ["A04", "Assiduidade", "Declaração acima de 50% da carga / alto", "137,5", "Perde 100% de todos os quesitos da semana."],
        ["A05", "Assiduidade", "Saída por poucas horas / baixo", "37,5", "Perde 100% da assiduidade semanal."],
        ["A06", "Assiduidade", "Saída superior a 50% do dia / alto", "125", "Considera meia falta: perde 50% da assiduidade mensal e 50% dos outros quesitos na semana."],
        ["A07", "Assiduidade", "Atraso até 7h30 / baixo", "9,37", "Perde 25% da assiduidade semanal."],
        ["A08", "Assiduidade", "Atraso depois de 7h30 / alto", "37,5", "Perde 100% da assiduidade semanal."],
        ["Q01", "Qualidade", "Crítico", "50", "Perde 100% de Qualidade e Taxa de erros na semana."],
        ["Q02", "Qualidade", "Alto", "25", "Perde 50% de Qualidade e Taxa de erros na semana."],
        ["Q03", "Qualidade", "Médio", "12,5", "Perde 25% de Qualidade e Taxa de erros na semana."],
        ["Q04", "Qualidade", "Baixo", "5", "Perde 10% de Qualidade e Taxa de erros na semana."],
        ["P01", "Produtividade", "Crítico", "25", "Perde 100% da bonificação semanal de Produtividade."],
        ["P02", "Produtividade", "Alto", "12,5", "Perde 50% da bonificação semanal de Produtividade."],
        ["P03", "Produtividade", "Médio", "6,3", "Perde 25% da bonificação semanal de Produtividade."],
        ["P04", "Produtividade", "Baixo", "2,5", "Perde 10% da bonificação semanal de Produtividade."],
        ["C01", "Comportamento", "Crítico", "25", "Perde 100% da bonificação semanal de Comportamento. Cabe carta de advertência conforme o processo interno."],
        ["C02", "Comportamento", "Alto", "12,5", "Perde 50% da bonificação semanal de Comportamento."],
        ["C03", "Comportamento", "Médio", "6,3", "Perde 25% da bonificação semanal de Comportamento."],
        ["C04", "Comportamento", "Baixo", "2,5", "Perde 10% da bonificação semanal de Comportamento."],
    ]
    for row, values in zip(tables[1].rows, rules_rows):
        for col_index, (cell, value) in enumerate(zip(row.cells, values)):
            align = WD_ALIGN_PARAGRAPH.CENTER if col_index in (0, 3) else WD_ALIGN_PARAGRAPH.LEFT
            set_cell_text(cell, value, size=8.0, bold=row is tables[1].rows[0], align=align)
    style_table(tables[1], [0.62, 1.00, 1.43, 0.62, 2.83], body_size=8.0, header_size=8.0)

    # Remove a quebra manual herdada e força o início da seção no próprio
    # título. Isso evita que o Word posicione o primeiro título fora da área
    # útil quando a quebra sucede uma tabela longa.
    page_break = paragraphs[13]
    page_break._p.getparent().remove(page_break._p)

    proportional = paragraphs[14]
    clear_paragraph(proportional)
    proportional.style = "Normal"
    proportional.alignment = WD_ALIGN_PARAGRAPH.LEFT
    proportional.paragraph_format.left_indent = Inches(0)
    proportional.paragraph_format.right_indent = Inches(0)
    proportional.paragraph_format.first_line_indent = Inches(0)
    proportional.paragraph_format.keep_with_next = False
    proportional.paragraph_format.keep_together = False
    proportional.paragraph_format.page_break_before = True
    add_segment(proportional, "Tabela de proporcionalidade de pagamento", size=17, bold=True)
    add_line_break(proportional)
    add_segment(proportional, "A nota enquadra cada quesito em uma faixa. As ocorrências são aplicadas depois da faixa, respeitando o saldo disponível.", size=10.5)
    set_paragraph_spacing(proportional, 0, 12, 1.12)

    band_rows = [
        ["Resultado atingido no quesito", "Parcela do valor paga"],
        ["De 0% a 50%", "0%"],
        ["Acima de 50% até 70%", "25%"],
        ["Acima de 70% até 80%", "50%"],
        ["Acima de 80% até 90%", "75%"],
        ["Acima de 90% até 100%", "100%"],
    ]
    for row, values in zip(tables[2].rows, band_rows):
        for col_index, (cell, value) in enumerate(zip(row.cells, values)):
            set_cell_text(cell, value, size=9.6, bold=row is tables[2].rows[0], align=WD_ALIGN_PARAGRAPH.CENTER if col_index == 1 else WD_ALIGN_PARAGRAPH.LEFT)
    style_table(tables[2], [3.8, 2.7], body_size=9.6, header_size=9.6)

    example = paragraphs[15]
    clear_paragraph(example)
    add_segment(example, "Exemplo prático de cálculo: ", size=10.5, bold=True)
    add_segment(example, "se Qualidade possui teto mensal de R$ 100,00 e o colaborador alcança 85%, o quesito entra na faixa de 75%, pagando R$ 75,00 antes da aplicação das ocorrências.", size=10.5, italic=True)
    set_paragraph_spacing(example, 12, 12, 1.12)

    validation = paragraphs[16]
    complement_heading = insert_paragraph_before(validation)
    complement_heading.style = "Heading 1"
    add_segment(complement_heading, "Regras complementares do fechamento", size=15, bold=True)
    set_paragraph_spacing(complement_heading, 12, 6, 1.0)
    complement_heading.paragraph_format.keep_with_next = True

    complement_data = [
        ["Componente", "Regra vigente", "Valor"],
        ["Competência", "O bônus-base é dividido em quatro semanas fixas.", "Até R$ 550,00"],
        ["Monitoria", "Adicional fixo para monitor ativo e elegível. Não há avaliação mensal de monitoria.", "R$ 300,00"],
        ["Tempo de casa", "Adicional calculado por ano completo na data de referência do fechamento.", "R$ 30,00 por ano"],
        ["Coordenação e supervisão", "Quando elegíveis, não recebem avaliação semanal e ficam em grupo separado.", "Base de R$ 550,00"],
    ]
    complement_table = insert_table_before(doc, validation, rows=len(complement_data), cols=3)
    for row, values in zip(complement_table.rows, complement_data):
        for cell, value in zip(row.cells, values):
            set_cell_text(cell, value, size=8.8, bold=row is complement_table.rows[0])
    style_table(complement_table, [1.55, 3.75, 1.20], body_size=8.8, header_size=8.8)

    eligibility = insert_paragraph_before(validation)
    add_segment(eligibility, "Elegibilidade: ", size=9.4, bold=True)
    add_segment(eligibility, "a semana de contratação não conta; o colaborador entra somente em semana posterior à semana de admissão. Semanas com segunda-feira posterior ao desligamento não são elegíveis.", size=9.4)
    set_paragraph_spacing(eligibility, 7, 12, 1.08)

    clear_paragraph(validation)
    add_segment(validation, "Validação e ciência", size=15, bold=True)
    validation.paragraph_format.keep_with_next = True
    set_paragraph_spacing(validation, 6, 16, 1.0)

    signature_table = tables[3]
    signature_texts = [
        ["_______________________________\nSUP. ROBSON\nResponsável pelo Corte", "_______________________________\nSUP. GABRIEL\nResponsável pelo Estoque de Tecido"],
        ["_______________________________\nSUP. YOHANN\nResponsável pelo Estoque de Peças Prontas", "_______________________________\nCIÊNCIA DO COLABORADOR\nAssinatura do funcionário"],
    ]
    for row_index, row in enumerate(signature_table.rows):
        for col_index, cell in enumerate(row.cells):
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            lines = signature_texts[row_index][col_index].split("\n")
            for line_index, line in enumerate(lines):
                add_segment(paragraph, line, size=9.2, bold=line_index > 0)
                if line_index < len(lines) - 1:
                    add_line_break(paragraph)
            set_paragraph_spacing(paragraph, 0, 0, 1.05)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.BOTTOM
            set_cell_margins(cell, top=180, start=120, bottom=180, end=120)
    signature_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    signature_table.autofit = False
    for row in signature_table.rows:
        prevent_row_split(row)
        for cell in row.cells:
            cell.width = Inches(3.25)
    # Remove visible borders from the signature layout.
    tbl_pr = signature_table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "nil")

    # Apply Portuguese language metadata to all runs for spellcheck behavior.
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            r_pr = run._element.get_or_add_rPr()
            lang = r_pr.find(qn("w:lang"))
            if lang is None:
                lang = OxmlElement("w:lang")
                r_pr.append(lang)
            lang.set(qn("w:val"), "pt-BR")
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        r_pr = run._element.get_or_add_rPr()
                        lang = r_pr.find(qn("w:lang"))
                        if lang is None:
                            lang = OxmlElement("w:lang")
                            r_pr.append(lang)
                        lang.set(qn("w:val"), "pt-BR")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT))
    print(OUTPUT)


if __name__ == "__main__":
    main()
