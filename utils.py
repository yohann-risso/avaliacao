# utils.py

from datetime import date, timedelta, datetime
import calendar

from constants import PAY_BANDS


def date_iso_to_br(d: str | date) -> str:
    """
    Converte 'YYYY-MM-DD' ou date -> 'dd/mm/aaaa'
    """
    if not d:
        return "-"
    if isinstance(d, date):
        return d.strftime("%d/%m/%Y")
    try:
        return datetime.strptime(str(d), "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(d)


def datetime_iso_to_br(dt: str) -> str:
    """
    Converte 'YYYY-MM-DD HH:MM:SS' -> 'dd/mm/aaaa HH:MM'
    """
    if not dt:
        return "-"
    try:
        return datetime.fromisoformat(str(dt)).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(dt)


def month_label_to_br(month_label: str) -> str:
    """
    Converte 'YYYY-MM' -> 'MM/AAAA' para exibição.
    """
    if not str(month_label or "").strip():
        return "-"
    try:
        return datetime.strptime(str(month_label).strip(), "%Y-%m").strftime("%m/%Y")
    except Exception:
        return str(month_label)


def parse_iso_date(value: str | date) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def current_month_br() -> str:
    return date.today().strftime("%m/%Y")


def number_br(value, decimals: int = 1) -> str:
    if value is None:
        return "-"
    if isinstance(value, str) and value.strip() in {"", "-"}:
        return value.strip() or "-"
    try:
        numeric = float(value)
        if numeric != numeric:
            return "-"
        text = f"{numeric:,.{int(decimals)}f}"
    except Exception:
        return str(value)
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def pct_br(value, decimals: int = 1) -> str:
    if value is None:
        return "-"
    if isinstance(value, str) and value.strip() in {"", "-"}:
        return value.strip() or "-"
    return f"{number_br(value, decimals)}%"


def pay_band_multiplier(pct: float, pay_bands=None) -> float:
    """
    Retorna o multiplicador da faixa de pagamento.

    PAY_BANDS documenta faixas inteiras (0-50, 51-70, ...), mas alguns
    cálculos geram percentuais decimais. Para evitar buracos como 90.5%
    retornando 0, os limites são tratados como contínuos:
    <=50, >50-70, >70-80, >80-90, >90-100.
    """
    try:
        p = max(0.0, min(100.0, float(pct)))
    except (TypeError, ValueError):
        return 0.0

    bands = pay_bands if pay_bands is not None else PAY_BANDS
    normalized_bands = sorted(
        ((float(lo), float(hi), float(mult)) for lo, hi, mult in bands),
        key=lambda band: band[1],
    )

    for _lo, hi, mult in normalized_bands:
        if p <= hi:
            return mult

    return normalized_bands[-1][2] if normalized_bands else 0.0


def severity_label(value: str) -> str:
    labels = {
        "BAIXO": "BAIXO",
        "MEDIO": "MÉDIO",
        "MÉDIO": "MÉDIO",
        "ALTO": "ALTO",
        "CRITICO": "CRÍTICO",
        "CRÍTICO": "CRÍTICO",
    }
    key = str(value or "").strip().upper()
    return labels.get(key, str(value or "").strip())


def strip_embedded_justification_block(notes: str, marker: str) -> str:
    """
    Remove o bloco técnico de justificativas salvo dentro de notes.
    As justificativas também ficam em colunas próprias; na UI, notes deve
    mostrar apenas a observação geral para evitar duplicação ao salvar.
    """
    text = str(notes or "").strip()
    marker = str(marker or "").strip()
    if not text or not marker:
        return text

    idx = text.find(marker)
    if idx == -1:
        return text

    return text[:idx].rstrip()


def brl(v: float) -> str:
    s = f"{v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def parse_month_yyyy_mm(yyyy_mm: str) -> tuple[int, int]:
    y, m = yyyy_mm.split("-")
    return int(y), int(m)

def month_range(year: int, month: int) -> tuple[date, date]:
    first = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)
    return first, last

def monday_of(d: date) -> date:
    """Retorna a segunda-feira da semana (semana operacional)."""
    return d - timedelta(days=d.weekday())


