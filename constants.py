# constants.py

WEEKLY_CRITERIA = [
    # key, label, weekly_value, monthly_cap
    ("assiduidade", "Assiduidade", 37.50, 150.00),
    ("qualidade", "Qualidade", 25.00, 100.00),
    ("taxa_erros", "Taxa de Erros", 25.00, 100.00),
    ("produtividade", "Produtividade", 25.00, 100.00),
    ("comportamento", "Comportamento", 25.00, 100.00),
]

MONITOR_MONTHLY_CRITERIA = [
    # key, label, monthly_value, obs_weight
    ("acomp_metas", "Acompanhamento de metas", 120.00, "40%"),
    ("org_fluxo", "Organização do fluxo", 75.00, "25%"),
    ("suporte_equipe", "Suporte à equipe", 60.00, "20%"),
    ("disciplina_oper", "Disciplina operacional", 45.00, "15%"),
]

MONITOR_MONTHLY_TOTAL = 300.00

TENURE_BONUS_PER_YEAR = 30.00

SEVERITIES = ["BAIXO", "MEDIO", "ALTO", "CRITICO"]

DEFAULT_ERROR_TYPES = [
    "Erro de Picking",
    "Produto sem Estoque (venda sem estoque)",
    "Divergência de Endereçamento",
    "Pedido enviado errado",
    "Etiqueta/Documento incorreto",
    "Avaria",
    "Outro",
]

MONITOR_CRITERIA = MONITOR_MONTHLY_CRITERIA

# Faixas de pagamento (resultado -> % pago do quesito)
PAY_BANDS = [
    (0, 50, 0.00),
    (51, 70, 0.25),
    (71, 80, 0.50),
    (81, 90, 0.75),
    (91, 100, 1.00),
]
