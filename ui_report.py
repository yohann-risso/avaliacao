# ui_report.py

import io
import pandas as pd
import streamlit as st
from datetime import date, datetime
from xml.sax.saxutils import escape as xml_escape

from db import fetch_df, normalize_month_label
from constants import WEEKLY_CRITERIA, MONITOR_MONTHLY_CRITERIA, TENURE_BONUS_PER_YEAR
from theme import render_divider, render_operation_status, render_page_header, render_section_header
from utils import (
    brl,
    current_month_br,
    date_iso_to_br,
    eligible_weeks_after_start_date,
    has_eligible_week_after_start_date,
    is_week_after_start_date,
    month_label_to_br,
    pay_band_multiplier,
    parse_iso_date,
    pct_br,
    severity_label,
    week_label,
    week_end_friday,
    weeks_for_competencia,
    competencia_from_week_start,
    monthly_cap_to_week_value,
)

# compatibilidade: seu utils pode ter weeks_for_month (alias) ou weeks_that_intersect_month
try:
    from utils import weeks_for_month
except Exception:
    from utils import weeks_that_intersect_month as weeks_for_month

from rules import calculate_weekly_payment

# PAY_BANDS fallback (caso não exista no constants.py)
try:
    from constants import PAY_BANDS
except Exception:
    PAY_BANDS = [
        (0, 50, 0.00),
        (51, 70, 0.25),
        (71, 80, 0.50),
        (81, 90, 0.75),
        (91, 100, 1.00),
    ]

# -----------------------------
# ReportLab (PDF)
# -----------------------------
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
    PageBreak,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER


