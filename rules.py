# rules.py
from datetime import datetime
from dataclasses import dataclass

from constants import PAY_BANDS, WEEKLY_CRITERIA
from utils import competencia_from_week_start, monthly_cap_to_week_value, number_br, pay_band_multiplier, pct_br

# Você edita aqui SEM mexer no resto do app.

SEVERITY_WEIGHTS = {
    "BAIXO": 0.5,
    "MEDIO": 1.0,
    "ALTO": 2.0,
    "CRITICO": 4.0,
}


# Mapeia a função/cargo para uma "família" de regra
# Ajuste conforme seus cargos reais:
def role_family(role: str) -> str:
    r = (role or "").lower()
    if "expedi" in r or "confer" in r or "pack" in r:
        return "EXPEDICAO"
    if "pick" in r or "separa" in r:
        return "PICKING"
    if "estoq" in r or "repos" in r:
        return "ESTOQUE"
    return "GERAL"


def role_family_label(fam: str) -> str:
    return {
        "EXPEDICAO": "Expedição",
        "PICKING": "Picking",
        "ESTOQUE": "Estoque",
        "GERAL": "Geral",
    }.get(str(fam or "").upper(), str(fam or "Geral"))

# Tipos críticos por família
CRITICAL_TYPES = {
    "EXPEDICAO": {"Pedido enviado errado"},
    "PICKING": set(),
    "ESTOQUE": set(),
    "GERAL": set(),
}

@dataclass
class Suggestion:
    suggested_pct: float
    reason: str

def suggest_taxa_erros_pct(
    role: str,
    items_count: int,
    weekly_errors_rows: list[dict],
    strict_critical_zero: bool = True,
    factor: float = 12.0,
) -> Suggestion:
    """
    Retorna uma sugestão de taxa_erros_pct (0-100) baseada no log de erros.
    - Se EXPEDIÇÃO e houver "Pedido enviado errado" CRÍTICO:
      - strict_critical_zero=True => sugere 0%
      - senão => aplica peso alto
    - Se PICKING e items_count>0 => usa (erros_ponderados / itens) com fator
    - Caso contrário => penalidade simples por peso
    """
    fam = role_family(role)
    fam_label = role_family_label(fam)
    if not weekly_errors_rows:
        return Suggestion(100.0, "Sem erros registrados no log da semana.")

    # Checagem de críticos (por tipo)
    critical_types = CRITICAL_TYPES.get(fam, set())
    has_critical_type = any((row.get("error_type") in critical_types and row.get("severity") == "CRITICO") for row in weekly_errors_rows)

    if has_critical_type and strict_critical_zero:
        return Suggestion(0.0, f"Detectado erro crítico para {fam_label}; a sugestão zera a taxa de erros.")

    # Soma ponderada
    weighted = 0.0
    critical_count = 0
    for row in weekly_errors_rows:
        sev = (row.get("severity") or "MEDIO").upper()
        qty = int(row.get("qty") or 1)
        w = SEVERITY_WEIGHTS.get(sev, 1.0)
        weighted += w * qty
        if sev == "CRITICO":
            critical_count += qty

    # Família PICKING: usa itens como base se existir
    if fam == "PICKING" and items_count and items_count > 0:
        rate = weighted / float(items_count)  # erros ponderados por item
        pct = max(0.0, 100.0 - (rate * 100.0 * factor))
        return Suggestion(
            round(pct, 1),
            (
                f"{fam_label}: erros ponderados {number_br(weighted, 2)}, "
                f"itens {items_count}, taxa {pct_br(rate * 100, 2)}. "
                f"Fator aplicado: {number_br(factor, 1)}."
            )
        )

    # Outras famílias: penalidade simples (ajuste o divisor se quiser)
    # Quanto maior o divisor, mais "leve" a penalidade.
    divisor = 1.5 if fam == "EXPEDICAO" else 2.5
    penalty = (weighted / divisor) * 10.0  # escala
    pct = max(0.0, 100.0 - penalty)

    extra = f" incluindo {critical_count} crítico(s)" if critical_count else ""
    return Suggestion(
        round(pct, 1),
        (
            f"{fam_label}: erros ponderados {number_br(weighted, 2)}{extra}; "
            f"divisor {number_br(divisor, 1)}; penalidade {pct_br(penalty, 1)}."
        )
    )

def band_multiplier(pct: float) -> float:
    return pay_band_multiplier(pct, PAY_BANDS)


def calculate_weekly_payment(row) -> dict:
    """
    Pagamento semanal por FAIXA, mas usando rateio do teto mensal:
    valor da semana = monthly_cap / número de semanas válidas da competência
    """
    result = {}

    week_start_raw = row.get("week_start")
    if not week_start_raw:
        # fallback defensivo: se não vier a semana, usa o weekly_value legado
        for key, _label, weekly_value, _cap in WEEKLY_CRITERIA:
            pct = float(row.get(f"{key}_pct", 0) or 0)
            mult = band_multiplier(pct)
            result[key] = float(weekly_value) * mult
        return result

    if isinstance(week_start_raw, str):
        week_start = datetime.strptime(week_start_raw.strip(), "%Y-%m-%d").date()
    else:
        week_start = week_start_raw

    competencia = competencia_from_week_start(week_start)

    for key, _label, _weekly_value, monthly_cap in WEEKLY_CRITERIA:
        pct = float(row.get(f"{key}_pct", 0) or 0)
        mult = band_multiplier(pct)

        week_value = monthly_cap_to_week_value(float(monthly_cap), competencia)
        result[key] = float(week_value) * mult

    return result
