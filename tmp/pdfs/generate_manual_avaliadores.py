from __future__ import annotations

from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(r"C:\Users\yohan\Desktop\Python\avaliacao")
OUT = ROOT / "output" / "pdf" / "manual_avaliacao_avaliadores.pdf"
LOGO = ROOT / "assets" / "logo.png"

PAGE_W, PAGE_H = A4
MARGIN_X = 17 * mm
MARGIN_TOP = 22 * mm
MARGIN_BOTTOM = 17 * mm

NAVY = colors.HexColor("#0B182A")
INK = colors.HexColor("#12263A")
BLUE = colors.HexColor("#347DA5")
GREEN = colors.HexColor("#177864")
AMBER = colors.HexColor("#CB8A19")
RED = colors.HexColor("#B04557")
BG = colors.HexColor("#EDF3F7")
SURFACE = colors.HexColor("#F9FCFF")
LINE = colors.HexColor("#D6E1E8")
MUTED = colors.HexColor("#5F7182")
PALE_BLUE = colors.HexColor("#E8F3F8")
PALE_GREEN = colors.HexColor("#E8F4F0")
PALE_AMBER = colors.HexColor("#FFF4DE")
PALE_RED = colors.HexColor("#FBECEF")


def register_fonts() -> None:
    candidates = {
        "UISans": Path(r"C:\Windows\Fonts\segoeui.ttf"),
        "UISans-Semibold": Path(r"C:\Windows\Fonts\seguisb.ttf"),
        "UISans-Bold": Path(r"C:\Windows\Fonts\segoeuib.ttf"),
        "UISans-Italic": Path(r"C:\Windows\Fonts\segoeuii.ttf"),
    }
    for name, path in candidates.items():
        if not path.exists():
            raise FileNotFoundError(f"Fonte obrigatoria nao encontrada: {path}")
        pdfmetrics.registerFont(TTFont(name, str(path)))


register_fonts()

BASE = getSampleStyleSheet()
STYLES = {
    "body": ParagraphStyle(
        "body",
        parent=BASE["BodyText"],
        fontName="UISans",
        fontSize=9.2,
        leading=13.2,
        textColor=INK,
        spaceAfter=5,
    ),
    "small": ParagraphStyle(
        "small",
        parent=BASE["BodyText"],
        fontName="UISans",
        fontSize=7.4,
        leading=10.2,
        textColor=MUTED,
    ),
    "tiny": ParagraphStyle(
        "tiny",
        parent=BASE["BodyText"],
        fontName="UISans",
        fontSize=6.5,
        leading=8.5,
        textColor=INK,
    ),
    "h1": ParagraphStyle(
        "h1",
        parent=BASE["Heading1"],
        fontName="UISans-Bold",
        fontSize=22,
        leading=25,
        textColor=NAVY,
        spaceAfter=8,
    ),
    "h2": ParagraphStyle(
        "h2",
        parent=BASE["Heading2"],
        fontName="UISans-Bold",
        fontSize=15,
        leading=18,
        textColor=NAVY,
        spaceBefore=5,
        spaceAfter=7,
    ),
    "h3": ParagraphStyle(
        "h3",
        parent=BASE["Heading3"],
        fontName="UISans-Semibold",
        fontSize=10.5,
        leading=13,
        textColor=INK,
        spaceBefore=4,
        spaceAfter=4,
    ),
    "eyebrow": ParagraphStyle(
        "eyebrow",
        parent=BASE["BodyText"],
        fontName="UISans-Bold",
        fontSize=7,
        leading=9,
        tracking=1.2,
        textColor=BLUE,
        spaceAfter=5,
    ),
    "white_body": ParagraphStyle(
        "white_body",
        parent=BASE["BodyText"],
        fontName="UISans",
        fontSize=10,
        leading=14,
        textColor=colors.white,
    ),
    "cover_title": ParagraphStyle(
        "cover_title",
        parent=BASE["Title"],
        fontName="UISans-Bold",
        fontSize=32,
        leading=34,
        textColor=colors.white,
        alignment=TA_LEFT,
        spaceAfter=8,
    ),
    "cover_kicker": ParagraphStyle(
        "cover_kicker",
        parent=BASE["BodyText"],
        fontName="UISans-Bold",
        fontSize=8,
        leading=10,
        tracking=1.4,
        textColor=colors.HexColor("#A9D8EA"),
        spaceAfter=7,
    ),
    "cover_meta": ParagraphStyle(
        "cover_meta",
        parent=BASE["BodyText"],
        fontName="UISans-Semibold",
        fontSize=8.5,
        leading=12,
        textColor=colors.white,
    ),
    "quote": ParagraphStyle(
        "quote",
        parent=BASE["BodyText"],
        fontName="UISans-Semibold",
        fontSize=11.5,
        leading=16,
        textColor=NAVY,
        leftIndent=9,
        borderColor=BLUE,
        borderWidth=0,
        borderPadding=0,
    ),
    "table_head": ParagraphStyle(
        "table_head",
        parent=BASE["BodyText"],
        fontName="UISans-Bold",
        fontSize=7.2,
        leading=9.1,
        textColor=colors.white,
        alignment=TA_LEFT,
    ),
    "table": ParagraphStyle(
        "table",
        parent=BASE["BodyText"],
        fontName="UISans",
        fontSize=7.3,
        leading=9.6,
        textColor=INK,
    ),
    "table_strong": ParagraphStyle(
        "table_strong",
        parent=BASE["BodyText"],
        fontName="UISans-Semibold",
        fontSize=7.3,
        leading=9.6,
        textColor=INK,
    ),
    "number": ParagraphStyle(
        "number",
        parent=BASE["BodyText"],
        fontName="UISans-Bold",
        fontSize=18,
        leading=19,
        textColor=BLUE,
        alignment=TA_CENTER,
    ),
    "center_small": ParagraphStyle(
        "center_small",
        parent=BASE["BodyText"],
        fontName="UISans",
        fontSize=7.5,
        leading=10,
        textColor=MUTED,
        alignment=TA_CENTER,
    ),
}


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def bullet(text: str, color: colors.Color = BLUE) -> Table:
    dot = Table([[""]], colWidths=[3.2 * mm], rowHeights=[3.2 * mm])
    dot.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("BOX", (0, 0), (-1, -1), 0, color),
    ]))
    table = Table([[dot, P(text)]], colWidths=[5.5 * mm, 158 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def section_header(kicker: str, title: str, intro: str | None = None) -> list:
    items = [P(kicker.upper(), "eyebrow"), P(title, "h1")]
    if intro:
        items.append(P(intro))
        items.append(Spacer(1, 2 * mm))
    return items


def callout(title: str, body: str, tone: str = "blue", width: float = 164 * mm) -> Table:
    palette = {
        "blue": (PALE_BLUE, BLUE),
        "green": (PALE_GREEN, GREEN),
        "amber": (PALE_AMBER, AMBER),
        "red": (PALE_RED, RED),
        "navy": (colors.HexColor("#E7ECF2"), NAVY),
    }
    bg, accent = palette[tone]
    data = [[P(title, "h3")], [P(body, "body")]]
    table = Table(data, colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.Color(accent.red, accent.green, accent.blue, alpha=0.28)),
        ("LINEBEFORE", (0, 0), (0, -1), 4, accent),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (0, 0), 7),
        ("BOTTOMPADDING", (0, 0), (0, 0), 1),
        ("TOPPADDING", (0, 1), (0, 1), 1),
        ("BOTTOMPADDING", (0, 1), (0, 1), 7),
    ]))
    return table