def is_week_after_start_date(
    start_date_iso: str,
    week_start_iso: str,
    missing_is_eligible: bool = True,
) -> bool:
    start_date = parse_iso_date(start_date_iso)
    if start_date is None:
        return bool(missing_is_eligible)

    week_start = datetime.strptime(str(week_start_iso).strip(), "%Y-%m-%d").date()
    return week_start > monday_of(start_date)


def eligible_weeks_after_start_date(
    start_date_iso: str,
    weeks_iso: list[str],
    missing_is_eligible: bool = True,
) -> list[str]:
    return [
        ws
        for ws in weeks_iso
        if is_week_after_start_date(start_date_iso, ws, missing_is_eligible=missing_is_eligible)
    ]


def has_eligible_week_after_start_date(
    start_date_iso: str,
    weeks_iso: list[str],
    missing_is_eligible: bool = False,
) -> bool:
    return bool(
        eligible_weeks_after_start_date(
            start_date_iso,
            weeks_iso,
            missing_is_eligible=missing_is_eligible,
        )
    )

def week_end_friday(week_start: date) -> date:
    """Semana operacional: segunda -> sexta."""
    return week_start + timedelta(days=4)

def week_label(week_start: date) -> str:
    """Label da semana operacional (Seg → Sex)."""
    week_end = week_end_friday(week_start)
    return f"{week_start.strftime('%d/%m/%Y')} → {week_end.strftime('%d/%m/%Y')}"

def weeks_that_intersect_month(year: int, month: int) -> list[date]:
    """
    Retorna as segundas-feiras das semanas que intersectam o mês.
    Semana considerada: Seg→Sex.
    Critério de interseção: qualquer dia útil (Seg–Sex) dentro do mês.
    """
    first, last = month_range(year, month)

    # começa na segunda-feira da semana do primeiro dia do mês
    cur = monday_of(first)
    weeks = []

    while cur <= last:
        # intervalo útil da semana
        wk_start = cur
        wk_end = week_end_friday(cur)

        # interseção com [first, last]
        if wk_end >= first and wk_start <= last:
            weeks.append(cur)

        cur += timedelta(days=7)

    return weeks

def weeks_for_month(year: int, month: int):
    return weeks_that_intersect_month(year, month)

# =========================================================
# COMPETÊNCIA COM FECHAMENTO DIA 25
# =========================================================

FECHAMENTO_DIA = 25


def competencia_from_week_start(week_start: date, fechamento_dia: int = FECHAMENTO_DIA) -> str:
    """
    Define a competência da semana pela sexta-feira.
    - sexta até 25 => mês da própria sexta
    - sexta depois de 25 => próximo mês
    """
    friday = week_end_friday(week_start)

    if friday.day > fechamento_dia:
        if friday.month == 12:
            return f"{friday.year + 1}-01"
        return f"{friday.year}-{friday.month + 1:02d}"

    return f"{friday.year}-{friday.month:02d}"


def weeks_for_competencia(year: int, month: int, fechamento_dia: int = FECHAMENTO_DIA) -> list[date]:
    """
    Retorna todas as segundas-feiras cuja competência pertença ao mês informado.
    """
    target = f"{year}-{month:02d}"

    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    start = monday_of(first_day - timedelta(days=35))
    end = monday_of(last_day + timedelta(days=35))

    weeks = []
    cur = start

    while cur <= end:
        if competencia_from_week_start(cur, fechamento_dia) == target:
            weeks.append(cur)
        cur += timedelta(days=7)

    return weeks


def weeks_count_for_competencia_label(month_label: str, fechamento_dia: int = FECHAMENTO_DIA) -> int:
    """
    month_label: YYYY-MM
    """
    year, month = parse_month_yyyy_mm(month_label)
    return max(1, len(weeks_for_competencia(year, month, fechamento_dia)))


def monthly_cap_to_week_value(monthly_cap: float, month_label: str, fechamento_dia: int = FECHAMENTO_DIA) -> float:
    """
    Rateia o teto mensal igualmente entre as semanas válidas da competência.
    """
    weeks_count = weeks_count_for_competencia_label(month_label, fechamento_dia)
    return float(monthly_cap) / float(weeks_count)
