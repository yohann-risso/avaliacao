from __future__ import annotations

from datetime import date, datetime

from constants import MONITOR_MONTHLY_CRITERIA, WEEKLY_CRITERIA
from rules import calculate_weekly_payment
from utils import competencia_from_week_start, current_month_br, parse_iso_date, weeks_for_competencia


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_week_start() -> str:
    today = date.today()
    return today.fromordinal(today.toordinal() - today.weekday()).isoformat()


def default_month() -> str:
    return current_month_br()


def weekly_preview(evaluation) -> dict:
    return calculate_weekly_payment({
        "assiduidade_pct": evaluation.assiduidade_pct,
        "qualidade_pct": evaluation.qualidade_pct,
        "taxa_erros_pct": evaluation.taxa_erros_pct,
        "produtividade_pct": evaluation.produtividade_pct,
        "comportamento_pct": evaluation.comportamento_pct,
        "week_start": evaluation.week_start,
    })


def weekly_criteria() -> list[tuple[str, str]]:
    return [(key, label) for key, label, *_ in WEEKLY_CRITERIA]


def monitor_criteria() -> list[tuple[str, str]]:
    return [(key, label) for key, label, *_ in MONITOR_MONTHLY_CRITERIA]


def month_weeks(month: str) -> list[str]:
    year, number = map(int, month.split("-"))
    return [week.isoformat() for week in weeks_for_competencia(year, number)]


def employee_is_eligible(employee, week_start: str) -> bool:
    week_date = parse_iso_date(week_start)
    hire_date = parse_iso_date(employee.hire_date)
    if not week_date or not hire_date:
        return False
    return week_date >= hire_date