def card(title: str, body: str, width: float, tone: str = "blue") -> Table:
    palette = {
        "blue": (PALE_BLUE, BLUE),
        "green": (PALE_GREEN, GREEN),
        "amber": (PALE_AMBER, AMBER),
        "red": (PALE_RED, RED),
        "white": (SURFACE, NAVY),
    }
    bg, accent = palette[tone]
    table = Table([[P(title, "h3")], [P(body, "small")]], colWidths=[width], rowHeights=[None, None])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LINEABOVE", (0, 0), (-1, 0), 3.5, accent),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def cards(rows: list[list[tuple[str, str, str]]], widths: list[float] | None = None) -> Table:
    count = max(len(row) for row in rows)
    widths = widths or [164 * mm / count] * count
    data = []
    for row in rows:
        data.append([card(title, body, widths[i] - 3 * mm, tone) for i, (title, body, tone) in enumerate(row)])
    table = Table(data, colWidths=widths, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    return table


def data_table(
    headers: list[str],
    rows: Iterable[Iterable[str]],
    widths: list[float],
    *,
    header_color: colors.Color = NAVY,
    font_size: float | None = None,
    repeat_rows: int = 1,
) -> Table:
    head = [P(value, "table_head") for value in headers]
    body = []
    for row in rows:
        body.append([P(str(value), "table") for value in row])
    table = Table([head, *body], colWidths=widths, repeatRows=repeat_rows, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F8FA")]),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if font_size:
        style.extend([
            ("FONTSIZE", (0, 1), (-1, -1), font_size),
            ("LEADING", (0, 1), (-1, -1), font_size + 2),
        ])
    table.setStyle(TableStyle(style))
    return table


def step_row(number: str, title: str, body: str, accent: colors.Color = BLUE) -> Table:
    number_cell = Table([[P(number, "number")]], colWidths=[13 * mm], rowHeights=[13 * mm])
    number_cell.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, accent),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    table = Table([[number_cell, [P(title, "h3"), P(body, "small")]]], colWidths=[18 * mm, 146 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def on_page(canvas, doc) -> None:
    page = canvas.getPageNumber()
    if page == 1:
        return
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, PAGE_H - 12 * mm, PAGE_W, 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(NAVY)
    canvas.setFont("UISans-Semibold", 7.3)
    canvas.drawString(MARGIN_X, PAGE_H - 8.2 * mm, "KAISAN  |  MANUAL DE AVALIACAO")
    canvas.setFillColor(BLUE)
    canvas.rect(PAGE_W - MARGIN_X - 21 * mm, PAGE_H - 9.2 * mm, 21 * mm, 2.2 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_X, 12 * mm, PAGE_W - MARGIN_X, 12 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("UISans", 7)
    canvas.drawString(MARGIN_X, 8 * mm, "Uso interno  |  Versao 1.0  |  28/09/2026")
    canvas.drawRightString(PAGE_W - MARGIN_X, 8 * mm, f"Pagina {page}")
    canvas.restoreState()


class ManualDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=MARGIN_X,
            rightMargin=MARGIN_X,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="Manual de Avaliacao - Guia para Avaliadores",
            author="KAISAN",
            subject="Criterios, ocorrencias, evidencias e boas praticas de avaliacao",
            creator="Avaliacao & Bonificacao",
        )
        frame = Frame(
            MARGIN_X,
            MARGIN_BOTTOM,
            PAGE_W - 2 * MARGIN_X,
            PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
            id="normal",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates([PageTemplate(id="manual", frames=[frame], onPage=on_page)])


def cover_story() -> list:
    story = [Spacer(1, 7 * mm)]
    if LOGO.exists():
        logo = Image(str(LOGO), width=36 * mm, height=36 * mm)
        logo.hAlign = "LEFT"
        story.append(logo)
    story.extend([
        Spacer(1, 12 * mm),
        P("AVALIACAO &amp; BONIFICACAO", "cover_kicker"),
        P("Manual de<br/>Avaliação", "cover_title"),
        P("Guia para avaliadores", "white_body"),
        Spacer(1, 11 * mm),
        Table(
            [[P("CRITERIOS", "cover_meta"), P("EVIDENCIAS", "cover_meta"), P("OCORRENCIAS", "cover_meta")]],
            colWidths=[50 * mm, 50 * mm, 50 * mm],
            style=TableStyle([
                ("LINEABOVE", (0, 0), (-1, 0), 0.7, colors.HexColor("#64849B")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]),
        ),
        Spacer(1, 31 * mm),
        P("Objetivo", "cover_kicker"),
        P(
            "Apoiar avaliações semanais justas, consistentes e auditáveis, com critérios comuns para toda a operação. Este documento orienta o julgamento do avaliador; não é um passo a passo da plataforma.",
            "white_body",
        ),
        Spacer(1, 16 * mm),
        P("USO INTERNO  |  VERSAO 1.0  |  SETEMBRO DE 2026", "cover_meta"),
    ])
    return story


def draw_cover_background(canvas, doc) -> None:
    if canvas.getPageNumber() != 1:
        return
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(BLUE)
    canvas.rect(0, 0, 13 * mm, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(GREEN)
    canvas.rect(13 * mm, PAGE_H - 11 * mm, PAGE_W - 13 * mm, 11 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#102841"))
    canvas.circle(PAGE_W - 22 * mm, 48 * mm, 43 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#173B55"))
    canvas.circle(PAGE_W - 10 * mm, 25 * mm, 26 * mm, fill=1, stroke=0)
    canvas.restoreState()


def build_story() -> list:
    s: list = []
    s.extend(cover_story())
    s.append(PageBreak())

    s.extend(section_header(
        "01 | Fundamentos",
        "Como usar este manual",
        "A avaliação transforma fatos do período em uma decisão explicável. O avaliador deve conseguir responder: o que aconteceu, qual critério foi afetado, qual evidência sustenta a nota e qual orientação foi dada ao colaborador.",
    ))
    s.append(callout(
        "Regra de ouro",
        "Avalie a entrega observável, não a pessoa. Notas e ocorrências devem se apoiar em fatos do período, aplicar o mesmo padrão a funções comparáveis e permitir revisão posterior.",
        "blue",
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(P("Princípios obrigatórios", "h2"))
    s.append(cards([
        [
            ("Imparcialidade", "Use o mesmo critério para situações equivalentes. Afinidade, antiguidade, popularidade ou impressão pessoal não são evidências.", "blue"),
            ("Rastreabilidade", "Registre data, fato, impacto e fonte. Uma terceira pessoa deve compreender a decisão sem depender da memória do avaliador.", "green"),
        ],
        [
            ("Proporcionalidade", "A nota deve refletir frequência, gravidade e impacto. Um episódio isolado não deve ser tratado como padrão recorrente sem base factual.", "amber"),
            ("Respeito", "Descreva condutas e resultados, sem rótulos. Preserve dados pessoais e nunca registre diagnóstico ou detalhe médico desnecessário.", "white"),
        ],
    ], widths=[82 * mm, 82 * mm]))
    s.append(P("Responsabilidades", "h2"))
    s.append(data_table(
        ["Papel", "Responsabilidade principal", "Limite de decisão"],
        [
            ["Avaliador", "Reunir evidências, atribuir notas, justificar desvios, classificar ocorrências e dar feedback.", "Não criar punições, exceções ou códigos fora da diretriz vigente."],
            ["Liderança / administração", "Calibrar casos, resolver divergências, revisar pendências e autorizar correções relevantes.", "Não alterar fatos para atingir orçamento, média ou distribuição desejada."],
            ["RH / gestão responsável", "Receber o fechamento, tratar medidas formais e assegurar aderência às políticas internas.", "Medidas disciplinares seguem o processo interno; a avaliação não substitui esse processo."],
            ["Colaborador", "Conhecer o resultado, oferecer contexto e assumir ações acordadas.", "A manifestação do colaborador não apaga evidência válida, mas deve ser considerada na revisão."],
        ],
        [28 * mm, 71 * mm, 65 * mm],
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(callout(
        "Separação essencial",
        "A nota posiciona o desempenho na faixa. A ocorrência aplica o desconto corporativo depois da faixa. Não rebaixe arbitrariamente a nota apenas para duplicar o efeito financeiro de uma ocorrência já registrada.",
        "amber",
    ))
    s.append(PageBreak())

    s.extend(section_header(
        "02 | Estrutura vigente",
        "O que compõe a avaliação",
        "A operação usa quatro semanas fixas por competência. Cada semana tem cinco critérios. O valor máximo mensal do bônus-base é R$ 550,00; o máximo semanal é R$ 137,50.",
    ))
    s.append(data_table(
        ["Critério", "O que representa", "Máximo mensal", "Máximo semanal"],
        [
            ["Assiduidade", "Presença, pontualidade e regularidade.", "R$ 150,00", "R$ 37,50"],
            ["Qualidade", "Conformidade, cuidado e padrão de execução.", "R$ 100,00", "R$ 25,00"],
            ["Taxa de erros", "Frequência e gravidade das falhas registradas.", "R$ 100,00", "R$ 25,00"],
            ["Produtividade", "Volume, ritmo e eficiência compatíveis com a função.", "R$ 100,00", "R$ 25,00"],
            ["Comportamento", "Conduta profissional e aderência às normas.", "R$ 100,00", "R$ 25,00"],
            ["TOTAL BASE", "Soma dos cinco critérios.", "R$ 550,00", "R$ 137,50"],
        ],
        [35 * mm, 69 * mm, 30 * mm, 30 * mm],
        header_color=BLUE,
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(P("Composição do valor final", "h2"))
    s.append(cards([[ 
        ("1. Bônus-base", "Resultado das quatro avaliações semanais, após faixas e ocorrências.", "blue"),
        ("2. Monitoria", "R$ 300,00 fixos para monitor ativo e elegível. Não existe avaliação mensal de monitoria na regra atual.", "green"),
        ("3. Tempo de casa", "R$ 30,00 por ano completo, calculado na data de referência do fechamento.", "white"),
    ]], widths=[54.7 * mm, 54.7 * mm, 54.6 * mm]))
    s.append(P("Elegibilidade do período", "h2"))
    for text in [
        "A competência reúne as quatro últimas semanas cuja sexta-feira pertence ao mês ou cai até o dia 25; sextas-feiras após o dia 25 são atribuídas ao mês seguinte.",
        "A semana de contratação não conta. O colaborador entra apenas em semana posterior à semana em que foi admitido.",
        "A semana permanece elegível quando a segunda-feira é igual ou anterior à data de desligamento; semanas posteriores não entram.",
        "Coordenação e supervisão elegíveis aparecem em grupo separado, recebem base mensal de R$ 550,00 e não recebem avaliação semanal.",
        "O adicional de monitor exige marcação ativa, data de início e ao menos uma semana elegível posterior à semana de início. Liderança não acumula monitoria.",
    ]:
        s.append(bullet(text))
    s.append(callout(
        "Sem discricionariedade",
        "Elegibilidade, adicional de monitor, base de liderança e tempo de casa são regras de cálculo. O avaliador não deve compensá-las aumentando ou reduzindo notas.",
        "navy",
    ))
    s.append(PageBreak())

    s.extend(section_header(
        "03 | Julgamento",
        "Escala de notas e faixas de pagamento",
        "A nota é contínua de 0% a 100%, mas o pagamento ocorre por faixas. Pequenas diferenças próximas aos limites podem mudar o valor pago; por isso, a justificativa precisa ser especialmente clara nesses casos.",
    ))
    band_rows = [
        ["91% a 100%", "100%", "Atende ao esperado com consistência. Desvios, se houver, são isolados e sem impacto relevante."],
        ["Acima de 80% até 90%", "75%", "Atende em grande parte, com pontos de ajuste objetivos e impacto limitado."],
        ["Acima de 70% até 80%", "50%", "Entrega parcial ou instável; há desvios claros que exigem acompanhamento."],
        ["Acima de 50% até 70%", "25%", "Resultado significativamente abaixo do esperado, com impacto ou recorrência material."],
        ["0% a 50%", "0%", "Resultado insuficiente ou falha grave no critério durante o período."],
    ]
    s.append(data_table(
        ["Nota do critério", "Parcela paga", "Referência recomendada para o julgamento"],
        band_rows,
        [37 * mm, 30 * mm, 97 * mm],
        header_color=NAVY,
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(callout(
        "Atenção aos limites",
        "50% ainda paga 0%; 70% paga 25%; 80% paga 50%; 90% paga 75%. A faixa integral começa somente acima de 90%. Não use 90% como sinônimo de desempenho integral.",
        "red",
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(P("Método de decisão em quatro perguntas", "h2"))
    s.append(step_row("1", "Qual era o padrão esperado?", "Considere função, setor, meta comunicada, escala e condições conhecidas do período."))
    s.append(step_row("2", "Quais fatos foram observados?", "Use registros, indicadores, entregas, ocorrências, controles de jornada e observação direta verificável."))
    s.append(step_row("3", "Qual foi a frequência e o impacto?", "Diferencie evento isolado de recorrência e impacto leve de impacto operacional, financeiro, de cliente ou de segurança."))
    s.append(step_row("4", "A faixa escolhida é defensável?", "Compare com casos semelhantes e escreva uma justificativa que conecte fato, impacto e expectativa."))
    s.append(P("O que não fazer", "h2"))
    s.append(cards([[ 
        ("Média por simpatia", "Não arredonde a nota para favorecer ou prejudicar alguém.", "red"),
        ("Quota de notas", "Não force uma distribuição de pessoas entre faixas.", "amber"),
        ("Compensação cruzada", "Bom comportamento não apaga erro de qualidade; cada critério é independente.", "white"),
    ]], widths=[54.7 * mm, 54.7 * mm, 54.6 * mm]))
    s.append(PageBreak())

    s.extend(section_header(
        "04 | Critério 1",
        "Assiduidade",
        "Mede presença, pontualidade e regularidade no cumprimento da jornada. Ausências e atrasos devem seguir os códigos A01 a A08; a nota não substitui o registro formal da ocorrência.",
    ))
    s.append(cards([[ 
        ("Observe", "Presença no período; horários de entrada e saída; retorno de intervalos; regularidade; comunicação e registro conforme a política interna.", "blue"),
        ("Evidências adequadas", "Espelho de ponto, escala, justificativa formal, registro de liderança, autorização de saída e documento exigido pela política.", "green"),
    ]], widths=[82 * mm, 82 * mm]))
    s.append(P("Critérios de julgamento", "h2"))
    s.append(data_table(
        ["Situação", "Interpretação", "Conduta do avaliador"],
        [
            ["Sem desvio relevante", "Jornada cumprida conforme o esperado.", "Mantenha nota coerente com a entrega e confirme ausência de ocorrência."],
            ["Atraso ou saída", "Impacto depende do horário, duração e código aplicável.", "Registre o código correto, quantidade e contexto objetivo."],
            ["Ausência", "Atestado, declaração e falta sem atestado possuem regras distintas.", "Não improvise equivalência; use A01 a A06 conforme o fato documentado."],
            ["Reincidência", "A repetição pode acumular descontos; A01 repetida bloqueia o bônus-base mensal.", "Cheque o histórico da competência antes do fechamento."],
        ],
        [36 * mm, 61 * mm, 67 * mm],
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(callout(
        "Privacidade em saúde",
        "Para atestados e declarações, registre somente o necessário para classificar a ocorrência e comprovar o período. Não inclua diagnóstico, CID, detalhes clínicos ou comentários sobre a condição de saúde no campo de avaliação.",
        "amber",
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(P("Exemplos de justificativa", "h2"))
    s.append(data_table(
        ["Evite", "Prefira"],
        [
            ["\"É descomprometido e vive atrasando.\"", "\"Na semana de 14/09, houve entrada após 7h30 em 16/09, registrada como A08. Reforçado o horário previsto para a próxima semana.\""],
            ["\"Faltou muito.\"", "\"Foram registradas 2 ocorrências A02, nos dias 15 e 17/09, conforme documentos recebidos. A reincidência aplica o desconto previsto.\""],
        ],
        [69 * mm, 95 * mm],
        header_color=RED,
    ))
    s.append(PageBreak())

    s.extend(section_header(
        "05 | Critérios 2 e 3",
        "Qualidade e taxa de erros",
        "Os dois critérios são relacionados, mas não idênticos. Qualidade avalia o padrão geral da execução; taxa de erros mede a ocorrência objetiva de falhas. Os códigos Q01 a Q04 afetam financeiramente ambos.",
    ))
    s.append(data_table(
        ["Critério", "Pergunta central", "Exemplos de evidência", "Não confundir com"],
        [
            ["Qualidade", "O trabalho foi executado conforme o padrão, com cuidado e baixa necessidade de correção?", "Retrabalho, divergência, avaria, conferência, aderência ao procedimento, devolução.", "Ritmo de produção ou traço de personalidade."],
            ["Taxa de erros", "Quantas falhas ocorreram, com qual gravidade e em quantas oportunidades?", "Códigos Q, quantidade, itens processados, registros de pedido, auditoria e impacto.", "Impressão genérica de que o trabalho \"parece ruim\"."],
        ],
        [29 * mm, 50 * mm, 54 * mm, 31 * mm],
        header_color=BLUE,
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(P("Como interpretar", "h2"))
    for text in [
        "Considere a gravidade antes da quantidade: uma falha crítica pode superar várias falhas leves em impacto.",
        "Use o volume de itens como contexto, não como desculpa automática. Compare funções e condições semelhantes.",
        "Verifique se a falha é atribuível ao trabalho do colaborador. Problema sistêmico, falta de insumo, cadastro incorreto ou instrução conflitante devem ser separados.",
        "Quando a mesma falha gerar o código Q, registre a ocorrência e mantenha a nota baseada no desempenho global do critério. Evite desconto manual duplicado sem evidência adicional.",
        "Elogios também precisam ser específicos: baixa reincidência, conferência consistente, identificação preventiva de divergência ou redução de retrabalho.",
    ]:
        s.append(bullet(text))
    s.append(P("Matriz de impacto", "h2"))
    s.append(data_table(
        ["Nível", "Sinal típico", "Leitura recomendada"],
        [
            ["Baixo", "Desvio pontual, corrigido rapidamente, sem efeito relevante.", "Q04 quando enquadrado pela diretriz; documente o fato e a correção."],
            ["Médio", "Retrabalho ou impacto perceptível, sem interrupção grave.", "Q03; verifique recorrência e necessidade de acompanhamento."],
            ["Alto", "Impacto operacional importante, perda, atraso ou risco elevado.", "Q02; descreva consequência e ação de contenção."],
            ["Crítico", "Falha de maior severidade, com impacto expressivo.", "Q01; exige revisão da liderança e perde 100% de Qualidade e Taxa de erros na semana."],
        ],
        [24 * mm, 72 * mm, 68 * mm],
    ))
    s.append(callout(
        "Teste de atribuição",
        "Antes de penalizar, pergunte: o padrão estava claro? havia recurso e tempo razoáveis? o fato foi confirmado? a causa estava sob controle do colaborador? Se a resposta for não, registre o contexto e leve o caso para calibração.",
        "navy",
    ))
    s.append(PageBreak())

    s.extend(section_header(
        "06 | Critérios 4 e 5",
        "Produtividade e comportamento",
        "Produtividade trata do resultado operacional; comportamento trata da forma profissional de trabalhar. Alto volume não compensa descumprimento de segurança, e boa postura não substitui a entrega esperada.",
    ))
    s.append(P("Produtividade", "h2"))
    s.append(cards([[ 
        ("Observe", "Volume e ritmo; aderência à meta; consistência; aproveitamento do tempo; eficiência dentro do padrão de qualidade e segurança.", "blue"),
        ("Contextualize", "Função, mix de tarefas, complexidade, paradas, indisponibilidade sistêmica, treinamento, apoio recebido e jornada efetiva.", "green"),
        ("Evidencie", "Itens executados, meta comunicada, relatório de produção, registro de parada e comparação com período ou grupo equivalente.", "white"),
    ]], widths=[54.7 * mm, 54.7 * mm, 54.6 * mm]))
    s.append(callout(
        "Produtividade segura",
        "Nunca incentive velocidade à custa de qualidade, segurança, ergonomia ou procedimento. Resultado obtido por atalho indevido não deve ser tratado como desempenho superior.",
        "amber",
    ))
    s.append(Spacer(1, 4 * mm))
    s.append(P("Comportamento", "h2"))
    s.append(data_table(
        ["Observe", "Evidência aceitável", "Evite avaliar"],
        [
            ["Cumprimento de normas e orientações", "Fato, data, orientação dada e resposta observada.", "Concordância pessoal com o avaliador."],
            ["Colaboração e comunicação operacional", "Passagem de informação, apoio, respeito e coordenação em atividade real.", "Extroversão, estilo social ou amizade."],
            ["Cuidado com pessoas, materiais e ambiente", "Registro de conduta, quase acidente, dano evitado ou descumprimento confirmado.", "Boato, impressão ou comentário sem fonte."],
            ["Abertura a feedback e correção", "Mudança observável após orientação e reincidência documentada.", "Questionamento respeitoso ou pedido legítimo de esclarecimento."],
        ],
        [54 * mm, 65 * mm, 45 * mm],
        header_color=GREEN,
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(P("Exemplos objetivos", "h2"))
    s.append(data_table(
        ["Frase fraca", "Frase auditável"],
        [
            ["\"Não tem iniciativa.\"", "\"Em 3 separações com divergência, aguardou nova orientação após o procedimento já ter sido reforçado em 08/09; houve atraso de 25 minutos no fluxo.\""],
            ["\"É excelente com a equipe.\"", "\"Durante a ausência do responsável em 18/09, redistribuiu as tarefas conforme orientação e comunicou duas pendências antes do corte.\""],
        ],
        [60 * mm, 104 * mm],
        header_color=NAVY,
    ))
    s.append(PageBreak())

    s.extend(section_header(
        "07 | Ocorrências",
        "Como aplicar os códigos",
        "O catálogo corporativo possui 20 códigos. Pontos representam a referência máxima de desconto; o cálculo respeita o valor disponível em cada critério e acumula incidências até o limite aplicável.",
    ))
    s.append(cards([[ 
        ("Classifique", "Escolha categoria e código pelo fato comprovado, não pelo valor financeiro desejado.", "blue"),
        ("Quantifique", "Informe a quantidade real. Lançamentos repetidos acumulam efeitos, limitados ao bônus disponível.", "amber"),
        ("Contextualize", "Registre data, situação, fonte e consequência. Não replique dados pessoais desnecessários.", "green"),
    ]], widths=[54.7 * mm, 54.7 * mm, 54.6 * mm]))
    s.append(P("Regras de incidência", "h2"))
    for text in [
        "Primeiro calcula-se a faixa de pagamento da nota; depois são aplicados os descontos das ocorrências.",
        "Se o valor disponível no critério for menor que o desconto de referência, o desconto é limitado ao saldo disponível.",
        "Ocorrências no mesmo critério se acumulam até zerar a verba daquele critério.",
        "Registros legados sem código A, Q, P ou C permanecem para auditoria, mas não geram desconto automático.",
        "C01 informa que cabe carta de advertência; a emissão da medida formal deve seguir a autoridade e o processo interno, fora da decisão isolada do avaliador.",
    ]:
        s.append(bullet(text))
    s.append(Spacer(1, 3 * mm))
    s.append(callout(
        "Dois controles diferentes",
        "Gravidade descreve a natureza do fato. Pontos e percentuais definem o efeito financeiro. Não altere a gravidade para tentar aproximar um desconto; selecione o código correto e deixe o cálculo aplicar a regra.",
        "navy",
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(P("Assiduidade - códigos A01 a A08", "h2"))
    a_rows = [
        ["A01", "Falta sem atestado", "ALTO", "250", "-100% da assiduidade mensal e -100% dos outros critérios na semana. A 2ª A01 bloqueia todo o bônus-base mensal."],
        ["A02", "Falta com atestado", "BAIXO", "47,5", "-100% da assiduidade semanal e -20% por dia nos demais critérios; reincidência repete o desconto."],
        ["A03", "Declaração de até 50% da carga", "BAIXO", "87,5", "-100% da assiduidade semanal e -50% dos demais critérios."],
        ["A04", "Declaração acima de 50% da carga", "ALTO", "137,5", "-100% de todos os critérios da semana."],
        ["A05", "Saída por poucas horas", "BAIXO", "37,5", "-100% da assiduidade semanal."],
        ["A06", "Saída superior a 50% do dia", "ALTO", "125", "Meia falta: -50% da assiduidade mensal e -50% dos demais critérios na semana."],
        ["A07", "Atraso até 7h30", "BAIXO", "9,37", "-25% da assiduidade semanal."],
        ["A08", "Atraso depois de 7h30", "ALTO", "37,5", "-100% da assiduidade semanal."],
    ]
    s.append(data_table(
        ["Código", "Ocorrência", "Nível", "Pontos", "Efeito vigente"],
        a_rows,
        [15 * mm, 43 * mm, 18 * mm, 17 * mm, 71 * mm],
        header_color=AMBER,
        font_size=6.8,
    ))
    s.append(PageBreak())

    s.extend(section_header(
        "07 | Ocorrências",
        "Qualidade, produtividade e comportamento",
        "Use os níveis baixo, médio, alto e crítico de forma consistente. A classificação deve refletir consequência, risco, reversibilidade e recorrência, conforme a diretriz corporativa.",
    ))
    qpc_rows = [
        ["Q01", "Qualidade", "Crítico", "50", "-100% de Qualidade e Taxa de erros na semana."],
        ["Q02", "Qualidade", "Alto", "25", "-50% de Qualidade e Taxa de erros na semana."],
        ["Q03", "Qualidade", "Médio", "12,5", "-25% de Qualidade e Taxa de erros na semana."],
        ["Q04", "Qualidade", "Baixo", "5", "-10% de Qualidade e Taxa de erros na semana."],
        ["P01", "Produtividade", "Crítico", "25", "-100% de Produtividade na semana."],
        ["P02", "Produtividade", "Alto", "12,5", "-50% de Produtividade na semana."],
        ["P03", "Produtividade", "Médio", "6,3", "-25% de Produtividade na semana."],
        ["P04", "Produtividade", "Baixo", "2,5", "-10% de Produtividade na semana."],
        ["C01", "Comportamento", "Crítico", "25", "-100% de Comportamento na semana; cabe carta de advertência."],
        ["C02", "Comportamento", "Alto", "12,5", "-50% de Comportamento na semana."],
        ["C03", "Comportamento", "Médio", "6,3", "-25% de Comportamento na semana."],
        ["C04", "Comportamento", "Baixo", "2,5", "-10% de Comportamento na semana."],
    ]
    s.append(data_table(
        ["Código", "Categoria", "Nível", "Pontos", "Efeito vigente"],
        qpc_rows,
        [17 * mm, 34 * mm, 23 * mm, 20 * mm, 70 * mm],
        header_color=NAVY,
    ))
    s.append(Spacer(1, 6 * mm))
    s.append(P("Perguntas para calibrar a gravidade", "h2"))
    s.append(cards([
        [
            ("Impacto", "Houve retrabalho, atraso, perda, risco, reclamação ou interrupção? Qual a magnitude?", "blue"),
            ("Reversibilidade", "O fato foi corrigido imediatamente ou produziu consequência difícil de reverter?", "green"),
        ],
        [
            ("Recorrência", "É um caso isolado ou repetido após orientação clara e oportunidade de correção?", "amber"),
            ("Controle", "O colaborador tinha informação, recurso, treinamento e autonomia para evitar o fato?", "white"),
        ],
    ], widths=[82 * mm, 82 * mm]))
    s.append(callout(
        "Quando houver dúvida",
        "Não escolha o código mais grave por precaução. Preserve os fatos, peça revisão da liderança e calibre com um caso comparável antes do fechamento.",
        "red",
    ))
    s.append(PageBreak())

    s.extend(section_header(
        "08 | Registro",
        "Justificativas que sustentam a decisão",
        "Toda nota abaixo de 100% exige justificativa. Uma boa justificativa é curta, específica e útil para feedback; ela explica a decisão sem atacar a pessoa.",
    ))
    s.append(P("Modelo F.I.E.A.", "h2"))
    s.append(cards([[ 
        ("Fato", "O que aconteceu, quando e em qual atividade?", "blue"),
        ("Impacto", "Qual foi a consequência observável?", "amber"),
        ("Expectativa", "Qual padrão ou comportamento era esperado?", "green"),
        ("Ação", "O que foi orientado e como será acompanhado?", "white"),
    ]], widths=[41 * mm, 41 * mm, 41 * mm, 41 * mm]))
    s.append(Spacer(1, 3 * mm))
    s.append(callout(
        "Exemplo completo",
        "Em 17/09, duas separações foram concluídas sem a conferência final, gerando retrabalho de 30 minutos (fato e impacto). O procedimento exige conferência antes da liberação (expectativa). O processo foi revisto com o colaborador e será acompanhado nas próximas duas semanas (ação).",
        "blue",
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(P("Padrão mínimo por tipo de registro", "h2"))
    s.append(data_table(
        ["Registro", "Inclua", "Não inclua"],
        [
            ["Nota abaixo de 100%", "Fato, período, impacto, referência esperada e ação.", "Rótulo, ironia, ameaça ou opinião sem exemplo."],
            ["Ocorrência", "Código, quantidade, data/situação, evidência e consequência.", "Detalhe pessoal sem relação com a classificação."],
            ["Observação geral", "Contexto transversal que ajuda a compreender a semana.", "Resumo que contradiga as justificativas dos critérios."],
            ["Reconhecimento", "Entrega específica, resultado e comportamento a manter.", "Elogio genérico sem indicar o que deve ser repetido."],
        ],
        [35 * mm, 68 * mm, 61 * mm],
    ))
    s.append(Spacer(1, 6 * mm))
    s.append(P("Lista de palavras a revisar", "h2"))
    s.append(data_table(
        ["Evite", "Substitua por"],
        [
            ["sempre / nunca", "frequência observada e datas"],
            ["preguiçoso / desinteressado", "conduta ou entrega concreta"],
            ["ruim / fraco", "padrão não atingido e impacto"],
            ["todo mundo sabe", "fonte verificável"],
            ["problema pessoal", "contexto operacional relevante, com privacidade"],
        ],
        [52 * mm, 112 * mm],
        header_color=RED,
    ))
    s.append(PageBreak())

    s.extend(section_header(
        "09 | Governança",
        "Calibração, revisão e feedback",
        "Calibrar não é negociar nota. É verificar se fatos semelhantes recebem tratamento semelhante antes que o resultado seja fechado.",
    ))
    s.append(P("Roteiro de calibração", "h2"))
    s.append(step_row("1", "Compare situações equivalentes", "Mesma função, atividade, período e condição operacional sempre que possível.", GREEN))
    s.append(step_row("2", "Cheque o limite de faixa", "Dê atenção a 50, 70, 80 e 90, porque pequenas diferenças alteram o pagamento.", GREEN))
    s.append(step_row("3", "Separe nota e ocorrência", "Confirme que o código foi aplicado e que não houve desconto manual duplicado sem justificativa independente.", GREEN))
    s.append(step_row("4", "Resolva inconsistências", "Corrija fatos, quantidades, códigos, notas e textos antes do fechamento; registre o motivo da revisão.", GREEN))
    s.append(Spacer(1, 4 * mm))
    s.append(P("Casos que exigem revisão da liderança", "h2"))
    for text in [
        "Dúvida entre dois códigos ou entre níveis de gravidade.",
        "Conflito de interesse, relação direta no fato ou impossibilidade de avaliar com imparcialidade.",
        "Evidências contraditórias ou dependência de apuração externa.",
        "Nota no limite da faixa sem evidência clara que sustente a escolha.",
        "A01 reincidente, Q01, P01, C01 ou qualquer caso com impacto grave.",
        "Condições operacionais atípicas que afetaram meta, volume, sistema, equipamento ou segurança.",
    ]:
        s.append(bullet(text, AMBER))
    s.append(P("Conversa de feedback", "h2"))
    s.append(data_table(
        ["Momento", "Boa prática"],
        [
            ["Abrir", "Explique o objetivo e o período avaliado; crie espaço para contexto."],
            ["Apresentar", "Comece pelos fatos e resultados. Mostre como eles se conectam aos critérios."],
            ["Ouvir", "Permita esclarecimento e diferencie nova evidência de discordância sem base."],
            ["Acordar", "Defina uma ação específica, responsável e prazo de acompanhamento."],
            ["Fechar", "Confirme entendimento, registre eventual correção e preserve o respeito."],
        ],
        [32 * mm, 132 * mm],
        header_color=GREEN,
    ))
    s.append(callout(
        "Direito de revisão",
        "Se surgir evidência nova ou erro factual, a avaliação deve ser revisada pelo fluxo interno antes do fechamento. Discordância, por si só, não invalida uma decisão sustentada por evidência.",
        "navy",
    ))
    s.append(PageBreak())

    s.extend(section_header(
        "10 | Fechamento",
        "Checklist do avaliador",
        "Use esta verificação antes de considerar a competência pronta. O objetivo é evitar pendência, inconsistência e decisão impossível de explicar ao colaborador ou ao RH.",
    ))
    checklist = [
        ("Cobertura", "Todos os colaboradores operacionais possuem avaliação em cada semana elegível."),
        ("Período", "As semanas pertencem à competência correta e respeitam admissão e desligamento."),
        ("Liderança", "Coordenação e supervisão não receberam avaliação semanal indevida."),
        ("Notas", "Todos os percentuais estão entre 0% e 100% e refletem evidências do período."),
        ("Limites", "Notas próximas a 50, 70, 80 ou 90 possuem justificativa especialmente clara."),
        ("Justificativas", "Cada critério abaixo de 100% tem texto específico no padrão F.I.E.A."),
        ("Ocorrências", "Códigos, quantidades, gravidades e datas foram conferidos; não há duplicidade."),
        ("A01", "A reincidência na competência foi verificada e o bloqueio mensal foi compreendido."),
        ("Monitoria", "Monitores elegíveis possuem data de início válida; o adicional é fixo de R$ 300,00."),
        ("Tempo de casa", "A data de contratação está correta para o adicional de R$ 30,00 por ano completo."),
        ("Calibração", "Casos graves, atípicos e limítrofes foram revisados com a liderança."),
        ("Feedback", "O colaborador recebeu ou receberá retorno com fatos e ação de acompanhamento."),
    ]
    for index, (title, body) in enumerate(checklist, start=1):
        s.append(step_row(str(index), title, body, BLUE if index <= 6 else GREEN))
    s.append(Spacer(1, 4 * mm))
    s.append(callout(
        "Condição para fechar",
        "O fechamento deve ter 100% de cobertura das semanas elegíveis, zero pendência crítica e justificativas suficientes para sustentar cada redução e cada ocorrência.",
        "green",
    ))
    s.append(PageBreak())

    s.extend(section_header(
        "11 | Consulta rápida",
        "Uma página para a rotina",
        "Antes de atribuir uma nota, siga a sequência: padrão esperado, fato, frequência, impacto, faixa, ocorrência e justificativa.",
    ))
    s.append(data_table(
        ["Nota", "Parcela paga", "Leitura rápida"],
        [
            [">90% a 100%", "100%", "Atende com consistência"],
            [">80% a 90%", "75%", "Atende em grande parte"],
            [">70% a 80%", "50%", "Entrega parcial / instável"],
            [">50% a 70%", "25%", "Abaixo do esperado"],
            ["0% a 50%", "0%", "Insuficiente / grave"],
        ],
        [38 * mm, 31 * mm, 95 * mm],
        header_color=NAVY,
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(data_table(
        ["Critério", "Pergunta-chave", "Teto mensal"],
        [
            ["Assiduidade", "Cumpriu jornada e horários?", "R$ 150,00"],
            ["Qualidade", "Executou conforme o padrão?", "R$ 100,00"],
            ["Taxa de erros", "Quantas falhas e qual gravidade?", "R$ 100,00"],
            ["Produtividade", "Entregou volume e eficiência no contexto?", "R$ 100,00"],
            ["Comportamento", "Atuou com disciplina, respeito e aderência?", "R$ 100,00"],
        ],
        [38 * mm, 91 * mm, 35 * mm],
        header_color=BLUE,
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(cards([[ 
        ("NOTA", "Define a faixa de pagamento do critério.", "blue"),
        ("OCORRÊNCIA", "Aplica o desconto corporativo depois da faixa.", "amber"),
        ("JUSTIFICATIVA", "Explica fato, impacto, expectativa e ação.", "green"),
    ]], widths=[54.7 * mm, 54.7 * mm, 54.6 * mm]))
    s.append(P("Escalonamento imediato", "h2"))
    s.append(bullet("Reincidência A01; códigos Q01, P01 ou C01; risco de segurança; evidência contraditória; conflito de interesse; nota limítrofe sem sustentação." , RED))
    s.append(callout(
        "Frase de controle",
        "Se eu não consigo explicar a decisão com fatos verificáveis e uma expectativa previamente conhecida, ainda não estou pronto para fechar a avaliação.",
        "navy",
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(P("Fórmula vigente", "h2"))
    formula = Table([
        [P("BONIFICACAO FINAL", "table_head"), P("=", "table_head"), P("BONUS-BASE", "table_head"), P("+", "table_head"), P("MONITORIA", "table_head"), P("+", "table_head"), P("TEMPO DE CASA", "table_head")],
        [P("", "table"), P("", "table"), P("até R$ 550,00", "center_small"), P("", "table"), P("R$ 300,00 se elegível", "center_small"), P("", "table"), P("R$ 30,00 / ano completo", "center_small")],
    ], colWidths=[34 * mm, 8 * mm, 31 * mm, 8 * mm, 36 * mm, 8 * mm, 39 * mm])
    formula.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 1), (-1, 1), SURFACE),
    ]))
    s.append(formula)
    s.append(PageBreak())

    s.extend(section_header(
        "12 | Controle do documento",
        "Vigência e atualização",
        "Este manual reflete as regras implementadas na aplicação Avaliação & Bonificação na data de emissão. Em caso de divergência, a regra vigente do sistema e a diretriz corporativa formal devem ser revisadas pela administração responsável.",
    ))
    s.append(data_table(
        ["Campo", "Informação"],
        [
            ["Documento", "Manual de Avaliação - Guia para Avaliadores"],
            ["Versão", "1.0"],
            ["Data de emissão", "28/09/2026"],
            ["Público", "Avaliadores, lideranças, administração e RH"],
            ["Escopo", "Avaliação semanal, critérios, ocorrências, bonificação e fechamento"],
            ["Revisão recomendada", "Sempre que houver alteração em critérios, faixas, códigos, elegibilidade ou valores"],
        ],
        [48 * mm, 116 * mm],
        header_color=NAVY,
    ))
    s.append(Spacer(1, 7 * mm))
    s.append(P("Bases consultadas", "h2"))
    for text in [
        "Implementação vigente: src/lib/constants.ts, src/lib/rules.ts, src/lib/money.ts, src/lib/dates.ts e src/lib/report.ts.",
        "Documentação do projeto: README.md e docs/REGRAS_CALCULO.md.",
        "O guia operacional antigo foi tratado como referência histórica quando divergiu da implementação atual, especialmente em monitoria.",
    ]:
        s.append(bullet(text))
    s.append(Spacer(1, 8 * mm))
    s.append(callout(
        "Registro de ciência",
        "Declaro ter lido este manual e compreendido que a avaliação deve ser baseada em fatos, aplicada com consistência e documentada de modo respeitoso e auditável.",
        "blue",
    ))
    s.append(Spacer(1, 12 * mm))
    signature = Table([
        ["", ""],
        [P("Nome do avaliador", "small"), P("Responsável / liderança", "small")],
        ["", ""],
        [P("Data", "small"), P("Versão recebida", "small")],
    ], colWidths=[78 * mm, 78 * mm], rowHeights=[13 * mm, 7 * mm, 13 * mm, 7 * mm])
    signature.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, MUTED),
        ("LINEBELOW", (0, 2), (-1, 2), 0.7, MUTED),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8 * mm),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    s.append(signature)
    s.append(Spacer(1, 9 * mm))
    s.append(P("KAISAN  |  AVALIACAO &amp; BONIFICACAO", "eyebrow"))
    s.append(P("Documento de uso interno. Não distribua fora do público autorizado.", "small"))
    return s


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = ManualDocTemplate(str(OUT))
    template = doc.pageTemplates[0]
    original = template.onPage

    def combined_on_page(canvas, document):
        draw_cover_background(canvas, document)
        original(canvas, document)

    template.onPage = combined_on_page
    doc.build(build_story())
    print(OUT)


if __name__ == "__main__":
    main()