# -----------------------------
# Helpers
# -----------------------------
def brl_to_float(x: str) -> float:
    s = str(x).replace("R$", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def pdf_text(value: str) -> str:
    text = str(value or "").strip()
    text = xml_escape(text)
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")


def pdf_field(label: str, value: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(f"<b>{pdf_text(label)}:</b> {pdf_text(value)}", style)


def band_multiplier(pct: float) -> float:
    return pay_band_multiplier(pct, PAY_BANDS)


def band_label(mult: float) -> str:
    return pct_br(mult * 100, 0)


def calc_monitoria_bonus_from_row(mrow: dict) -> float:
    """
    Calcula o valor mensal de monitoria usando faixas por critério.
    MONITOR_MONTHLY_CRITERIA: (key, label, monthly_value, obs)
    No banco: campos <key>_pct
    """
    if not mrow:
        return 0.0

    total = 0.0
    for key, _label, monthly_value, _obs in MONITOR_MONTHLY_CRITERIA:
        pct = float(mrow.get(f"{key}_pct", 0) or 0)
        mult = band_multiplier(pct)
        total += float(monthly_value) * mult
    return float(total)


def years_in_company(hire_date_iso: str, reference_date: date) -> int:
    if not str(hire_date_iso or "").strip():
        return 0

    try:
        hire_date = datetime.strptime(str(hire_date_iso).strip(), "%Y-%m-%d").date()
    except Exception:
        return 0

    years = reference_date.year - hire_date.year
    if (reference_date.month, reference_date.day) < (hire_date.month, hire_date.day):
        years -= 1
    return max(0, years)


def parse_hire_date(hire_date_iso: str) -> date | None:
    return parse_iso_date(hire_date_iso)


def is_week_after_hire(hire_date_iso: str, week_start_iso: str) -> bool:
    return is_week_after_start_date(hire_date_iso, week_start_iso, missing_is_eligible=True)


def eligible_weeks_for_employee(hire_date_iso: str, weeks_iso: list[str]) -> list[str]:
    return eligible_weeks_after_start_date(hire_date_iso, weeks_iso, missing_is_eligible=True)


def is_week_before_or_on_termination(termination_date_iso: str, week_start_iso: str) -> bool:
    termination_date = parse_iso_date(termination_date_iso)
    if termination_date is None:
        return True

    try:
        week_start = datetime.strptime(str(week_start_iso).strip(), "%Y-%m-%d").date()
    except Exception:
        return False

    return week_start <= termination_date


def eligible_weeks_for_valid_employee(
    hire_date_iso: str,
    weeks_iso: list[str],
    termination_date_iso: str = "",
) -> list[str]:
    if parse_hire_date(hire_date_iso) is None:
        return []

    weeks_after_hire = eligible_weeks_after_start_date(
        hire_date_iso,
        weeks_iso,
        missing_is_eligible=False,
    )
    return [
        ws
        for ws in weeks_after_hire
        if is_week_before_or_on_termination(termination_date_iso, ws)
    ]


def is_monitoria_eligible_for_month(monitor_start_date_iso: str, weeks_iso: list[str]) -> bool:
    return has_eligible_week_after_start_date(
        monitor_start_date_iso,
        weeks_iso,
        missing_is_eligible=False,
    )


def is_leadership_eligible_for_month(leadership_start_date_iso: str, weeks_iso: list[str]) -> bool:
    return has_eligible_week_after_start_date(
        leadership_start_date_iso,
        weeks_iso,
        missing_is_eligible=False,
    )


def _has_role_start_date(value) -> bool:
    return bool(str(value or "").strip())


def is_employee_monitor_for_month(emp, weeks_iso: list[str]) -> bool:
    if int(emp.get("is_monitor", 0) or 0) != 1:
        return False
    if int(emp.get("is_leadership", 0) or 0) == 1:
        return False
    start_date = str(emp.get("monitor_start_date", "") or "")
    return _has_role_start_date(start_date) and is_monitoria_eligible_for_month(start_date, weeks_iso)


def is_employee_leadership_for_month(emp, weeks_iso: list[str]) -> bool:
    if int(emp.get("is_leadership", 0) or 0) != 1:
        return False
    start_date = str(emp.get("leadership_start_date", "") or "")
    return _has_role_start_date(start_date) and is_leadership_eligible_for_month(start_date, weeks_iso)


def should_skip_weekly_for_leadership_month(emp, weeks_iso: list[str]) -> bool:
    if int(emp.get("is_leadership", 0) or 0) != 1:
        return False

    start_date = str(emp.get("leadership_start_date", "") or "")
    if not _has_role_start_date(start_date):
        return True

    return is_leadership_eligible_for_month(start_date, weeks_iso)


def is_employee_valid_for_period(emp, weeks_iso: list[str]) -> bool:
    employee_weeks = eligible_weeks_for_valid_employee(
        emp.get("hire_date", ""),
        weeks_iso,
        emp.get("termination_date", ""),
    )
    if not employee_weeks:
        return False

    if int(emp.get("is_leadership", 0) or 0) == 1:
        return is_employee_leadership_for_month(emp, weeks_iso)

    return True


def tenure_bonus(hire_date_iso: str, reference_date: date) -> tuple[int, float]:
    years = years_in_company(hire_date_iso, reference_date)
    return years, float(years) * float(TENURE_BONUS_PER_YEAR)


def standard_monthly_base_value() -> float:
    return float(sum(float(cap) for *_rest, cap in WEEKLY_CRITERIA))


def week_money_preview(pcts: dict, week_start=None) -> pd.DataFrame:
    rows = []
    total = 0.0

    competencia = None
    if week_start is not None:
        if isinstance(week_start, str):
            week_start = datetime.strptime(week_start, "%Y-%m-%d").date()
        competencia = competencia_from_week_start(week_start)

    for key, label, weekly_value, monthly_cap in WEEKLY_CRITERIA:
        pct = float(pcts.get(key, 0) or 0)
        mult = band_multiplier(pct)

        if competencia:
            value_base = monthly_cap_to_week_value(float(monthly_cap), competencia)
        else:
            value_base = float(weekly_value)  # fallback

        pay = float(value_base) * mult
        total += pay

        if key == "produtividade":
            label = "Produtividade / Eficiência"

        rows.append({
            "Quesito": label,
            "Resultado (%)": pct_br(pct, 1),
            "Faixa paga": band_label(mult),
            "Valor semana": brl(float(value_base)),
            "Pagamento": brl(float(pay)),
        })

    df = pd.DataFrame(rows)
    df.loc[len(df)] = {
        "Quesito": "TOTAL",
        "Resultado (%)": "",
        "Faixa paga": "",
        "Valor semana": "",
        "Pagamento": brl(total),
    }
    return df


def monitoria_money_preview(pcts: dict) -> pd.DataFrame:
    rows = []
    total = 0.0
    for key, label, monthly_value, _obs in MONITOR_MONTHLY_CRITERIA:
        pct = float(pcts.get(key, 0) or 0)
        mult = band_multiplier(pct)
        pay = float(monthly_value) * mult
        total += pay
        rows.append({
            "Critério (Monitoria)": label,
            "Resultado (%)": pct_br(pct, 1),
            "Faixa paga": band_label(mult),
            "Valor (mês)": brl(float(monthly_value)),
            "Pagamento": brl(float(pay)),
        })
    df = pd.DataFrame(rows)
    df.loc[len(df)] = {"Critério (Monitoria)": "TOTAL MONITORIA", "Resultado (%)": "", "Faixa paga": "", "Valor (mês)": "", "Pagamento": brl(total)}
    return df


def format_report_display_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    pct_cols = [c for c in out.columns if "(%)" in str(c)]
    for col in pct_cols:
        out[col] = out[col].map(lambda v: pct_br(v, 1) if str(v).strip() not in {"", "-"} else v)
    return out


def build_employee_period_summary(
    month: str,
    summary_row: dict | None,
    eligible_weeks: list[str],
    weekly_rows_df: pd.DataFrame | None,
) -> dict:
    summary_row = summary_row or {}
    year, month_num = str(month or "").split("-")

    evaluated_weeks = 0
    if weekly_rows_df is not None and not weekly_rows_df.empty and "week_start" in weekly_rows_df.columns:
        evaluated_weeks = int(weekly_rows_df["week_start"].astype(str).nunique())

    prod_avg = summary_row.get("Prod/Efic média (%)", "-")
    if isinstance(prod_avg, (int, float)):
        prod_avg = pct_br(prod_avg, 1)

    return {
        "Período": month_label_to_br(month),
        "Semanas elegíveis": int(len(eligible_weeks or [])),
        "Semanas avaliadas": evaluated_weeks,
        "Erros (qtd)": int(summary_row.get("Erros (qtd)", 0) or 0),
        "Prod/Efic média": str(prod_avg),
        "Total Base (mês)": str(summary_row.get("Total Base (mês)", brl(0.0))),
        "Monitoria (mês)": str(summary_row.get("Monitoria (mês)", brl(0.0))),
        "Adicional Tempo (mês)": str(summary_row.get("Adicional Tempo (mês)", brl(0.0))),
        "Total Geral (mês)": str(summary_row.get("Total Geral (mês)", brl(0.0))),
    }


def _get_monitor_justs_from_row(mrow: dict) -> dict:
    """
    Prioridade:
    1) Colunas *_just (se existirem)
    2) Fallback: notes (bloco JUSTIFICATIVAS (MONITORIA))
    """
    out = {
        "Acompanhamento de metas": "",
        "Organização do fluxo": "",
        "Suporte à equipe": "",
        "Disciplina operacional": "",
    }
    if not mrow:
        return out

    col_map = [
        ("Acompanhamento de metas", "acomp_metas_just"),
        ("Organização do fluxo", "org_fluxo_just"),
        ("Suporte à equipe", "suporte_equipe_just"),
        ("Disciplina operacional", "disciplina_oper_just"),
    ]
    has_cols = any(col in mrow for _, col in col_map)
    if has_cols:
        for label, col in col_map:
            out[label] = str(mrow.get(col, "") or "").strip()
        return out

    notes = str(mrow.get("notes", "") or "")
    marker = "JUSTIFICATIVAS (MONITORIA)"
    idx = notes.find(marker)
    if idx == -1:
        return out

    block = notes[idx:].splitlines()
    for line in block:
        line = line.strip()
        if line.startswith("- "):
            try:
                k, v = line[2:].split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                if "meta" in k:
                    out["Acompanhamento de metas"] = v
                elif "flux" in k:
                    out["Organização do fluxo"] = v
                elif "suporte" in k:
                    out["Suporte à equipe"] = v
                elif "disciplina" in k:
                    out["Disciplina operacional"] = v
            except Exception:
                continue
    return out


def parse_justificativas_from_notes(notes: str) -> dict:
    out = {
        "Assiduidade": "",
        "Qualidade": "",
        "Taxa de Erros": "",
        "Produtividade/Eficiência": "",
        "Comportamento": "",
    }
    if not notes:
        return out

    text = str(notes)
    marker = "JUSTIFICATIVAS (SEMANA)"
    idx = text.find(marker)
    if idx == -1:
        return out

    block = text[idx:].splitlines()
    for line in block:
        line = line.strip()
        if line.startswith("- "):
            try:
                k, v = line[2:].split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                if k.startswith("produtividade"):
                    out["Produtividade/Eficiência"] = v
                elif k.startswith("taxa"):
                    out["Taxa de Erros"] = v
                elif k.startswith("assid"):
                    out["Assiduidade"] = v
                elif k.startswith("qual"):
                    out["Qualidade"] = v
                elif k.startswith("comp"):
                    out["Comportamento"] = v
            except Exception:
                continue
    return out


def _get_weekly_justs_from_row(row: dict) -> dict:
    """
    Prioridade:
    1) Colunas *_just (se existirem)
    2) Fallback: notes
    """
    keys = [
        ("Assiduidade", "assiduidade_just"),
        ("Qualidade", "qualidade_just"),
        ("Taxa de Erros", "taxa_erros_just"),
        ("Produtividade/Eficiência", "produtividade_just"),
        ("Comportamento", "comportamento_just"),
    ]
    out = {}
    has_cols = any(col in row for _, col in keys)
    if has_cols:
        for label, col in keys:
            out[label] = str(row.get(col, "") or "").strip()
        return out

    return parse_justificativas_from_notes(str(row.get("notes", "") or ""))


def _clean_week_start_sql(alias: str = "w") -> str:
    col = f"{alias}.week_start" if alias else "week_start"
    return f"REPLACE(REPLACE(TRIM({col}), char(13), ''), char(10), '')"


def fetch_weekly_evaluations_for_weeks(weeks_iso: list[str], employee_ids: list[int] | None = None) -> pd.DataFrame:
    if not weeks_iso:
        return pd.DataFrame()
    if employee_ids is not None and not employee_ids:
        return pd.DataFrame()

    week_params = [str(w).strip() for w in weeks_iso]
    emp_clause = ""
    params = list(week_params)

    if employee_ids is not None:
        emp_clause = f"AND employee_id IN ({','.join(['?'] * len(employee_ids))})"
        params.extend([int(eid) for eid in employee_ids])

    return fetch_df(
        f"""
        WITH normalized AS (
            SELECT
                w.*,
                {_clean_week_start_sql("w")} AS clean_week_start
            FROM weekly_evaluations w
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY employee_id, clean_week_start
                    ORDER BY created_at DESC, id DESC
                ) AS rn
            FROM normalized
            WHERE clean_week_start IN ({",".join(["?"] * len(week_params))})
              {emp_clause}
        )
        SELECT
            id,
            employee_id,
            clean_week_start AS week_start,
            evaluator,
            notes,
            assiduidade_pct,
            qualidade_pct,
            taxa_erros_pct,
            produtividade_pct,
            comportamento_pct,
            efficiency_pct,
            items_count,
            created_at,
            assiduidade_just,
            qualidade_just,
            taxa_erros_just,
            produtividade_just,
            comportamento_just
        FROM ranked
        WHERE rn = 1
        """,
        tuple(params),
    )


def build_closing_check_tables(month: str, weeks_iso: list[str]) -> dict:
    month = normalize_month_label(month)
    weeks_iso = [str(w).strip() for w in weeks_iso]
    empty = pd.DataFrame()

    if not weeks_iso:
        return {
            "summary": {"expected": 0, "done": 0, "issues": 0},
            "missing_weekly": empty,
            "duplicate_weekly": empty,
            "bad_week_dates": empty,
            "missing_weekly_justs": empty,
            "missing_hire_dates": empty,
            "missing_monitor_start_dates": empty,
            "missing_leadership_start_dates": empty,
            "pre_hire_weekly": empty,
            "leadership_weekly": empty,
            "missing_monitoria": empty,
            "missing_monitoria_justs": empty,
        }

    employees = fetch_df(
        f"""
        SELECT DISTINCT
            e.id,
            e.name,
            e.sector,
            e.role,
            e.hire_date,
            e.monitor_start_date,
            e.leadership_start_date,
            e.termination_date,
            e.is_monitor,
            e.active,
            e.deactivated_at,
            COALESCE(e.is_leadership, 0) AS is_leadership
        FROM employees e
        LEFT JOIN weekly_evaluations w
          ON w.employee_id = e.id
         AND {_clean_week_start_sql("w")} IN ({",".join(["?"] * len(weeks_iso))})
        LEFT JOIN weekly_errors er
          ON er.employee_id = e.id
         AND {_clean_week_start_sql("er")} IN ({",".join(["?"] * len(weeks_iso))})
        LEFT JOIN monitor_monthly_evaluations m
          ON m.employee_id = e.id
         AND TRIM(m.month) = ?
        ORDER BY e.active DESC, e.sector, e.role, e.name
        """,
        tuple(weeks_iso + weeks_iso + [month]),
    )

    if employees.empty or not weeks_iso:
        return {
            "summary": {"expected": 0, "done": 0, "issues": 0},
            "missing_weekly": empty,
            "duplicate_weekly": empty,
            "bad_week_dates": empty,
            "missing_weekly_justs": empty,
            "missing_hire_dates": empty,
            "missing_monitor_start_dates": empty,
            "missing_leadership_start_dates": empty,
            "pre_hire_weekly": empty,
            "leadership_weekly": empty,
            "missing_monitoria": empty,
            "missing_monitoria_justs": empty,
        }

    clean_expr = _clean_week_start_sql("w")
    week_placeholders = ",".join(["?"] * len(weeks_iso))

    present = fetch_df(
        f"""
        SELECT employee_id, {clean_expr} AS week_start, COUNT(*) AS registros
        FROM weekly_evaluations w
        WHERE {clean_expr} IN ({week_placeholders})
        GROUP BY employee_id, {clean_expr}
        """,
        tuple(weeks_iso),
    )

    active_ids = set(employees["id"].astype(int).tolist())
    present_pairs = {
        (int(r["employee_id"]), str(r["week_start"]))
        for _, r in present.iterrows()
        if int(r["employee_id"]) in active_ids and int(r["registros"]) > 0
    } if not present.empty else set()

    expected_pairs = set()
    missing_rows = []
    for _, emp in employees.iterrows():
        if not is_employee_valid_for_period(emp, weeks_iso):
            continue
        if should_skip_weekly_for_leadership_month(emp, weeks_iso):
            continue
        emp_weeks = eligible_weeks_for_valid_employee(
            emp.get("hire_date", ""),
            weeks_iso,
            emp.get("termination_date", ""),
        )
        for ws in emp_weeks:
            expected_pairs.add((int(emp["id"]), ws))
            if (int(emp["id"]), ws) not in present_pairs:
                missing_rows.append({
                    "Funcionário": emp["name"],
                    "Setor": emp["sector"],
                    "Função": emp["role"],
                    "Semana": week_label(datetime.strptime(ws, "%Y-%m-%d").date()),
                })
    missing_weekly = pd.DataFrame(missing_rows)

    pre_hire_rows = []
    for _, emp in employees.iterrows():
        if not is_employee_valid_for_period(emp, weeks_iso):
            continue
        if should_skip_weekly_for_leadership_month(emp, weeks_iso):
            continue
        hire_date = parse_hire_date(emp.get("hire_date", ""))
        if hire_date is None:
            continue

        for emp_id, ws in sorted(present_pairs):
            if emp_id != int(emp["id"]):
                continue
            if is_week_after_hire(emp.get("hire_date", ""), ws):
                continue
            pre_hire_rows.append({
                "Funcionário": emp["name"],
                "Setor": emp["sector"],
                "Função": emp["role"],
                "Contratação": hire_date.strftime("%d/%m/%Y"),
                "Semana": week_label(datetime.strptime(ws, "%Y-%m-%d").date()),
            })
    pre_hire_weekly = pd.DataFrame(pre_hire_rows)

    duplicate_weekly = fetch_df(
        f"""
        SELECT
            e.name AS Funcionário,
            e.sector AS Setor,
            e.role AS Função,
            {clean_expr} AS Semana,
            COUNT(*) AS Registros,
            GROUP_CONCAT(w.id, ', ') AS IDs
        FROM weekly_evaluations w
        JOIN employees e ON e.id = w.employee_id
        WHERE {clean_expr} IN ({week_placeholders})
          AND COALESCE(e.is_leadership, 0) = 0
        GROUP BY w.employee_id, {clean_expr}
        HAVING COUNT(*) > 1
        ORDER BY e.name, Semana
        """,
        tuple(weeks_iso),
    )

    bad_week_dates = fetch_df(
        f"""
        SELECT
            e.name AS Funcionário,
            w.id AS ID,
            quote(w.week_start) AS Data_gravada,
            {clean_expr} AS Data_corrigida
        FROM weekly_evaluations w
        JOIN employees e ON e.id = w.employee_id
        WHERE w.week_start <> {clean_expr}
        ORDER BY e.name, w.id
        """
    )

    leadership_weekly = fetch_df(
        f"""
        SELECT
            e.name AS Funcionário,
            e.sector AS Setor,
            e.role AS Função,
            {clean_expr} AS Semana,
            w.id AS ID
        FROM weekly_evaluations w
        JOIN employees e ON e.id = w.employee_id
        WHERE COALESCE(e.is_leadership, 0) = 1
          AND {clean_expr} IN ({week_placeholders})
        ORDER BY e.name, Semana
        """,
        tuple(weeks_iso),
    )

    weekly_justs = fetch_df(
        f"""
        SELECT
            w.employee_id AS employee_id,
            e.name AS Funcionário,
            {clean_expr} AS Semana,
            COALESCE(w.assiduidade_just, '') AS assiduidade_just,
            COALESCE(w.qualidade_just, '') AS qualidade_just,
            COALESCE(w.taxa_erros_just, '') AS taxa_erros_just,
            COALESCE(w.produtividade_just, '') AS produtividade_just,
            COALESCE(w.comportamento_just, '') AS comportamento_just
        FROM weekly_evaluations w
        JOIN employees e ON e.id = w.employee_id
        WHERE {clean_expr} IN ({week_placeholders})
          AND COALESCE(e.is_leadership, 0) = 0
        """,
        tuple(weeks_iso),
    )

    just_labels = {
        "assiduidade_just": "Assiduidade",
        "qualidade_just": "Qualidade",
        "taxa_erros_just": "Taxa de Erros",
        "produtividade_just": "Produtividade/Eficiência",
        "comportamento_just": "Comportamento",
    }
    employee_date_map = {
        int(r["id"]): (
            str(r.get("hire_date", "") or ""),
            str(r.get("termination_date", "") or ""),
        )
        for _, r in employees.iterrows()
    }
    missing_just_rows = []
    for _, row in weekly_justs.iterrows():
        hire_date_iso, termination_date_iso = employee_date_map.get(int(row["employee_id"]), ("", ""))
        if str(row["Semana"]) not in eligible_weeks_for_valid_employee(hire_date_iso, weeks_iso, termination_date_iso):
            continue

        missing = [label for col, label in just_labels.items() if not str(row.get(col, "") or "").strip()]
        if missing:
            missing_just_rows.append({
                "Funcionário": row["Funcionário"],
                "Semana": week_label(datetime.strptime(str(row["Semana"]), "%Y-%m-%d").date()),
                "Justificativas faltantes": ", ".join(missing),
            })
    missing_weekly_justs = pd.DataFrame(missing_just_rows)

    missing_hire_dates = employees[
        (employees["active"].fillna(1).astype(int) == 1)
        & (employees["hire_date"].fillna("").astype(str).str.strip() == "")
    ][["name", "sector", "role"]].copy()
    if not missing_hire_dates.empty:
        missing_hire_dates = missing_hire_dates.rename(columns={
            "name": "Funcionário",
            "sector": "Setor",
            "role": "Função",
        })

    missing_monitor_start_dates = employees[
        (employees["active"].fillna(1).astype(int) == 1)
        & (employees["is_monitor"].fillna(0).astype(int) == 1)
        & (employees["is_leadership"].fillna(0).astype(int) == 0)
        & (employees["monitor_start_date"].fillna("").astype(str).str.strip() == "")
    ][["name", "sector", "role"]].copy()
    if not missing_monitor_start_dates.empty:
        missing_monitor_start_dates = missing_monitor_start_dates.rename(columns={
            "name": "Funcionário",
            "sector": "Setor",
            "role": "Função",
        })

    missing_leadership_start_dates = employees[
        (employees["active"].fillna(1).astype(int) == 1)
        & (employees["is_leadership"].fillna(0).astype(int) == 1)
        & (employees["leadership_start_date"].fillna("").astype(str).str.strip() == "")
    ][["name", "sector", "role"]].copy()
    if not missing_leadership_start_dates.empty:
        missing_leadership_start_dates = missing_leadership_start_dates.rename(columns={
            "name": "Funcionário",
            "sector": "Setor",
            "role": "Função",
        })

    present_monitoria = fetch_df(
        "SELECT DISTINCT employee_id FROM monitor_monthly_evaluations WHERE TRIM(month) = ?",
        (month,),
    )
    present_monitor_ids = (
        set(present_monitoria["employee_id"].fillna(0).astype(int).tolist())
        if not present_monitoria.empty
        else set()
    )
    missing_monitor_rows = []
    for _, emp in employees.iterrows():
        if not is_employee_valid_for_period(emp, weeks_iso):
            continue
        if not is_employee_monitor_for_month(emp, weeks_iso):
            continue
        if int(emp["id"]) in present_monitor_ids:
            continue
        missing_monitor_rows.append({
            "Funcionário": emp["name"],
            "Setor": emp["sector"],
            "Função": emp["role"],
            "Monitor desde": date_iso_to_br(emp.get("monitor_start_date", "")),
        })
    missing_monitoria = pd.DataFrame(missing_monitor_rows)

    monitor_justs = fetch_df(
        """
        SELECT
            e.id AS employee_id,
            e.name AS Funcionário,
            e.hire_date,
            e.monitor_start_date,
            e.leadership_start_date,
            e.termination_date,
            e.is_monitor,
            COALESCE(e.is_leadership, 0) AS is_leadership,
            COALESCE(m.acomp_metas_just, '') AS acomp_metas_just,
            COALESCE(m.org_fluxo_just, '') AS org_fluxo_just,
            COALESCE(m.suporte_equipe_just, '') AS suporte_equipe_just,
            COALESCE(m.disciplina_oper_just, '') AS disciplina_oper_just
        FROM monitor_monthly_evaluations m
        JOIN employees e ON e.id = m.employee_id
        WHERE TRIM(m.month) = ?
        ORDER BY e.name
        """,
        (month,),
    )
    monitor_labels = {
        "acomp_metas_just": "Acompanhamento de metas",
        "org_fluxo_just": "Organização do fluxo",
        "suporte_equipe_just": "Suporte à equipe",
        "disciplina_oper_just": "Disciplina operacional",
    }
    missing_monitor_just_rows = []
    for _, row in monitor_justs.iterrows():
        if not is_employee_valid_for_period(row, weeks_iso):
            continue
        if not is_employee_monitor_for_month(row, weeks_iso):
            continue
        missing = [label for col, label in monitor_labels.items() if not str(row.get(col, "") or "").strip()]
        if missing:
            missing_monitor_just_rows.append({
                "Funcionário": row["Funcionário"],
                "Justificativas faltantes": ", ".join(missing),
            })
    missing_monitoria_justs = pd.DataFrame(missing_monitor_just_rows)

    expected = len(expected_pairs)
    done = len(present_pairs & expected_pairs)
    issues = (
        len(missing_weekly)
        + len(duplicate_weekly)
        + len(bad_week_dates)
        + len(missing_weekly_justs)
        + len(missing_hire_dates)
        + len(missing_monitor_start_dates)
        + len(missing_leadership_start_dates)
        + len(pre_hire_weekly)
        + len(leadership_weekly)
        + len(missing_monitoria)
        + len(missing_monitoria_justs)
    )

    return {
        "summary": {"expected": expected, "done": done, "issues": issues},
        "missing_weekly": missing_weekly,
        "duplicate_weekly": duplicate_weekly,
        "bad_week_dates": bad_week_dates,
        "missing_weekly_justs": missing_weekly_justs,
        "missing_hire_dates": missing_hire_dates,
        "missing_monitor_start_dates": missing_monitor_start_dates,
        "missing_leadership_start_dates": missing_leadership_start_dates,
        "pre_hire_weekly": pre_hire_weekly,
        "leadership_weekly": leadership_weekly,
        "missing_monitoria": missing_monitoria,
        "missing_monitoria_justs": missing_monitoria_justs,
    }


def render_closing_check(month: str, weeks_iso: list[str]):
    checks = build_closing_check_tables(month, weeks_iso)
    summary = checks["summary"]

    with st.expander("Checklist de fechamento", expanded=summary["issues"] > 0):
        m1, m2, m3 = st.columns(3, gap="medium")
        m1.metric("Avaliações esperadas", int(summary["expected"]))
        m2.metric("Avaliações encontradas", int(summary["done"]))
        m3.metric("Pendências", int(summary["issues"]))

        if summary["issues"] == 0:
            st.success("Fechamento sem pendências críticas para as semanas, justificativas e monitoria.")
            return

        st.warning("Revise as pendências antes de gerar o PDF final.")

        sections = [
            ("Avaliações semanais faltantes", checks["missing_weekly"]),
            ("Avaliações semanais duplicadas", checks["duplicate_weekly"]),
            ("Datas semanais com sujeira no banco", checks["bad_week_dates"]),
            ("Justificativas semanais faltantes", checks["missing_weekly_justs"]),
            ("Datas de contratação faltantes", checks["missing_hire_dates"]),
            ("Datas de início como monitor faltantes", checks["missing_monitor_start_dates"]),
            ("Datas de início em coordenação/supervisão faltantes", checks["missing_leadership_start_dates"]),
            ("Avaliações antes da contratação", checks["pre_hire_weekly"]),
            ("Avaliações registradas para coordenação/supervisão", checks["leadership_weekly"]),
            ("Monitoria mensal faltante", checks["missing_monitoria"]),
            ("Justificativas de monitoria faltantes", checks["missing_monitoria_justs"]),
        ]

        for title, table in sections:
            if table is not None and not table.empty:
                st.markdown(f"#### {title}")
                st.dataframe(table, width="stretch", hide_index=True)


# -----------------------------
# Data builders
# -----------------------------
def build_month_df(month: str) -> tuple[pd.DataFrame, list[str]]:
    """
    Monta dataframe consolidado do mês (tela).
    Inclui _employee_id para joins corretos no anexo RH.
    """
    month = normalize_month_label(month)
    year, month_num = map(int, month.split("-"))
    weeks = weeks_for_competencia(year, month_num)
    weeks_iso = [w.isoformat() for w in weeks]
    if not weeks_iso:
        return pd.DataFrame(), weeks_iso
    reference_date = week_end_friday(max(weeks)) if weeks else date(year, month_num, 1)

    employees = fetch_df(
        f"""
        SELECT DISTINCT
            e.id,
            e.name,
            e.sector,
            e.role,
            e.hire_date,
            e.monitor_start_date,
            e.leadership_start_date,
            e.termination_date,
            e.is_monitor,
            e.active,
            e.deactivated_at,
            COALESCE(e.is_leadership, 0) AS is_leadership
        FROM employees e
        LEFT JOIN weekly_evaluations w
          ON w.employee_id = e.id
         AND {_clean_week_start_sql("w")} IN ({",".join(["?"] * len(weeks_iso))})
        LEFT JOIN weekly_errors er
          ON er.employee_id = e.id
         AND {_clean_week_start_sql("er")} IN ({",".join(["?"] * len(weeks_iso))})
        LEFT JOIN monitor_monthly_evaluations m
          ON m.employee_id = e.id
         AND TRIM(m.month) = ?
        ORDER BY e.active DESC, e.sector, e.role, e.name
        """,
        tuple(weeks_iso + weeks_iso + [month]),
    )
    if employees.empty or not weeks_iso:
        return pd.DataFrame(), weeks_iso

    weekly = fetch_weekly_evaluations_for_weeks(weeks_iso)

    errors_rows = fetch_df(
        f"""
        SELECT employee_id, {_clean_week_start_sql("")} AS week_start, qty
        FROM weekly_errors
        WHERE {_clean_week_start_sql("")} IN ({",".join(["?"] * len(weeks_iso))})
        """,
        tuple(weeks_iso)
    )

    monitor_rows = fetch_df("""
        SELECT *
        FROM monitor_monthly_evaluations
        WHERE month = ?
    """, (month,))
    monitor_map = {}
    if not monitor_rows.empty:
        for _, r in monitor_rows.iterrows():
            monitor_map[int(r["employee_id"])] = r.to_dict()

    rows = []
    for _, emp in employees.iterrows():
        if not is_employee_valid_for_period(emp, weeks_iso):
            continue

        emp_id = int(emp["id"])
        is_monitor = is_employee_monitor_for_month(emp, weeks_iso)
        is_leadership = is_employee_leadership_for_month(emp, weeks_iso)
        emp_eligible_weeks = eligible_weeks_for_valid_employee(
            emp.get("hire_date", ""),
            weeks_iso,
            emp.get("termination_date", ""),
        )

        if is_leadership:
            emp_weeks = pd.DataFrame()
        elif not weekly.empty:
            emp_weeks = weekly[
                (weekly["employee_id"] == emp_id)
                & (weekly["week_start"].astype(str).isin(emp_eligible_weeks))
            ]
        else:
            emp_weeks = weekly

        totals = {key: 0.0 for (key, _label, _weekly_value, _cap) in WEEKLY_CRITERIA}
        prod_vals = []

        for _, wrow in emp_weeks.iterrows():
            pay = calculate_weekly_payment(wrow)  # já por faixa
            for k, v in pay.items():
                totals[k] += float(v)
            prod_vals.append(float(wrow.get("produtividade_pct", 0) or 0))

        # caps mensais
        for (key, _label, _weekly_value, cap) in WEEKLY_CRITERIA:
            totals[key] = min(float(totals.get(key, 0.0)), float(cap))

        total_base = standard_monthly_base_value() if is_leadership else sum(totals.values())
        prod_avg = (sum(prod_vals) / len(prod_vals)) if prod_vals else 0.0

        monitor_bonus = 0.0
        if is_monitor:
            mrow = monitor_map.get(emp_id)
            monitor_bonus = calc_monitoria_bonus_from_row(mrow) if mrow else 0.0

        if is_leadership:
            errors_qtd = 0
        elif not errors_rows.empty:
            emp_errors = errors_rows[
                (errors_rows["employee_id"] == emp_id)
                & (errors_rows["week_start"].astype(str).isin(emp_eligible_weeks))
            ]
            errors_qtd = int(emp_errors["qty"].fillna(0).astype(int).sum())
        else:
            errors_qtd = 0

        company_years, company_bonus = tenure_bonus(emp.get("hire_date", ""), reference_date)
        total_geral = float(total_base) + float(monitor_bonus) + float(company_bonus)

        row_out = {
            "_employee_id": emp_id,
            "_hire_date": str(emp.get("hire_date", "") or ""),
            "_monitor_start_date": str(emp.get("monitor_start_date", "") or ""),
            "_leadership_start_date": str(emp.get("leadership_start_date", "") or ""),
            "_termination_date": str(emp.get("termination_date", "") or ""),
            "_is_leadership": 1 if is_leadership else 0,
            "_active": int(emp.get("active", 1) or 0),
            "Grupo": "Coordenação/Supervisão" if is_leadership else "Colaboradores",
            "Funcionário": emp["name"],
            "Setor": emp["sector"],
            "Função": emp["role"],
            "Status": "ATIVO" if int(emp.get("active", 1) or 0) == 1 else "DESATIVADO",

            "Monitoria (mês)": brl(float(monitor_bonus)),
            "Tempo Empresa (anos)": int(company_years),
            "Adicional Tempo (mês)": brl(float(company_bonus)),

            # tela (não vai pro PDF executivo)
            "Erros (qtd)": errors_qtd,
            "Prod/Efic média (%)": round(prod_avg, 1),
        }

        for (key, label, _weekly_value, _cap) in WEEKLY_CRITERIA:
            if key == "produtividade":
                label = "Produtividade / Eficiência"
            row_out[label] = "-" if is_leadership else brl(float(totals[key]))

        row_out["Total Base (mês)"] = brl(float(total_base))
        row_out["Total Geral (mês)"] = brl(float(total_geral))
        rows.append(row_out)

    df = pd.DataFrame(rows)
    return df, weeks_iso


def _avg_or_none(values) -> float | None:
    clean = []
    for value in values:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric == numeric:
            clean.append(numeric)
    if not clean:
        return None
    return round(sum(clean) / len(clean), 1)


def _pct_or_dash(value, decimals: int = 1) -> str:
    if value is None:
        return "-"
    return pct_br(value, decimals)


def _attention_status(
    is_leadership: bool,
    avg_pct: float | None,
    errors_qtd: int,
    missing_weeks: int,
    missing_justs: int,
    criterion_summary: dict | None = None,
) -> str:
    if is_leadership:
        return "Acompanhamento mensal"
    if missing_weeks > 0:
        return "Regularizar"
    if avg_pct is None:
        return "Sem avaliação"
    criterion_values = [
        pct
        for _label, pct in _ordered_criterion_scores(criterion_summary or {})
        if pct is not None
    ]
    min_criterion_pct = min(criterion_values) if criterion_values else None
    if avg_pct < 71 or errors_qtd >= 3 or (min_criterion_pct is not None and min_criterion_pct < 71):
        return "Prioritário"
    if (
        avg_pct < 81
        or errors_qtd > 0
        or missing_justs > 0
        or (min_criterion_pct is not None and min_criterion_pct < 91)
    ):
        return "Acompanhar"
    return "Manter"


def _followup_frequency(indicator: str) -> str:
    indicator = str(indicator or "").strip()
    if indicator in {"Regularizar", "Prioritário"}:
        return "Semanal"
    if indicator == "Acompanhar":
        return "Quinzenal"
    return "Mensal"


def _criterion_action(label: str, pct: float | None, errors_qtd: int = 0) -> str:
    if pct is None:
        return "sem média registrada para análise"

    if label == "Assiduidade":
        if pct < 71:
            return "corrigir faltas/atrasos e combinar rotina de aviso antes do turno"
        if pct < 81:
            return "reduzir atrasos pontuais e reforçar previsibilidade da escala"
        if pct < 91:
            return "acompanhar pontualidade para voltar acima de 90%"
        return "manter presença e pontualidade"

    if label == "Qualidade":
        if pct < 71:
            return "refazer padrão de conferência e revisar causas de retrabalho"
        if pct < 81:
            return "reforçar atenção nos pontos de conferência antes da liberação"
        if pct < 91:
            return "acompanhar pequenos desvios de qualidade na rotina"
        return "manter padrão de entrega"

    if label == "Taxa de Erros":
        if pct < 71:
            return "mapear tipos de erro e aplicar dupla checagem nas etapas críticas"
        if pct < 81:
            return "reduzir reincidência com checklist antes de finalizar pedidos"
        if pct < 91 or errors_qtd > 0:
            return "acompanhar ocorrências e validar se os erros foram pontuais"
        return "manter controle sem reincidência"

    if label == "Produtividade / Eficiência":
        if pct < 71:
            return "identificar gargalos de ritmo, meta e organização da bancada"
        if pct < 81:
            return "ajustar cadência de trabalho e remover travas do processo"
        if pct < 91:
            return "buscar estabilidade acima de 90% sem perda de qualidade"
        return "manter ritmo e consistência"

    if label == "Comportamento":
        if pct < 71:
            return "alinhar postura, comunicação e cumprimento de combinados"
        if pct < 81:
            return "reforçar colaboração, respeito aos fluxos e resposta a orientações"
        if pct < 91:
            return "acompanhar postura no time e aderência aos combinados"
        return "manter postura colaborativa"

    return "acompanhar evolução do quesito"


def _ordered_criterion_scores(criterion_summary: dict) -> list[tuple[str, float | None]]:
    order = [
        "Assiduidade",
        "Qualidade",
        "Taxa de Erros",
        "Produtividade / Eficiência",
        "Comportamento",
    ]
    return [(label, criterion_summary.get(label)) for label in order]


def _focus_text_from_scores(
    is_leadership: bool,
    criterion_summary: dict,
    avg_pct: float | None,
    errors_qtd: int,
    missing_weeks: int,
    missing_justs: int,
) -> str:
    if is_leadership:
        return "Metas do setor, gargalos operacionais e apoio esperado ao time."
    if missing_weeks > 0:
        return f"Regularizar {missing_weeks} semana(s) sem avaliação antes de fechar o feedback."
    if missing_justs > 0:
        return f"Completar {missing_justs} justificativa(s) para deixar o histórico rastreável."

    scored = [
        (label, pct)
        for label, pct in _ordered_criterion_scores(criterion_summary)
        if pct is not None
    ]
    if not scored:
        return "Registrar avaliações para definir foco com base nas médias."

    scored = sorted(scored, key=lambda item: item[1])
    selected = [item for item in scored if item[1] < 91][:2] or scored[:1]
    parts = [
        f"{label} ({pct_br(pct, 1)}): {_criterion_action(label, pct, errors_qtd)}"
        for label, pct in selected
    ]
    return "; ".join(parts)


def _feedback_text(
    is_leadership: bool,
    indicator: str,
    focus_label: str,
    avg_pct: float | None,
    errors_qtd: int,
    missing_weeks: int,
    missing_justs: int,
    criterion_summary: dict | None = None,
) -> str:
    criterion_summary = criterion_summary or {}
    focus_detail = _focus_text_from_scores(
        is_leadership=is_leadership,
        criterion_summary=criterion_summary,
        avg_pct=avg_pct,
        errors_qtd=errors_qtd,
        missing_weeks=missing_weeks,
        missing_justs=missing_justs,
    )

    if is_leadership:
        return "Conduzir alinhamento de metas do setor, gargalos operacionais e suporte esperado da coordenação/supervisão."
    if missing_weeks > 0:
        return f"Regularizar {missing_weeks} semana(s) sem avaliação; depois validar se a média final confirma necessidade de plano de ação."
    if missing_justs > 0:
        return f"Completar {missing_justs} justificativa(s) antes da conversa para sustentar o feedback com evidências."
    if avg_pct is None:
        return "Registrar avaliação para iniciar acompanhamento."

    avg_text = pct_br(avg_pct, 1)
    if indicator == "Manter" and errors_qtd == 0:
        return f"Média geral {avg_text}. Reconhecer consistência, manter rotina atual e observar o menor quesito: {focus_detail}"
    if indicator == "Prioritário":
        return f"Média geral {avg_text}. Definir plano de ação semanal com responsável e prazo. Principal foco: {focus_detail}"
    if indicator == "Acompanhar":
        return f"Média geral {avg_text}. Fazer revisão quinzenal e combinar uma meta objetiva de recuperação. Foco: {focus_detail}"
    if focus_label and focus_label != "-":
        return f"Média geral {avg_text}. Revisar {focus_label} e registrar ação para a próxima revisão."
    return f"Média geral {avg_text}. Revisar desvios do período e combinar próximo acompanhamento."


def build_sector_followup_tables(month: str, sector_filter: str = "(Todos)") -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Monta uma visão unificada para feedback e acompanhamento por setor.
    Retorna: resumo por setor, acompanhamento por funcionário e semanas da competência.
    """
    month_df, weeks_iso = build_month_df(month)
    if month_df.empty:
        return pd.DataFrame(), pd.DataFrame(), weeks_iso

    selected_sector = str(sector_filter or "(Todos)").strip()
    work_df = month_df.copy()
    if selected_sector and selected_sector != "(Todos)":
        work_df = work_df[work_df["Setor"].astype(str) == selected_sector].copy()
    if work_df.empty:
        return pd.DataFrame(), pd.DataFrame(), weeks_iso

    employee_ids = work_df["_employee_id"].fillna(0).astype(int).tolist()
    weekly = fetch_weekly_evaluations_for_weeks(weeks_iso, employee_ids)
    if weekly is None or weekly.empty:
        weekly = pd.DataFrame()

    rows = []
    for _, emp in work_df.iterrows():
        emp_id = int(emp["_employee_id"])
        is_leadership = int(emp.get("_is_leadership", 0) or 0) == 1
        eligible_weeks = [] if is_leadership else eligible_weeks_for_valid_employee(
            emp.get("_hire_date", ""),
            weeks_iso,
            emp.get("_termination_date", ""),
        )

        if weekly.empty or is_leadership:
            emp_weeks = pd.DataFrame()
        else:
            emp_weeks = weekly[
                (weekly["employee_id"].astype(int) == emp_id)
                & (weekly["week_start"].astype(str).isin(eligible_weeks))
            ].copy()

        evaluated_weeks = int(emp_weeks["week_start"].astype(str).nunique()) if not emp_weeks.empty else 0
        expected_weeks = len(eligible_weeks)
        missing_weeks = max(0, expected_weeks - evaluated_weeks)
        coverage_pct = round((evaluated_weeks / expected_weeks) * 100, 1) if expected_weeks else None

        weekly_avgs = []
        criterion_avgs = {}
        missing_justs = 0
        if not emp_weeks.empty:
            for _, wrow in emp_weeks.iterrows():
                row_scores = []
                for key, label, _weekly_value, _cap in WEEKLY_CRITERIA:
                    display_label = "Produtividade / Eficiência" if key == "produtividade" else label
                    value = float(wrow.get(f"{key}_pct", 0) or 0)
                    row_scores.append(value)
                    criterion_avgs.setdefault(display_label, []).append(value)
                weekly_avgs.append(_avg_or_none(row_scores))

                justs = _get_weekly_justs_from_row(wrow)
                missing_justs += sum(1 for value in justs.values() if not str(value or "").strip())

        avg_pct = _avg_or_none(weekly_avgs)
        focus_label = "-"
        focus_pct = None
        criterion_summary = {}
        if criterion_avgs:
            criterion_summary = {
                label: _avg_or_none(values)
                for label, values in criterion_avgs.items()
            }
            valid_focus = {label: value for label, value in criterion_summary.items() if value is not None}
            if valid_focus:
                focus_label, focus_pct = min(valid_focus.items(), key=lambda item: item[1])

        errors_qtd = int(emp.get("Erros (qtd)", 0) or 0)
        indicator = _attention_status(
            is_leadership,
            avg_pct,
            errors_qtd,
            missing_weeks,
            missing_justs,
            criterion_summary=criterion_summary,
        )
        followup = _followup_frequency(indicator)
        feedback = _feedback_text(
            is_leadership=is_leadership,
            indicator=indicator,
            focus_label=focus_label,
            avg_pct=avg_pct,
            errors_qtd=errors_qtd,
            missing_weeks=missing_weeks,
            missing_justs=missing_justs,
            criterion_summary=criterion_summary,
        )
        pending_total = missing_weeks + missing_justs
        total_geral_float = brl_to_float(str(emp.get("Total Geral (mês)", brl(0.0))))

        rows.append({
            "_employee_id": emp_id,
            "_is_leadership": 1 if is_leadership else 0,
            "_avg_pct": avg_pct,
            "_coverage_pct": coverage_pct,
            "_expected_weeks": expected_weeks,
            "_evaluated_weeks": evaluated_weeks,
            "_missing_weeks": missing_weeks,
            "_missing_justs": missing_justs,
            "_errors_qtd": errors_qtd,
            "_pending_total": pending_total,
            "_total_geral_float": total_geral_float,
            "Setor": emp["Setor"],
            "Funcionário": emp["Funcionário"],
            "Função": emp["Função"],
            "Grupo": emp["Grupo"],
            "Status": emp["Status"],
            "Indicador": indicator,
            "Média geral (%)": _pct_or_dash(avg_pct, 1),
            "Assiduidade (%)": _pct_or_dash(criterion_summary.get("Assiduidade"), 1),
            "Qualidade (%)": _pct_or_dash(criterion_summary.get("Qualidade"), 1),
            "Taxa de Erros (%)": _pct_or_dash(criterion_summary.get("Taxa de Erros"), 1),
            "Prod/Efic (%)": _pct_or_dash(criterion_summary.get("Produtividade / Eficiência"), 1),
            "Comportamento (%)": _pct_or_dash(criterion_summary.get("Comportamento"), 1),
            "Cobertura avaliações": _pct_or_dash(coverage_pct, 1),
            "Semanas avaliadas/elegíveis": f"{evaluated_weeks}/{expected_weeks}" if expected_weeks else "-",
            "Erros (qtd)": errors_qtd,
            "Pendências": pending_total,
            "Foco do feedback": _focus_text_from_scores(
                is_leadership=is_leadership,
                criterion_summary=criterion_summary,
                avg_pct=avg_pct,
                errors_qtd=errors_qtd,
                missing_weeks=missing_weeks,
                missing_justs=missing_justs,
            ),
            "Acompanhamento": followup,
            "Feedback sugerido": feedback,
            "Total Geral (mês)": emp["Total Geral (mês)"],
        })

    employee_df = pd.DataFrame(rows)
    if employee_df.empty:
        return pd.DataFrame(), employee_df, weeks_iso

    summary_rows = []
    for sector, group in employee_df.groupby("Setor", dropna=False):
        expected = int(group["_expected_weeks"].sum())
        evaluated = int(group["_evaluated_weeks"].sum())
        coverage = round((evaluated / expected) * 100, 1) if expected else None
        avg_pct = _avg_or_none(group["_avg_pct"].dropna().tolist())
        priority_count = int(group["Indicador"].isin(["Regularizar", "Prioritário"]).sum())
        summary_rows.append({
            "_avg_pct": avg_pct,
            "_coverage_pct": coverage,
            "_expected_weeks": expected,
            "_evaluated_weeks": evaluated,
            "_pending_total": int(group["_pending_total"].sum()),
            "_total_geral_float": float(group["_total_geral_float"].sum()),
            "Setor": str(sector),
            "Funcionários": int(len(group)),
            "Colaboradores": int((group["_is_leadership"] == 0).sum()),
            "Coord./Sup.": int((group["_is_leadership"] == 1).sum()),
            "Média geral (%)": _pct_or_dash(avg_pct, 1),
            "Cobertura avaliações": _pct_or_dash(coverage, 1),
            "Erros (qtd)": int(group["_errors_qtd"].sum()),
            "Pendências": int(group["_pending_total"].sum()),
            "Prioritários": priority_count,
            "Total Geral (mês)": brl(float(group["_total_geral_float"].sum())),
        })

    summary_df = pd.DataFrame(summary_rows).sort_values("Setor").reset_index(drop=True)
    employee_df = employee_df.sort_values(
        ["Setor", "Indicador", "_avg_pct", "Funcionário"],
        na_position="last",
    ).reset_index(drop=True)
    return summary_df, employee_df, weeks_iso


def _drop_hidden_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    hidden = [col for col in df.columns if str(col).startswith("_")]
    return df.drop(columns=hidden)


# -----------------------------
# PDF: Anexo RH (resultados semanais %)
# -----------------------------
def build_weekly_pct_tables_for_pdf(weeks_iso: list[str], weekly_join_df: pd.DataFrame):
    styles = getSampleStyleSheet()
    H2 = ParagraphStyle("H2W", parent=styles["Heading2"], fontSize=11, leading=13, spaceBefore=6, spaceAfter=4)
    SMALL = ParagraphStyle("SW", parent=styles["BodyText"], fontSize=8.5, leading=10.5)

    flow = []
    if weekly_join_df is None or weekly_join_df.empty or "week_start" not in weekly_join_df.columns:
        return flow

    weekly_join_df = weekly_join_df.copy()
    if "name" not in weekly_join_df.columns:
        fallback_names = weekly_join_df["employee_id"].astype(str) if "employee_id" in weekly_join_df.columns else ""
        weekly_join_df["name"] = fallback_names

    weekly_join_df = weekly_join_df.sort_values(["week_start", "name"])

    for i, ws in enumerate(weeks_iso):
        wk = weekly_join_df[weekly_join_df["week_start"] == ws].copy()
        if wk.empty:
            continue

        ws_date = datetime.strptime(ws, "%Y-%m-%d").date()
        flow.append(Paragraph(f"Anexo RH — Resultados Semanais (%) • Semana {week_label(ws_date)}", H2))
        flow.append(Spacer(1, 2 * mm))

        data = [["Funcionário", "Assid%", "Qual%", "Erros%", "Prod%", "Comp%"]]
        for _, r in wk.iterrows():
            data.append([
                Paragraph(pdf_text(str(r["name"])), SMALL),
                f"{float(r.get('assiduidade_pct', 0) or 0):.0f}",
                f"{float(r.get('qualidade_pct', 0) or 0):.0f}",
                f"{float(r.get('taxa_erros_pct', 0) or 0):.0f}",
                f"{float(r.get('produtividade_pct', 0) or 0):.0f}",
                f"{float(r.get('comportamento_pct', 0) or 0):.0f}",
            ])

        col_widths = [110*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm]

        tbl = Table(data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
            ("FONTSIZE", (0, 1), (-1, -1), 8.2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        flow.append(tbl)
        flow.append(Spacer(1, 4 * mm))

        if i < len(weeks_iso) - 1:
            flow.append(PageBreak())

    return flow


# -----------------------------
# PDF executivo (paisagem)
# -----------------------------
def build_report_pdf_bytes_executivo(
    df_pdf: pd.DataFrame,
    month: str,
    coordinator_name: str,
    report_observation: str,
    weeks_iso: list[str],
    weekly_join_df: pd.DataFrame,
    include_weekly_appendix: bool = True,
    logo_path: str = "assets/logo.png",
) -> bytes:
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=9 * mm,
        bottomMargin=8 * mm,
        title=f"Relatório Mensal {month_label_to_br(month)}",
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleExec",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=18,
        textColor=colors.HexColor("#111827"),
        spaceAfter=2,
    )
    subtitle = ParagraphStyle(
        "SubExec",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#374151"),
        spaceAfter=6,
    )
    small = ParagraphStyle(
        "Small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#374151"),
    )
    small_bold = ParagraphStyle("SmallBold", parent=small, fontName="Helvetica-Bold")

    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    def draw_header_footer(canvas, doc_):
        canvas.saveState()
        w, h = landscape(A4)

        canvas.setFillColor(colors.HexColor("#111827"))
        canvas.rect(0, h - 8 * mm, w, 8 * mm, stroke=0, fill=1)

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(14 * mm, h - 6 * mm, f"Relatório Mensal • {month_label_to_br(month)}")

        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - 14 * mm, h - 6 * mm, f"Gerado em {generated_at}")

        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(14 * mm, 7 * mm, "Uso interno • Avaliação & Bonificação")
        canvas.drawRightString(w - 14 * mm, 7 * mm, f"Página {doc_.page}")

        canvas.restoreState()

    story = []

    # Logo
    try:
        logo = Image(logo_path, width=18 * mm, height=18 * mm)
        logo.hAlign = "LEFT"
        story.append(logo)
    except Exception:
        pass

    story.append(Paragraph("Relatório Mensal de Avaliação & Bonificação", title))
    story.append(Paragraph(f"Mês de referência: <b>{month_label_to_br(month)}</b>", subtitle))
    story.append(Spacer(1, 2 * mm))

    # --- PDF-friendly: remove Função (se existir), encurta cabeçalhos, reordena ---
    dfp = df_pdf.copy()
    for col in [
        "Função", "_employee_id", "_hire_date", "_monitor_start_date", "_leadership_start_date",
        "_termination_date", "_is_leadership", "Erros (qtd)", "Prod/Efic média (%)",
    ]:
        if col in dfp.columns:
            dfp = dfp.drop(columns=[col])

    rename_map = {
        "Grupo": "Grupo",
        "Funcionário": "Funcionário",
        "Setor": "Setor",
        "Monitoria (mês)": "Monitoria",
        "Tempo Empresa (anos)": "Anos",
        "Adicional Tempo (mês)": "Adic.",
        "Assiduidade": "Assid.",
        "Qualidade": "Qualid.",
        "Taxa de Erros": "Erros",
        "Produtividade / Eficiência": "Prod/Efic",
        "Comportamento": "Comp.",
        "Total Base (mês)": "Base",
        "Total Geral (mês)": "Total",
    }
    dfp = dfp.rename(columns={k: v for k, v in rename_map.items() if k in dfp.columns})
    ordered = ["Grupo", "Funcionário", "Setor", "Status", "Monitoria", "Anos", "Adic.", "Assid.", "Qualid.", "Erros", "Prod/Efic", "Comp.", "Base", "Total"]
    dfp = dfp[[c for c in ordered if c in dfp.columns]]
    
    if "Funcionário" in dfp.columns:
        dfp = dfp.sort_values("Funcionário", key=lambda s: s.astype(str).str.lower()).reset_index(drop=True)

    # Resumo do PDF
    total_people = len(dfp)
    total_geral = dfp["Total"].apply(brl_to_float).sum() if "Total" in dfp.columns else 0.0

    def card(lbl: str, val: str):
        t = Table([[Paragraph(lbl, small), Paragraph(val, small_bold)]], colWidths=[60 * mm, 30 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F4F6")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    cards = Table(
        [[
            card("Funcionários no relatório", str(total_people)),
            card("Total geral (base + monitoria + adicional)", brl(float(total_geral))),
        ]],
        colWidths=[190 * mm, 190 * mm],
    )
    story.append(cards)
    story.append(Spacer(1, 5 * mm))

    observation_text = pdf_text(report_observation) or "-"
    obs_tbl = Table(
        [[Paragraph("Observação", small_bold)], [Paragraph(observation_text, small)]],
        colWidths=[doc.width],
    )
    obs_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FFFFFF")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#D1D5DB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(obs_tbl)
    story.append(Spacer(1, 5 * mm))

    col_widths_map = {
        "Funcionário": 58 * mm,
        "Setor": 20 * mm,
        "Status": 16 * mm,
        "Monitoria": 20 * mm,
        "Anos": 10 * mm,
        "Adic.": 18 * mm,
        "Assid.": 15 * mm,
        "Qualid.": 15 * mm,
        "Erros": 15 * mm,
        "Prod/Efic": 18 * mm,
        "Comp.": 15 * mm,
        "Base": 19 * mm,
        "Total": 20 * mm,
    }

    def append_report_table(section_title: str, section_df: pd.DataFrame):
        if section_df is None or section_df.empty:
            return

        section_df = section_df.copy()
        if "Grupo" in section_df.columns:
            section_df = section_df.drop(columns=["Grupo"])

        story.append(Paragraph(section_title, small_bold))
        story.append(Spacer(1, 2 * mm))

        cols = section_df.columns.tolist()
        data = [cols]
        col_widths = [col_widths_map.get(c, 20 * mm) for c in cols]

        for _, r in section_df.iterrows():
            data.append([Paragraph(pdf_text(str(r[c])), small) for c in cols])

        tbl = Table(data, colWidths=col_widths, repeatRows=1)
        table_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ]

        if "Total" in cols:
            total_col_idx = cols.index("Total")
            table_styles.extend([
                ("BACKGROUND", (total_col_idx, 0), (total_col_idx, 0), colors.HexColor("#065F46")),
                ("TEXTCOLOR", (total_col_idx, 0), (total_col_idx, -1), colors.white),
                ("FONTNAME", (total_col_idx, 0), (total_col_idx, -1), "Helvetica-Bold"),
                ("BACKGROUND", (total_col_idx, 1), (total_col_idx, -1), colors.HexColor("#D1FAE5")),
                ("LINEBEFORE", (total_col_idx, 0), (total_col_idx, -1), 1.2, colors.HexColor("#065F46")),
            ])

        tbl.setStyle(TableStyle(table_styles))
        story.append(tbl)
        story.append(Spacer(1, 5 * mm))

    if "Grupo" in dfp.columns:
        colaboradores_dfp = dfp[dfp["Grupo"] != "Coordenação/Supervisão"].copy()
        lideranca_dfp = dfp[dfp["Grupo"] == "Coordenação/Supervisão"].copy()
    else:
        colaboradores_dfp = dfp.copy()
        lideranca_dfp = pd.DataFrame()

    append_report_table("Colaboradores avaliados", colaboradores_dfp)
    append_report_table("Coordenação/Supervisão (base padrão, sem avaliação)", lideranca_dfp)

    # --- ANEXO RH: resultados semanais (%) ---
    if include_weekly_appendix and weeks_iso and weekly_join_df is not None and (not weekly_join_df.empty):
        story.append(PageBreak())
        story.extend(build_weekly_pct_tables_for_pdf(weeks_iso, weekly_join_df))

    # Assinatura centralizada (no final do documento)
    story.append(Spacer(1, 6 * mm))

    sig_center = ParagraphStyle("SigCenter", parent=small, alignment=TA_CENTER)
    sig_center_bold = ParagraphStyle("SigCenterBold", parent=small_bold, alignment=TA_CENTER)

    sig_line = Table(
        [[""]],
        colWidths=[140 * mm],
        hAlign="CENTER",
        style=TableStyle([
            ("LINEBELOW", (0, 0), (0, 0), 0.9, colors.HexColor("#111827")),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
    )

    sig_block = KeepTogether([
        Paragraph("Assinatura do Coordenador", sig_center_bold),
        Spacer(1, 6 * mm),
        sig_line,
        Spacer(1, 2 * mm),
        Paragraph(pdf_text(coordinator_name.strip() or "______________________________"), sig_center),
    ])
    story.append(sig_block)

    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)

    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def build_sector_followup_pdf_bytes(
    summary_df: pd.DataFrame,
    employee_df: pd.DataFrame,
    month: str,
    sector_label: str,
    coordinator_name: str,
    report_observation: str,
    logo_path: str = "assets/logo.png",
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Relatório Unificado do Setor {sector_label} {month_label_to_br(month)}",
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleSector",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        textColor=colors.HexColor("#111827"),
        spaceAfter=2,
    )
    subtitle = ParagraphStyle(
        "SubSector",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=11.5,
        textColor=colors.HexColor("#374151"),
        spaceAfter=6,
    )
    small = ParagraphStyle(
        "SectorSmall",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=9.5,
        textColor=colors.HexColor("#374151"),
    )
    body = ParagraphStyle(
        "SectorBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=10.8,
        textColor=colors.HexColor("#374151"),
    )
    bold = ParagraphStyle("SectorBold", parent=body, fontName="Helvetica-Bold")
    h2 = ParagraphStyle("SectorH2", parent=bold, fontSize=10.5, leading=12.5, spaceBefore=7, spaceAfter=3)
    person_title = ParagraphStyle("SectorPersonTitle", parent=bold, fontSize=10.3, leading=12.3, textColor=colors.HexColor("#111827"))
    center = ParagraphStyle("SectorCenter", parent=body, alignment=TA_CENTER)
    center_bold = ParagraphStyle("SectorCenterBold", parent=bold, alignment=TA_CENTER)

    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    def draw_header_footer(canvas, doc_):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(colors.HexColor("#111827"))
        canvas.rect(0, h - 8 * mm, w, 8 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(14 * mm, h - 6 * mm, f"Relatório Unificado do Setor • {month_label_to_br(month)}")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - 14 * mm, h - 6 * mm, f"Gerado em {generated_at}")
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(14 * mm, 7 * mm, "Uso interno • Feedback e acompanhamento")
        canvas.drawRightString(w - 14 * mm, 7 * mm, f"Página {doc_.page}")
        canvas.restoreState()

    story = []
    try:
        logo = Image(logo_path, width=18 * mm, height=18 * mm)
        logo.hAlign = "LEFT"
        story.append(logo)
    except Exception:
        pass

    story.append(Paragraph("Relatório Unificado do Setor", title))
    story.append(Paragraph(
        f"<b>Setor:</b> {pdf_text(sector_label)} &nbsp;&nbsp; "
        f"<b>Competência:</b> {month_label_to_br(month)}",
        subtitle,
    ))
    story.append(Spacer(1, 2 * mm))

    observation_text = pdf_text(report_observation) or "-"
    obs_tbl = Table(
        [[Paragraph("Observação para feedback", bold)], [Paragraph(observation_text, body)]],
        colWidths=[doc.width],
    )
    obs_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(obs_tbl)
    story.append(Spacer(1, 4 * mm))

    summary_display = _drop_hidden_columns(summary_df)
    if summary_display is not None and not summary_display.empty:
        story.append(Paragraph("Resumo do setor", h2))
        story.append(Spacer(1, 2 * mm))
        summary_cols = [
            "Setor", "Funcionários", "Média geral (%)", "Cobertura avaliações",
            "Erros (qtd)", "Pendências", "Prioritários", "Total Geral (mês)",
        ]
        summary_display = summary_display[[c for c in summary_cols if c in summary_display.columns]]
        summary_data = [summary_display.columns.tolist()]
        for _, row in summary_display.iterrows():
            summary_data.append([Paragraph(pdf_text(str(row[col])), small) for col in summary_display.columns])
        summary_width_map = {
            "Setor": 36 * mm,
            "Funcionários": 18 * mm,
            "Média geral (%)": 22 * mm,
            "Cobertura avaliações": 26 * mm,
            "Erros (qtd)": 16 * mm,
            "Pendências": 18 * mm,
            "Prioritários": 18 * mm,
            "Total Geral (mês)": 28 * mm,
        }
        summary_tbl = Table(
            summary_data,
            repeatRows=1,
            colWidths=[summary_width_map.get(col, 22 * mm) for col in summary_display.columns],
        )
        summary_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.6),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(summary_tbl)
        story.append(Spacer(1, 5 * mm))

    employee_display = _drop_hidden_columns(employee_df)
    if employee_display is not None and not employee_display.empty:
        story.append(Paragraph("Funcionários e detalhes", h2))
        story.append(Spacer(1, 2 * mm))

        value_style = ParagraphStyle("SectorValue", parent=small)

        def detail_cell(label: str, value: str):
            return Paragraph(f"<b>{pdf_text(label)}:</b> {pdf_text(value)}", value_style)

        for idx, row in employee_display.iterrows():
            story.append(KeepTogether([
                Paragraph(pdf_text(str(row.get("Funcionário", "-"))), person_title),
                Paragraph(
                    f"{pdf_text(row.get('Função', '-'))} • {pdf_text(row.get('Setor', '-'))} • "
                    f"{pdf_text(row.get('Status', '-'))}",
                    small,
                ),
                Spacer(1, 1.5 * mm),
            ]))

            details_rows = [
                [
                    detail_cell("Indicador", row.get("Indicador", "-")),
                    detail_cell("Acompanhamento", row.get("Acompanhamento", "-")),
                ],
                [
                    detail_cell("Média geral", row.get("Média geral (%)", "-")),
                    detail_cell("Cobertura", row.get("Cobertura avaliações", "-")),
                ],
                [
                    detail_cell("Semanas", row.get("Semanas avaliadas/elegíveis", "-")),
                    detail_cell("Erros/Pendências", f"{row.get('Erros (qtd)', 0)} / {row.get('Pendências', 0)}"),
                ],
                [
                    detail_cell("Assiduidade", row.get("Assiduidade (%)", "-")),
                    detail_cell("Qualidade", row.get("Qualidade (%)", "-")),
                ],
                [
                    detail_cell("Taxa de Erros", row.get("Taxa de Erros (%)", "-")),
                    detail_cell("Prod/Efic", row.get("Prod/Efic (%)", "-")),
                ],
                [
                    detail_cell("Comportamento", row.get("Comportamento (%)", "-")),
                    detail_cell("Total Geral", row.get("Total Geral (mês)", "-")),
                ],
            ]
            details_tbl = Table(details_rows, colWidths=[doc.width / 2, doc.width / 2])
            details_tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#F9FAFB"), colors.white]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(details_tbl)
            story.append(Spacer(1, 2 * mm))

            focus_feedback_tbl = Table(
                [
                    [Paragraph(f"<b>Foco do feedback:</b> {pdf_text(row.get('Foco do feedback', '-'))}", body)],
                    [Paragraph(f"<b>Feedback sugerido:</b> {pdf_text(row.get('Feedback sugerido', '-'))}", body)],
                ],
                colWidths=[doc.width],
            )
            focus_feedback_tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F4F6")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.25, colors.HexColor("#D1D5DB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(focus_feedback_tbl)
            if idx < len(employee_display) - 1:
                story.append(Spacer(1, 5 * mm))

    story.append(Spacer(1, 6 * mm))
    sig_line = Table(
        [[""]],
        colWidths=[140 * mm],
        hAlign="CENTER",
        style=TableStyle([
            ("LINEBELOW", (0, 0), (0, 0), 0.9, colors.HexColor("#111827")),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
    )
    story.append(KeepTogether([
        Paragraph("Assinatura do Coordenador", center_bold),
        Spacer(1, 6 * mm),
        sig_line,
        Spacer(1, 2 * mm),
        Paragraph(pdf_text(coordinator_name.strip() or "______________________________"), center),
    ]))

    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


# -----------------------------
# PDF detalhado por funcionário (A4 retrato)
# -----------------------------
def build_detailed_employee_pdf_bytes(
    employee_name: str,
    employee_sector: str,
    employee_role: str,
    month: str,
    weeks_iso: list[str],
    weekly_rows_df: pd.DataFrame,
    errors_df: pd.DataFrame,
    coordinator_name: str,
    report_observation: str,
    logo_path: str = "assets/logo.png",
    monitor_row: dict = None,
    period_summary: dict | None = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Detalhado • {employee_name} • {month_label_to_br(month)}",
    )

    styles = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=14, leading=16, spaceAfter=4)
    H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, leading=13, spaceBefore=8, spaceAfter=4)
    BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontSize=9, leading=11)
    SMALL = ParagraphStyle("SMALL", parent=styles["BodyText"], fontSize=8.5, leading=10.5, textColor=colors.HexColor("#374151"))
    CENTER = ParagraphStyle("CENTER", parent=BODY, alignment=TA_CENTER)
    CENTER_BOLD = ParagraphStyle("CENTER_BOLD", parent=BODY, alignment=TA_CENTER, fontName="Helvetica-Bold")

    story = []

    try:
        logo = Image(logo_path, width=18 * mm, height=18 * mm)
        logo.hAlign = "LEFT"
        story.append(logo)
    except Exception:
        pass

    story.append(Paragraph("Relatório Detalhado de Avaliação (Auditoria)", H1))
    story.append(Paragraph(f"<b>Mês:</b> {month_label_to_br(month)}", BODY))
    story.append(Paragraph(
        f"<b>Funcionário:</b> {pdf_text(employee_name)} • "
        f"<b>Setor:</b> {pdf_text(employee_sector)} • "
        f"<b>Função:</b> {pdf_text(employee_role)}",
        BODY,
    ))
    story.append(Spacer(1, 4 * mm))

    if period_summary:
        story.append(Paragraph("Resumo geral do período", H2))
        weeks_text = f'{period_summary.get("Semanas avaliadas", 0)}/{period_summary.get("Semanas elegíveis", 0)}'
        summary_rows = [
            ["Período", period_summary.get("Período", "-"), "Semanas avaliadas/elegíveis", weeks_text],
            ["Base (mês)", period_summary.get("Total Base (mês)", brl(0.0)), "Monitoria (mês)", period_summary.get("Monitoria (mês)", brl(0.0))],
            ["Adicional tempo", period_summary.get("Adicional Tempo (mês)", brl(0.0)), "Total do mês", period_summary.get("Total Geral (mês)", brl(0.0))],
        ]
        summary_data = [
            [
                Paragraph(pdf_text(label_a), CENTER_BOLD),
                Paragraph(pdf_text(value_a), BODY),
                Paragraph(pdf_text(label_b), CENTER_BOLD),
                Paragraph(pdf_text(value_b), BODY),
            ]
            for label_a, value_a, label_b, value_b in summary_rows
        ]
        summary_tbl = Table(summary_data, colWidths=[38 * mm, 43 * mm, 48 * mm, 49 * mm])
        summary_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F4F6")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F3F4F6")),
            ("BACKGROUND", (2, 2), (3, 2), colors.HexColor("#D1FAE5")),
            ("TEXTCOLOR", (2, 2), (3, 2), colors.HexColor("#065F46")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
            ("FONTNAME", (3, 2), (3, 2), "Helvetica-Bold"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(summary_tbl)
        story.append(Spacer(1, 4 * mm))

    observation_text = pdf_text(report_observation) or "-"
    obs_tbl = Table(
        [[Paragraph("Observação", CENTER_BOLD)], [Paragraph(observation_text, BODY)]],
        colWidths=[doc.width],
    )
    obs_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#D1D5DB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(obs_tbl)
    story.append(Spacer(1, 4 * mm))

    # Seção Monitoria (se existir)
    if monitor_row:
        story.append(Paragraph("Monitoria (mês)", H2))

        mpcts = {
            "acomp_metas": float(monitor_row.get("acomp_metas_pct", 0) or 0),
            "org_fluxo": float(monitor_row.get("org_fluxo_pct", 0) or 0),
            "suporte_equipe": float(monitor_row.get("suporte_equipe_pct", 0) or 0),
            "disciplina_oper": float(monitor_row.get("disciplina_oper_pct", 0) or 0),
        }

        mprev = monitoria_money_preview(mpcts)
        mdata = [mprev.columns.tolist()] + mprev.astype(str).values.tolist()

        mtbl = Table(mdata, repeatRows=1, colWidths=[72*mm, 22*mm, 18*mm, 24*mm, 24*mm])
        mtbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(mtbl)
        story.append(Spacer(1, 3 * mm))

        mjusts = _get_monitor_justs_from_row(monitor_row)
        story.append(Paragraph("Justificativas da Monitoria", ParagraphStyle("MH", parent=H2, fontSize=10, spaceBefore=6)))
        story.append(pdf_field("Acompanhamento de metas", mjusts["Acompanhamento de metas"] or "-", BODY))
        story.append(pdf_field("Organização do fluxo", mjusts["Organização do fluxo"] or "-", BODY))
        story.append(pdf_field("Suporte à equipe", mjusts["Suporte à equipe"] or "-", BODY))
        story.append(pdf_field("Disciplina operacional", mjusts["Disciplina operacional"] or "-", BODY))
        story.append(Spacer(1, 6 * mm))

    # erros agrupados por semana
    errors_by_week = {}
    if errors_df is not None and not errors_df.empty:
        for _, r in errors_df.iterrows():
            ws = str(r["week_start"])
            errors_by_week.setdefault(ws, []).append(r)

    week_map = {str(r["week_start"]): r for _, r in weekly_rows_df.iterrows()}

    evaluated_weeks = [ws for ws in weeks_iso if ws in week_map]
    for idx, ws in enumerate(evaluated_weeks):

        row = week_map[ws]
        pcts = {
            "assiduidade": float(row.get("assiduidade_pct", 0) or 0),
            "qualidade": float(row.get("qualidade_pct", 0) or 0),
            "taxa_erros": float(row.get("taxa_erros_pct", 0) or 0),
            "produtividade": float(row.get("produtividade_pct", 0) or 0),
            "comportamento": float(row.get("comportamento_pct", 0) or 0),
        }

        ws_date = datetime.strptime(ws, "%Y-%m-%d").date()
        story.append(Paragraph(f"Semana {week_label(ws_date)}", H2))

        evaluator = str(row.get("evaluator", "") or "-")
        items = int(row.get("items_count", 0) or 0)
        story.append(Paragraph(f"<b>Avaliador:</b> {pdf_text(evaluator)} &nbsp;&nbsp; <b>Itens/peças:</b> {items}", SMALL))
        story.append(Spacer(1, 2 * mm))

        preview_df = week_money_preview(pcts, ws)
        data = [preview_df.columns.tolist()] + preview_df.astype(str).values.tolist()

        tbl = Table(data, repeatRows=1, colWidths=[55*mm, 25*mm, 22*mm, 28*mm, 28*mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 3 * mm))

        justs = _get_weekly_justs_from_row(row)
        story.append(Paragraph("Justificativas (semana)", ParagraphStyle("JH", parent=H2, fontSize=10, spaceBefore=6)))
        for k in ["Assiduidade", "Qualidade", "Taxa de Erros", "Produtividade/Eficiência", "Comportamento"]:
            val = (justs.get(k) or "-").strip() or "-"
            story.append(pdf_field(k, val, BODY))
        story.append(Spacer(1, 2 * mm))

        story.append(Paragraph("Log de erros (semana)", ParagraphStyle("EH", parent=H2, fontSize=10, spaceBefore=6)))
        wk_errs = errors_by_week.get(ws, [])
        if not wk_errs:
            story.append(Paragraph("Sem erros registrados no log nesta semana.", SMALL))
        else:
            err_rows = [["Tipo", "Gravidade", "Qtd", "Obs"]]
            for er in wk_errs:
                err_rows.append([
                    str(er.get("error_type", "")),
                    severity_label(str(er.get("severity", ""))),
                    str(er.get("qty", "")),
                    str(er.get("notes", "") or ""),
                ])
            err_tbl = Table(err_rows, repeatRows=1, colWidths=[72*mm, 22*mm, 12*mm, 72*mm])
            err_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(err_tbl)

        if idx < len(evaluated_weeks) - 1:
            story.append(PageBreak())

    # Assinatura
    story.append(Spacer(1, 6 * mm))
    sig_line = Table([[""]], colWidths=[120 * mm], hAlign="CENTER",
                     style=TableStyle([("LINEBELOW", (0, 0), (0, 0), 0.9, colors.HexColor("#111827"))]))
    story.append(KeepTogether([
        Paragraph("Assinatura do Coordenador", CENTER_BOLD),
        Spacer(1, 6 * mm),
        sig_line,
        Spacer(1, 2 * mm),
        Paragraph(pdf_text(coordinator_name.strip() or "______________________________"), CENTER),
    ]))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


# -----------------------------
# UI
# -----------------------------
def render_report_page():
    render_page_header(
        title="Relatório Mensal",
        subtitle="Fechamento com checklist, resumo executivo, acompanhamento do setor, PDF para assinatura, anexo RH e detalhamento por funcionário.",
        icon="📊",
        kicker="Etapa 4",
        meta=["Resumo executivo", "Setor", "Detalhado"],
    )
    render_operation_status()

    top_left, top_right = st.columns([2.6, 1], gap="large", vertical_alignment="bottom")
    with top_left:
        st.caption("Selecione a competência e revise pendências antes de gerar os arquivos finais.")
    with top_right:
        month_input = st.text_input("Mês (MM/AAAA)", value=current_month_br())
        try:
            month = normalize_month_label(month_input)
        except ValueError:
            st.error("Mês inválido. Use MM/AAAA (ex.: 05/2026).")
            return
        month_br = month_label_to_br(month)

    tabs = st.tabs(["Resumo", "Setor unificado", "Detalhado por funcionário"])

    # =========================
    # TAB 1: Resumo
    # =========================
    with tabs[0]:
        render_divider()
        try:
            df, weeks_iso = build_month_df(month)
        except Exception:
            st.error("Mês inválido. Use MM/AAAA (ex.: 05/2026).")
            return

        with st.expander("Semanas consideradas no fechamento"):
            st.write([week_label(datetime.strptime(w, "%Y-%m-%d").date()) for w in weeks_iso])

        render_closing_check(month, weeks_iso)

        if df.empty:
            st.info("Sem dados para o período (ou sem funcionários ativos).")
            return

        # Filtros (tela)
        f1, f2, f3 = st.columns([1.6, 1.2, 1.2], gap="medium")
        with f1:
            q = st.text_input("Busca", placeholder="Nome / Setor / Função")
        with f2:
            sectors = ["(Todos)"] + sorted(df["Setor"].dropna().astype(str).unique().tolist())
            sector_filter = st.selectbox("Setor", sectors)
        with f3:
            roles = ["(Todas)"] + sorted(df["Função"].dropna().astype(str).unique().tolist())
            role_filter = st.selectbox("Função", roles)

        df_view = df.copy()
        if q.strip():
            qq = q.strip().lower()
            df_view = df_view[
                df_view["Funcionário"].astype(str).str.lower().str.contains(qq, regex=False, na=False)
                | df_view["Setor"].astype(str).str.lower().str.contains(qq, regex=False, na=False)
                | df_view["Função"].astype(str).str.lower().str.contains(qq, regex=False, na=False)
            ]
        if sector_filter != "(Todos)":
            df_view = df_view[df_view["Setor"] == sector_filter]
        if role_filter != "(Todas)":
            df_view = df_view[df_view["Função"] == role_filter]

        total_geral = df_view["Total Geral (mês)"].apply(brl_to_float).sum()
        total_adicional_tempo = df_view["Adicional Tempo (mês)"].apply(brl_to_float).sum()

        c1, c2, c3, c4, c5 = st.columns(5, gap="medium")
        c1.metric("Funcionários (filtro)", len(df_view))
        c2.metric("Total Geral (mês)", brl(float(total_geral)))
        c3.metric("Setores", df_view["Setor"].nunique())
        c4.metric("Adicional tempo", brl(float(total_adicional_tempo)))
        c5.metric("Monitores (com valor)", int((df_view["Monitoria (mês)"].apply(brl_to_float) > 0).sum()))

        st.markdown("---")

        left, right = st.columns([3, 1.4], gap="large")
        with left:
            render_section_header(
                "Detalhamento",
                "A tabela da tela pode conter métricas auxiliares; o PDF executivo é mais limpo.",
                "Conferência",
            )
            hidden_cols = [
                "_employee_id", "_hire_date", "_monitor_start_date", "_leadership_start_date",
                "_termination_date", "_is_leadership", "_active",
            ]
            df_view_display = format_report_display_df(df_view)
            df_colab = df_view_display[df_view_display["Grupo"] == "Colaboradores"].copy()
            df_leadership = df_view_display[df_view_display["Grupo"] == "Coordenação/Supervisão"].copy()

            st.markdown("#### Colaboradores")
            if df_colab.empty:
                st.info("Nenhum colaborador no filtro atual.")
            else:
                st.dataframe(df_colab.drop(columns=hidden_cols), width="stretch", hide_index=True)

            st.markdown("#### Coordenação/Supervisão")
            if df_leadership.empty:
                st.info("Nenhum funcionário de coordenação/supervisão no filtro atual.")
            else:
                st.dataframe(df_leadership.drop(columns=hidden_cols), width="stretch", hide_index=True)

        with right:
            render_section_header("Ranking", "Top 10 por total geral no filtro atual.", "Total Geral")
            rank = df_view.copy()
            rank["_total"] = rank["Total Geral (mês)"].apply(brl_to_float)
            rank = rank.sort_values("_total", ascending=False)[["Funcionário", "Setor", "Função", "_total"]].head(10)
            rank = rank.rename(columns={"_total": "Total Geral"})
            rank["Total Geral"] = rank["Total Geral"].map(lambda v: brl(float(v)))
            st.dataframe(rank, width="stretch", hide_index=True)

        render_divider()
        render_section_header(
            "PDF para impressão",
            "Gere o relatório executivo com assinatura e, se necessário, o anexo RH semanal.",
            "Exportação",
        )

        coordinator_name = st.text_input("Coordenador (assinatura)", value="Yohann Risso")
        report_observation = st.text_area(
            "Observação do relatório",
            placeholder="Digite uma observação livre para aparecer no PDF.",
            height=100,
            key="report_observation_exec",
        )
        include_weekly_appendix = st.toggle("Incluir ANEXO RH (resultados semanais em %)", value=True)

        # monta df_pdf (remove erros/efic + remove Função + remove id interno)
        drop_cols = [
            c for c in [
                "Erros (qtd)", "Prod/Efic média (%)", "Função", "_employee_id", "_hire_date",
                "_monitor_start_date", "_leadership_start_date", "_termination_date", "_is_leadership", "_active",
            ]
            if c in df_view.columns
        ]
        df_pdf = df_view.drop(columns=drop_cols)

        # Anexo RH: puxa avaliações semanais (%) para os funcionários filtrados (por ID)
        df_appendix = df_view[df_view["_is_leadership"] == 0].copy()
        emp_ids = df_appendix["_employee_id"].tolist()
        weekly_join_df = pd.DataFrame()
        if include_weekly_appendix and weeks_iso and emp_ids:
            weekly_join_df = fetch_weekly_evaluations_for_weeks(weeks_iso, emp_ids)
            if not weekly_join_df.empty:
                name_map = dict(zip(df_appendix["_employee_id"], df_appendix["Funcionário"]))
                hire_map = dict(zip(df_appendix["_employee_id"], df_appendix["_hire_date"]))
                weekly_join_df = weekly_join_df[
                    weekly_join_df.apply(
                        lambda row: is_week_after_hire(hire_map.get(int(row["employee_id"]), ""), str(row["week_start"])),
                        axis=1,
                    )
                ]
                weekly_join_df["name"] = weekly_join_df["employee_id"].map(name_map)
                weekly_join_df = weekly_join_df.sort_values(["week_start", "name"])

        pdf_bytes = build_report_pdf_bytes_executivo(
            df_pdf=df_pdf,
            month=month,
            coordinator_name=coordinator_name,
            report_observation=report_observation,
            weeks_iso=weeks_iso,
            weekly_join_df=weekly_join_df,
            include_weekly_appendix=include_weekly_appendix,
            logo_path="assets/logo.png",
        )

        st.download_button(
            "⬇️ Baixar PDF (paisagem) — executivo + anexo RH",
            data=pdf_bytes,
            file_name=f"relatorio_{month}_executivo_com_anexoRH.pdf",
            mime="application/pdf",
        )

        render_divider()
        render_section_header("Exportação da tela", "Baixe a visão completa filtrada em CSV.", "Dados")
        csv_df = format_report_display_df(df_view.drop(columns=[
            "_employee_id",
            "_hire_date",
            "_monitor_start_date",
            "_leadership_start_date",
            "_termination_date",
            "_is_leadership",
            "_active",
        ]))
        csv = csv_df.to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button(
            "⬇️ Baixar CSV (completo)",
            csv,
            file_name=f"relatorio_{month}_completo.csv",
            mime="text/csv"
        )

    # =========================
    # TAB 2: Setor unificado
    # =========================
    with tabs[1]:
        render_divider()
        render_section_header(
            "Setor unificado",
            "Resumo para conversa de feedback, priorização de acompanhamento e visão única dos funcionários do setor.",
            "Feedback",
        )

        sector_options = ["(Todos)"]
        if "df" in locals() and isinstance(df, pd.DataFrame) and not df.empty:
            sector_options += sorted(df["Setor"].dropna().astype(str).unique().tolist())

        selected_sector = st.selectbox("Setor para acompanhamento", sector_options, key="sector_followup_filter")
        sector_label = "Todos os setores" if selected_sector == "(Todos)" else selected_sector

        try:
            sector_summary_df, sector_employee_df, sector_weeks_iso = build_sector_followup_tables(month, selected_sector)
        except Exception:
            st.error("Não foi possível montar o relatório unificado do setor para a competência selecionada.")
            return

        if sector_employee_df.empty:
            st.info("Sem funcionários válidos para o setor e período selecionados.")
        else:
            expected = int(sector_employee_df["_expected_weeks"].sum())
            evaluated = int(sector_employee_df["_evaluated_weeks"].sum())
            coverage = round((evaluated / expected) * 100, 1) if expected else None
            avg_pct = _avg_or_none(sector_employee_df["_avg_pct"].dropna().tolist())
            priority_count = int(sector_employee_df["Indicador"].isin(["Regularizar", "Prioritário"]).sum())
            pending_count = int(sector_employee_df["_pending_total"].sum())

            m1, m2, m3, m4, m5 = st.columns(5, gap="medium")
            m1.metric("Funcionários", len(sector_employee_df))
            m2.metric("Média geral", _pct_or_dash(avg_pct, 1))
            m3.metric("Cobertura", _pct_or_dash(coverage, 1))
            m4.metric("Pendências", pending_count)
            m5.metric("Prioritários", priority_count)

            with st.expander("Semanas consideradas no acompanhamento do setor"):
                st.write([week_label(datetime.strptime(w, "%Y-%m-%d").date()) for w in sector_weeks_iso])

            render_divider()
            left, right = st.columns([1.25, 2.4], gap="large")
            with left:
                render_section_header("Resumo por setor", "Indicadores agregados da seleção atual.", "Consolidado")
                st.dataframe(_drop_hidden_columns(sector_summary_df), width="stretch", hide_index=True)

            with right:
                render_section_header("Acompanhamento", "Lista prática para feedback e revisão de rotina.", "Funcionários")
                display_employee = _drop_hidden_columns(sector_employee_df)
                ordered_cols = [
                    "Setor", "Funcionário", "Função", "Indicador", "Média geral (%)",
                    "Assiduidade (%)", "Qualidade (%)", "Taxa de Erros (%)", "Prod/Efic (%)",
                    "Comportamento (%)", "Cobertura avaliações", "Semanas avaliadas/elegíveis", "Erros (qtd)",
                    "Pendências", "Foco do feedback", "Acompanhamento", "Feedback sugerido",
                    "Total Geral (mês)",
                ]
                display_employee = display_employee[[c for c in ordered_cols if c in display_employee.columns]]
                st.dataframe(display_employee, width="stretch", hide_index=True)

            render_divider()
            render_section_header(
                "Exportação do setor",
                "Baixe a lista de acompanhamento em CSV ou gere o PDF unificado para reunião e assinatura.",
                "Dados",
            )

            csv_sector = display_employee.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button(
                "⬇️ Baixar CSV (setor unificado)",
                csv_sector,
                file_name=f"relatorio_setor_{selected_sector.replace('/', '-')}_{month}.csv",
                mime="text/csv",
            )

            coord_sector = st.text_input("Coordenador (assinatura no PDF do setor)", value="Yohann Risso", key="coord_sector_pdf")
            sector_observation = st.text_area(
                "Observação do relatório do setor",
                placeholder="Digite uma orientação geral para a conversa de feedback do setor.",
                height=100,
                key="report_observation_sector",
            )
            pdf_sector = build_sector_followup_pdf_bytes(
                summary_df=sector_summary_df,
                employee_df=sector_employee_df,
                month=month,
                sector_label=sector_label,
                coordinator_name=coord_sector,
                report_observation=sector_observation,
                logo_path="assets/logo.png",
            )
            safe_sector = sector_label.strip().replace("/", "-").replace(" ", "_")
            st.download_button(
                "⬇️ Baixar PDF (setor unificado)",
                data=pdf_sector,
                file_name=f"relatorio_setor_unificado_{safe_sector}_{month}.pdf",
                mime="application/pdf",
            )

    # =========================
    # TAB 3: Detalhado por funcionário
    # =========================
    with tabs[2]:
        render_divider()
        render_section_header(
            "Detalhado por funcionário",
            "Semanas do mês com percentuais, faixa aplicada, pagamento, justificativas, erros e monitoria quando houver.",
            "Auditoria",
        )

        try:
            year, month_num = map(int, month.split("-"))
            weeks = weeks_for_competencia(year, month_num)
            weeks_iso = [w.isoformat() for w in weeks]
        except Exception:
            st.error("Mês inválido. Use MM/AAAA (ex.: 05/2026).")
            return

        employees = fetch_df(
            f"""
            SELECT DISTINCT
                e.id,
                e.name,
                e.sector,
                e.role,
                e.hire_date,
                e.monitor_start_date,
                e.leadership_start_date,
                e.termination_date,
                e.is_monitor,
                e.active
            FROM employees e
            LEFT JOIN weekly_evaluations w
              ON w.employee_id = e.id
             AND {_clean_week_start_sql("w")} IN ({",".join(["?"] * len(weeks_iso))})
            LEFT JOIN weekly_errors er
              ON er.employee_id = e.id
             AND {_clean_week_start_sql("er")} IN ({",".join(["?"] * len(weeks_iso))})
            WHERE COALESCE(e.is_leadership, 0) = 0
            ORDER BY e.active DESC, e.sector, e.role, e.name
            """,
            tuple(weeks_iso + weeks_iso),
        )
        if employees.empty:
            st.info("Nenhum funcionário ativo ou com histórico no mês selecionado.")
            return

        employees = employees[
            employees.apply(lambda emp: is_employee_valid_for_period(emp, weeks_iso), axis=1)
        ].copy()
        if employees.empty:
            st.info("Nenhum funcionário válido para o período selecionado.")
            return

        colS1, colS2 = st.columns([2.2, 1], gap="medium")
        with colS1:
            emp_map = {
                f'{r["name"]} • {r["sector"]} • {r["role"]}{" • MONITOR" if int(r["is_monitor"])==1 else ""}{" • DESATIVADO" if int(r.get("active", 1))==0 else ""}': int(r["id"])
                for _, r in employees.iterrows()
            }
            selected_emp = st.selectbox("Funcionário", list(emp_map.keys()))
        with colS2:
            st.caption("Semanas da competência")
            st.write(len(weeks_iso))

        employee_id = emp_map[selected_emp]
        emp_row = employees[employees["id"] == employee_id].iloc[0]
        employee_name = str(emp_row["name"])
        employee_sector = str(emp_row["sector"])
        employee_role = str(emp_row["role"])
        hire_date_iso = str(emp_row.get("hire_date", "") or "")
        monitor_start_date_iso = str(emp_row.get("monitor_start_date", "") or "")
        if not is_employee_valid_for_period(emp_row, weeks_iso):
            st.warning("Esse funcionário não é válido para o período selecionado.")
            return

        weeks_iso = eligible_weeks_for_valid_employee(
            hire_date_iso,
            weeks_iso,
            emp_row.get("termination_date", ""),
        )
        st.caption(f"Semanas elegíveis a partir da segunda semana: {len(weeks_iso)}")

        we = pd.DataFrame()
        if weeks_iso:
            we = fetch_weekly_evaluations_for_weeks(weeks_iso, [employee_id]).sort_values("week_start")

        if we.empty:
            st.warning("Esse funcionário não tem avaliações no mês selecionado.")
            return

        summary_row = {}
        if "df" in locals() and isinstance(df, pd.DataFrame) and not df.empty and "_employee_id" in df.columns:
            summary_match = df[df["_employee_id"].astype(int) == int(employee_id)]
            if not summary_match.empty:
                summary_row = summary_match.iloc[0].to_dict()

        if not summary_row:
            detail_month_df, _ = build_month_df(month)
            if not detail_month_df.empty and "_employee_id" in detail_month_df.columns:
                summary_match = detail_month_df[detail_month_df["_employee_id"].astype(int) == int(employee_id)]
                if not summary_match.empty:
                    summary_row = summary_match.iloc[0].to_dict()

        period_summary = build_employee_period_summary(
            month=month,
            summary_row=summary_row,
            eligible_weeks=weeks_iso,
            weekly_rows_df=we,
        )

        render_divider()
        st.markdown("#### Resumo geral do período")
        s1, s2, s3, s4 = st.columns(4, gap="medium")
        s1.metric("Base (mês)", period_summary["Total Base (mês)"])
        s2.metric("Monitoria", period_summary["Monitoria (mês)"])
        s3.metric("Adicional tempo", period_summary["Adicional Tempo (mês)"])
        s4.metric("Total do mês", period_summary["Total Geral (mês)"])

        s5, s6, s7, s8 = st.columns(4, gap="medium")
        s5.metric("Período", period_summary["Período"])
        s6.metric("Semanas avaliadas/elegíveis", f'{period_summary["Semanas avaliadas"]}/{period_summary["Semanas elegíveis"]}')
        s7.metric("Erros (qtd)", period_summary["Erros (qtd)"])
        s8.metric("Prod/Efic média", period_summary["Prod/Efic média"])

        component_rows = []
        for _key, label, _weekly_value, _cap in WEEKLY_CRITERIA:
            if _key == "produtividade":
                label = "Produtividade / Eficiência"
            if label in summary_row:
                component_rows.append({"Componente": label, "Valor no mês": str(summary_row.get(label, brl(0.0)))})
        component_rows.extend([
            {"Componente": "Monitoria", "Valor no mês": period_summary["Monitoria (mês)"]},
            {"Componente": "Adicional tempo", "Valor no mês": period_summary["Adicional Tempo (mês)"]},
            {"Componente": "Total do mês", "Valor no mês": period_summary["Total Geral (mês)"]},
        ])
        if component_rows:
            st.dataframe(pd.DataFrame(component_rows), width="stretch", hide_index=True)

        # monitoria do mês (se houver)
        mon_df = fetch_df(
            "SELECT * FROM monitor_monthly_evaluations WHERE employee_id = ? AND month = ?",
            (employee_id, month)
        )
        monitor_row = (
            mon_df.iloc[0].to_dict()
            if (
                not mon_df.empty
                and is_monitoria_eligible_for_month(monitor_start_date_iso, [w.isoformat() for w in weeks])
            )
            else None
        )

        # erros (todas as semanas do mês, 1 query)
        errs_all = pd.DataFrame()
        if weeks_iso:
            errs_all = fetch_df(
                f"""
                SELECT {_clean_week_start_sql("")} AS week_start, error_type, severity, qty, COALESCE(notes,'') AS notes
                FROM weekly_errors
                WHERE employee_id = ? AND {_clean_week_start_sql("")} IN ({",".join(["?"] * len(weeks_iso))})
                ORDER BY week_start ASC, id DESC
                """,
                tuple([employee_id] + weeks_iso)
            )

        # exibição por semana (expander)
        we_map = {str(r["week_start"]): r for _, r in we.iterrows()}

        render_divider()
        st.markdown("#### Semanas avaliadas")

        for ws in weeks_iso:
            if ws not in we_map:
                continue

            row = we_map[ws]
            pcts = {
                "assiduidade": float(row.get("assiduidade_pct", 0) or 0),
                "qualidade": float(row.get("qualidade_pct", 0) or 0),
                "taxa_erros": float(row.get("taxa_erros_pct", 0) or 0),
                "produtividade": float(row.get("produtividade_pct", 0) or 0),
                "comportamento": float(row.get("comportamento_pct", 0) or 0),
            }

            ws_date = datetime.strptime(ws, "%Y-%m-%d").date()
            with st.expander(f"Semana {week_label(ws_date)}", expanded=False):
                topA, topB, topC = st.columns([1.2, 1.2, 1], gap="medium")
                with topA:
                    st.metric("Itens/peças (info)", int(row.get("items_count", 0) or 0))
                with topB:
                    st.metric("Avaliador", str(row.get("evaluator", "") or "-"))
                with topC:
                    st.metric("Prod/Efic (resultado)", pct_br(pcts["produtividade"], 0))

                st.markdown("##### Percentuais, faixas e pagamento (semana)")
                st.dataframe(week_money_preview(pcts, ws), width="stretch", hide_index=True)

                st.markdown("##### Justificativas (semana)")
                justs = _get_weekly_justs_from_row(row)
                st.write(f"**Assiduidade:** {justs.get('Assiduidade') or '-'}")
                st.write(f"**Qualidade:** {justs.get('Qualidade') or '-'}")
                st.write(f"**Taxa de Erros:** {justs.get('Taxa de Erros') or '-'}")
                st.write(f"**Produtividade/Eficiência:** {justs.get('Produtividade/Eficiência') or '-'}")
                st.write(f"**Comportamento:** {justs.get('Comportamento') or '-'}")

                st.markdown("##### Log de erros (semana)")
                if errs_all is None or errs_all.empty:
                    st.info("Sem erros no mês.")
                else:
                    wk_errs = errs_all[errs_all["week_start"] == ws].copy()
                    if wk_errs.empty:
                        st.info("Sem erros registrados no log nesta semana.")
                    else:
                        wk_errs = wk_errs.rename(columns={
                            "error_type": "Tipo",
                            "severity": "Gravidade",
                            "qty": "Qtd",
                            "notes": "Obs",
                        })
                        wk_errs["Gravidade"] = wk_errs["Gravidade"].map(severity_label)
                        st.dataframe(wk_errs[["Tipo", "Gravidade", "Qtd", "Obs"]], width="stretch", hide_index=True)

        # PDF detalhado
        render_divider()
        render_section_header(
            "PDF detalhado",
            "Gere o arquivo individual para auditoria, assinatura ou conversa de feedback.",
            "Impressão",
        )

        coord_name = st.text_input("Coordenador (assinatura no PDF)", value="Yohann Risso", key="coord_det_pdf")
        detail_observation = st.text_area(
            "Observação do relatório detalhado",
            placeholder="Digite uma observação livre para aparecer no PDF detalhado.",
            height=100,
            key="report_observation_detail",
        )

        pdf_det = build_detailed_employee_pdf_bytes(
            employee_name=employee_name,
            employee_sector=employee_sector,
            employee_role=employee_role,
            month=month,
            weeks_iso=weeks_iso,
            weekly_rows_df=we,
            errors_df=errs_all,
            coordinator_name=coord_name,
            report_observation=detail_observation,
            logo_path="assets/logo.png",
            monitor_row=monitor_row,
            period_summary=period_summary,
        )

        safe_name = employee_name.strip().replace("/", "-")
        st.download_button(
            "⬇️ Baixar PDF detalhado (por funcionário)",
            data=pdf_det,
            file_name=f"detalhado_{safe_name}_{month}.pdf",
            mime="application/pdf",
        )
