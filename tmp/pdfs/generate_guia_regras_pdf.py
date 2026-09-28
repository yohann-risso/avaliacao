from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(r"C:\Users\yohan\Desktop\Python\avaliacao")
OUT = ROOT / "output" / "pdf" / "guia_regras_avaliacao_bonificacao.pdf"

PAGE_W, PAGE_H = letter
LEFT = 0.75 * inch
RIGHT = 0.75 * inch
TOP = 0.70 * inch
BOTTOM = 0.70 * inch
CONTENT_W = PAGE_W - LEFT - RIGHT

BLUE = colors.HexColor("#365F91")
LIGHT_BLUE = colors.HexColor("#D9EAF7")
GRID = colors.HexColor("#3B3B3B")
LIGHT_ROW = colors.HexColor("#F7FAFC")
BLACK = colors.black


def register_fonts() -> None:
    fonts = {
        "Arial": Path(r"C:\Windows\Fonts\arial.ttf"),
        "Arial-Bold": Path(r"C:\Windows\Fonts\arialbd.ttf"),
        "Arial-Italic": Path(r"C:\Windows\Fonts\ariali.ttf"),
        "Arial-BoldItalic": Path(r"C:\Windows\Fonts\arialbi.ttf"),
    }
    for name, path in fonts.items():
        if not path.exists():
            raise FileNotFoundError(path)
        pdfmetrics.registerFont(TTFont(name, str(path)))


register_fonts()

BASE = getSampleStyleSheet()
BODY = ParagraphStyle(
    "Body",
    parent=BASE["BodyText"],
    fontName="Arial",
    fontSize=10,
    leading=13.2,
    textColor=BLACK,
    spaceAfter=5,
)
SMALL = ParagraphStyle(
    "Small",
    parent=BODY,
    fontSize=8.2,
    leading=10.5,
    spaceAfter=0,
)
TITLE = ParagraphStyle(
    "Title",
    parent=BASE["Title"],
    fontName="Arial-Bold",
    fontSize=18,
    leading=22,
    alignment=TA_CENTER,
    textColor=BLACK,
    spaceAfter=10,
)
SUBTITLE = ParagraphStyle(
    "Subtitle",
    parent=BODY,
    fontName="Arial-Italic",
    alignment=TA_CENTER,
    spaceAfter=14,
)
H1 = ParagraphStyle(
    "Heading 1",
    parent=BASE["Heading1"],
    fontName="Arial-Bold",
    fontSize=14,
    leading=17,
    textColor=BLUE,
    spaceBefore=13,
    spaceAfter=5,
    keepWithNext=True,
)
H2 = ParagraphStyle(
    "Heading 2",
    parent=BASE["Heading2"],
    fontName="Arial-Bold",
    fontSize=10.5,
    leading=13,
    textColor=BLACK,
    spaceBefore=7,
    spaceAfter=4,
    keepWithNext=True,
)
TABLE_HEAD = ParagraphStyle(
    "Table Head",
    parent=SMALL,
    fontName="Arial-Bold",
    textColor=BLACK,
)
TABLE_BODY = ParagraphStyle(
    "Table Body",
    parent=SMALL,
    textColor=BLACK,
)
TABLE_BODY_BOLD = ParagraphStyle(
    "Table Body Bold",
    parent=TABLE_BODY,
    fontName="Arial-Bold",
)
FOOTER = ParagraphStyle(
    "Footer",
    parent=SMALL,
    fontSize=7.2,
    leading=8,
    textColor=colors.HexColor("#666666"),
)


def p(text: str, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(text, style)


def heading(number: int, title: str) -> Paragraph:
    return p(f"{number}. {title}", H1)


def rule_table(
    headers: list[str],
    rows: list[list[str]],
    widths: list[float],
    *,
    font_size: float = 8.2,
    header_rows: int = 1,
    bold_last_row: bool = False,
) -> Table:
    head = [p(value, TABLE_HEAD) for value in headers]
    body = [[p(str(value), TABLE_BODY) for value in row] for row in rows]
    table = Table([head, *body], colWidths=widths, repeatRows=header_rows, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.6, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_ROW]),
        ("FONTSIZE", (0, 1), (-1, -1), font_size),
    ]
    if bold_last_row:
        commands.append(("FONTNAME", (0, -1), (-1, -1), "Arial-Bold"))
    table.setStyle(TableStyle(commands))
    return table


def one_column_table(title: str, body: str) -> Table:
    table = Table(
        [[p(title, TABLE_HEAD)], [p(body, TABLE_BODY)]],
        colWidths=[CONTENT_W],
        hAlign="LEFT",
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.6, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return table


def on_page(canvas, doc) -> None:
    if canvas.getPageNumber() == 1:
        return
    canvas.saveState()
    canvas.setFont("Arial", 7.2)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(LEFT, 0.37 * inch, "Guia resumido de avaliação e bonificação")
    canvas.drawRightString(PAGE_W - RIGHT, 0.37 * inch, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()


def build_story() -> list:
    story: list = [
        p("Guia resumido de avaliação e bonificação", TITLE),
        p("Regras vigentes para avaliadores - Uso interno - Setembro/2026", SUBTITLE),
        p(
            "Este documento reúne, de forma simples, os critérios da avaliação semanal, as faixas de pagamento, os códigos de ocorrência e as regras usadas no fechamento mensal. Ele orienta a decisão do avaliador e não descreve a operação da plataforma."
        ),
    ]

    story.extend([
        heading(1, "Como funciona a avaliação"),
        p("A avaliação é semanal e depois consolidada em uma competência mensal de quatro semanas. Cada colaborador operacional elegível recebe um resultado de 0% a 100% em cinco critérios."),
        rule_table(
            ["Etapa", "O que acontece"],
            [
                ["Avaliação semanal", "O colaborador é avaliado nos cinco critérios da função."],
                ["Registro de justificativas", "Toda nota abaixo de 100% deve ser explicada com fatos do período."],
                ["Registro de ocorrências", "Os códigos corporativos aplicam descontos depois da faixa de pagamento."],
                ["Consolidação mensal", "O sistema soma as quatro semanas elegíveis e aplica as regras mensais."],
                ["Cálculo final", "Somam-se bônus-base, monitoria quando elegível e adicional por tempo de casa."],
            ],
            [2.0 * inch, 4.9 * inch],
        ),
        heading(2, "Critérios avaliados"),
        rule_table(
            ["Critério", "O que é observado", "Mensal", "Semanal"],
            [
                ["Assiduidade", "Presença, pontualidade e regularidade na rotina.", "R$ 150,00", "R$ 37,50"],
                ["Qualidade", "Cuidado, conformidade, retrabalho e padrão de entrega.", "R$ 100,00", "R$ 25,00"],
                ["Taxa de erros", "Quantidade e gravidade das falhas registradas.", "R$ 100,00", "R$ 25,00"],
                ["Produtividade", "Ritmo, meta, volume e eficiência dentro do padrão.", "R$ 100,00", "R$ 25,00"],
                ["Comportamento", "Disciplina, colaboração, postura e cumprimento de normas.", "R$ 100,00", "R$ 25,00"],
                ["Total base", "Soma máxima dos cinco critérios.", "R$ 550,00", "R$ 137,50"],
            ],
            [1.35 * inch, 3.45 * inch, 1.05 * inch, 1.05 * inch],
            bold_last_row=True,
        ),
        p("Os valores mensais são divididos por quatro semanas fixas. O valor semanal máximo do bônus-base é R$ 137,50."),
        heading(3, "Guia simples de pontuação"),
        rule_table(
            ["Resultado", "Significado geral"],
            [
                ["91% a 100%", "Entrega dentro do esperado, sem desvio relevante ou com ajuste isolado de baixo impacto."],
                ["81% a 90%", "Atende em grande parte, com pontos objetivos de ajuste."],
                ["71% a 80%", "Entrega parcial ou instável, com necessidade de acompanhamento."],
                ["51% a 70%", "Desempenho significativamente abaixo do esperado."],
                ["0% a 50%", "Falha grave, reincidência importante ou resultado insuficiente no critério."],
            ],
            [1.6 * inch, 5.3 * inch],
        ),
        PageBreak(),
        heading(4, "Faixas de pagamento"),
        p("O pagamento não é calculado diretamente pelo percentual exato. Cada critério entra em uma faixa própria."),
        rule_table(
            ["Resultado no critério", "Percentual pago daquele critério"],
            [
                ["0% a 50%", "0%"],
                ["Acima de 50% até 70%", "25%"],
                ["Acima de 70% até 80%", "50%"],
                ["Acima de 80% até 90%", "75%"],
                ["Acima de 90% até 100%", "100%"],
            ],
            [3.5 * inch, 3.4 * inch],
        ),
        Spacer(1, 8),
        rule_table(
            ["Exemplo simples", "Resultado"],
            [
                ["Qualidade possui valor mensal máximo de R$ 100,00.", ""],
                ["O colaborador atingiu 85% em Qualidade.", "Entra na faixa de 75%."],
                ["Valor pago em Qualidade no mês completo.", "R$ 75,00 antes de ocorrências."],
            ],
            [3.5 * inch, 3.4 * inch],
        ),
        heading(5, "Como as ocorrências impactam a avaliação"),
        p("A nota define a faixa de pagamento. Depois, os códigos de ocorrência aplicam os descontos corporativos. Os descontos se acumulam até o limite disponível em cada critério."),
        rule_table(
            ["Nível", "Leitura geral", "Tratamento"],
            [
                ["Baixo", "Desvio pontual de impacto leve.", "Registrar o fato e aplicar o código correspondente."],
                ["Médio", "Impacto perceptível ou repetição.", "Documentar consequência e acompanhar."],
                ["Alto", "Impacto operacional importante.", "Revisar com a liderança antes do fechamento."],
                ["Crítico", "Impacto expressivo ou risco relevante.", "Escalonar imediatamente e aplicar a regra vigente."],
            ],
            [1.0 * inch, 2.6 * inch, 3.3 * inch],
        ),
        p("Os pontos são uma referência máxima de desconto. O sistema nunca desconta mais que a bonificação disponível nem além da incidência permitida pela diretriz."),
        heading(6, "O que observar em cada critério"),
        rule_table(
            ["Critério", "Evidências adequadas", "Cuidados"],
            [
                ["Assiduidade", "Ponto, escala, atrasos, saídas e documentos previstos na política.", "Use os códigos A; não registre diagnóstico ou dado médico desnecessário."],
                ["Qualidade", "Retrabalho, divergência, avaria, conferência e aderência ao procedimento.", "Separe falha atribuível ao colaborador de problema sistêmico."],
                ["Taxa de erros", "Código, quantidade, gravidade, itens processados e impacto.", "Não use impressão genérica; registre o fato verificável."],
                ["Produtividade", "Itens, meta, ritmo, consistência, paradas e complexidade da tarefa.", "Não premie velocidade obtida com perda de qualidade ou segurança."],
                ["Comportamento", "Normas, comunicação, colaboração, segurança e resposta a orientações.", "Avalie condutas observáveis, não personalidade ou afinidade."],
            ],
            [1.3 * inch, 3.1 * inch, 2.5 * inch],
            font_size=7.9,
        ),
        PageBreak(),
        heading(7, "Regras de assiduidade"),
        p("As ocorrências A01 a A08 afetam a assiduidade semanal ou mensal e, em alguns casos, os demais critérios. Quantidades repetidas acumulam incidência até o limite disponível."),
        rule_table(
            ["Código", "Ocorrência", "Nível", "Pontos", "Efeito"],
            [
                ["A01", "Falta sem atestado", "Alto", "250", "Perde 100% da assiduidade mensal e 100% dos outros critérios na semana. A segunda A01 bloqueia todo o bônus-base mensal."],
                ["A02", "Falta com atestado", "Baixo", "47,5", "Perde 100% da assiduidade semanal e 20% por dia nos outros critérios."],
                ["A03", "Declaração de até 50% da carga", "Baixo", "87,5", "Perde 100% da assiduidade semanal e 50% dos outros critérios."],
                ["A04", "Declaração acima de 50% da carga", "Alto", "137,5", "Perde 100% de todos os critérios da semana."],
                ["A05", "Saída por poucas horas", "Baixo", "37,5", "Perde 100% da assiduidade semanal."],
                ["A06", "Saída superior a 50% do dia", "Alto", "125", "Meia falta: perde 50% da assiduidade mensal e 50% dos outros critérios na semana."],
                ["A07", "Atraso até 7h30", "Baixo", "9,37", "Perde 25% da assiduidade semanal."],
                ["A08", "Atraso depois de 7h30", "Alto", "37,5", "Perde 100% da assiduidade semanal."],
            ],
            [0.55 * inch, 1.7 * inch, 0.65 * inch, 0.62 * inch, 3.38 * inch],
            font_size=7.6,
        ),
        Spacer(1, 7),
        p("Regras mensais especiais", H2),
        rule_table(
            ["Regra", "Aplicação"],
            [
                ["A01", "Uma ocorrência elimina a assiduidade mensal. Duas ocorrências na competência bloqueiam todo o bônus-base de R$ 550,00."],
                ["A06", "Cada ocorrência representa meia falta e pode retirar até 50% da assiduidade mensal."],
                ["Acúmulo", "Ocorrências semanais se acumulam por critério, sempre limitadas ao saldo disponível."],
            ],
            [1.25 * inch, 5.65 * inch],
        ),
        heading(8, "Regras de qualidade e taxa de erros"),
        p("Os códigos Q01 a Q04 afetam, ao mesmo tempo, a bonificação semanal de Qualidade e de Taxa de erros."),
        rule_table(
            ["Código", "Gravidade", "Pontos", "Efeito semanal"],
            [
                ["Q01", "Crítico", "50", "Perde 100% de Qualidade e Taxa de erros."],
                ["Q02", "Alto", "25", "Perde 50% de Qualidade e Taxa de erros."],
                ["Q03", "Médio", "12,5", "Perde 25% de Qualidade e Taxa de erros."],
                ["Q04", "Baixo", "5", "Perde 10% de Qualidade e Taxa de erros."],
            ],
            [0.8 * inch, 1.1 * inch, 0.85 * inch, 4.15 * inch],
        ),
        PageBreak(),
        heading(9, "Regras de produtividade e comportamento"),
        p("Os códigos P incidem sobre Produtividade. Os códigos C incidem sobre Comportamento."),
        rule_table(
            ["Código", "Categoria", "Gravidade", "Pontos", "Efeito semanal"],
            [
                ["P01", "Produtividade", "Crítico", "25", "Perde 100% de Produtividade."],
                ["P02", "Produtividade", "Alto", "12,5", "Perde 50% de Produtividade."],
                ["P03", "Produtividade", "Médio", "6,3", "Perde 25% de Produtividade."],
                ["P04", "Produtividade", "Baixo", "2,5", "Perde 10% de Produtividade."],
                ["C01", "Comportamento", "Crítico", "25", "Perde 100% de Comportamento. Cabe carta de advertência conforme o processo interno."],
                ["C02", "Comportamento", "Alto", "12,5", "Perde 50% de Comportamento."],
                ["C03", "Comportamento", "Médio", "6,3", "Perde 25% de Comportamento."],
                ["C04", "Comportamento", "Baixo", "2,5", "Perde 10% de Comportamento."],
            ],
            [0.65 * inch, 1.35 * inch, 0.85 * inch, 0.7 * inch, 3.35 * inch],
            font_size=7.8,
        ),
        heading(10, "Monitoria liderança e tempo de casa"),
        rule_table(
            ["Componente", "Regra vigente", "Valor"],
            [
                ["Monitoria", "Adicional fixo para monitor ativo e elegível, com data de início válida e ao menos uma semana posterior à semana de início. Não há avaliação mensal de monitoria.", "R$ 300,00"],
                ["Coordenação e supervisão", "Quando elegíveis, ficam em grupo separado, não recebem avaliação semanal e recebem a base mensal.", "R$ 550,00"],
                ["Tempo de casa", "Adicional por ano completo, calculado na data de referência do fechamento.", "R$ 30,00 por ano"],
            ],
            [1.45 * inch, 4.35 * inch, 1.1 * inch],
            font_size=8.0,
        ),
        p("A semana de contratação não conta. O colaborador entra somente em semana posterior à semana da admissão. Semanas com segunda-feira posterior ao desligamento não são elegíveis."),
        heading(11, "Resumo do cálculo final"),
        one_column_table(
            "Fórmula resumida",
            "Bonificação final = bônus-base após faixas e ocorrências + R$ 300,00 de monitoria, quando elegível + R$ 30,00 por ano completo de empresa."
        ),
        Spacer(1, 8),
        rule_table(
            ["Parte", "Quando se aplica"],
            [
                ["Avaliação base semanal", "Para colaboradores operacionais avaliáveis."],
                ["Monitoria fixa", "Para monitor ativo e elegível; não depende de nota mensal."],
                ["Base de liderança", "Para coordenação e supervisão elegíveis, sem avaliação semanal."],
                ["Tempo de casa", "Conforme os anos completos de empresa."],
            ],
            [2.15 * inch, 4.75 * inch],
        ),
        PageBreak(),
        heading(12, "Pontos importantes para o avaliador"),
        rule_table(
            ["Ponto", "Explicação"],
            [
                ["Basear a avaliação em fatos", "Use registros, indicadores e situações verificáveis do período."],
                ["Avaliar cada critério separadamente", "Um bom resultado em um critério não apaga problema relevante em outro."],
                ["Não duplicar o desconto", "A nota define a faixa; a ocorrência aplica o desconto depois. Não reduza a nota apenas para repetir o efeito do mesmo fato."],
                ["Justificar notas abaixo de 100%", "Informe fato, impacto, expectativa e ação de acompanhamento."],
                ["Comparar situações equivalentes", "Use o mesmo padrão para funções e condições operacionais semelhantes."],
                ["Preservar o respeito e a privacidade", "Registre condutas e resultados, sem rótulos ou dados pessoais desnecessários."],
                ["Revisar casos graves", "Reincidência A01 e códigos Q01, P01 ou C01 devem ser calibrados com a liderança."],
            ],
            [2.5 * inch, 4.4 * inch],
        ),
        p("Checklist antes do fechamento", H2),
        rule_table(
            ["Verificação", "Condição esperada"],
            [
                ["Cobertura", "Todas as semanas elegíveis possuem avaliação."],
                ["Notas", "Percentuais entre 0% e 100%, coerentes com as evidências."],
                ["Justificativas", "Todos os resultados abaixo de 100% estão explicados."],
                ["Ocorrências", "Códigos, quantidades, datas e contextos foram conferidos."],
                ["Elegibilidade", "Admissão, desligamento, monitoria e liderança foram revisados."],
                ["Calibração", "Casos graves, atípicos e próximos aos limites de faixa foram revisados."],
                ["Feedback", "O colaborador recebeu ou receberá retorno objetivo sobre o período."],
            ],
            [2.0 * inch, 4.9 * inch],
        ),
        Spacer(1, 10),
        p("Referência vigente", H2),
        p("Este guia reflete as regras implementadas no sistema Avaliação &amp; Bonificação em 28/09/2026. Deve ser revisado sempre que critérios, faixas, códigos, valores ou regras de elegibilidade forem alterados."),
    ])
    return story


class RulesDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=letter,
            leftMargin=LEFT,
            rightMargin=RIGHT,
            topMargin=TOP,
            bottomMargin=BOTTOM,
            title="Guia resumido de avaliação e bonificação",
            author="KAISAN",
            subject="Regras vigentes para avaliadores",
            creator="Avaliação & Bonificação",
        )
        frame = Frame(
            LEFT,
            BOTTOM,
            CONTENT_W,
            PAGE_H - TOP - BOTTOM,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
            id="body",
        )
        self.addPageTemplates([PageTemplate(id="rules", frames=[frame], onPage=on_page)])


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = RulesDoc(str(OUT))
    doc.build(build_story())
    print(OUT)


if __name__ == "__main__":
    main()
