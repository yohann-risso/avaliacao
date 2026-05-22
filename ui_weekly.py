import streamlit as st
import pandas as pd
from datetime import date, datetime

from constants import WEEKLY_CRITERIA, SEVERITIES, DEFAULT_ERROR_TYPES
from theme import (
    mark_operation_status,
    render_divider,
    render_focus_strip,
    render_operation_status,
    render_page_header,
    render_progress_panel,
    render_section_header,
    render_stage_grid,
    render_status_cards,
    render_status_notice,
)

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

from utils import (
    datetime_iso_to_br,
    month_label_to_br,
    week_label,
    monday_of,
    brl,
    competencia_from_week_start,
    monthly_cap_to_week_value,
    pay_band_multiplier,
    pct_br,
    severity_label,
    strip_embedded_justification_block,
)
from db import (
    list_active_employees,
    list_active_leadership_evaluators,
    get_weekly_eval,
    get_last_weekly_eval,
    list_weekly_eval_basis,
    upsert_weekly_eval,
    upsert_weekly_evals,
    add_weekly_error,
    list_weekly_errors,
    delete_weekly_error,
    list_last_weekly,
)
from rules import suggest_taxa_erros_pct


# -----------------------------
# Helpers
# -----------------------------
CRITERIA_RULES = {
    "Assiduidade": {
        "100%": "sem faltas e sem atrasos relevantes",
        "80%": "pequenos desvios pontuais, sem impacto relevante",
        "50%": "recorrência moderada de atrasos/ausências",
        "0%": "desvio grave ou reincidente",
    },
    "Qualidade": {
        "100%": "sem retrabalho ou divergência relevante",
        "80%": "até pequenos desvios corrigidos rapidamente",
        "50%": "retrabalho recorrente ou falhas com impacto moderado",
        "0%": "falha grave com impacto claro",
    },
    "Taxa de Erros": {
        "100%": "log limpo ou impacto irrelevante",
        "80%": "poucos erros leves/médios",
        "50%": "erros recorrentes ou impacto operacional",
        "0%": "erro crítico ou reincidência grave",
    },
    "Produtividade / Eficiência": {
        "100%": "ritmo consistente e aderente à meta",
        "80%": "leve oscilação sem comprometer a operação",
        "50%": "abaixo da meta com frequência",
        "0%": "desempenho muito abaixo do esperado",
    },
    "Comportamento": {
        "100%": "boa disciplina, colaboração e aderência ao POP",
        "80%": "pequenos pontos de ajuste, sem impacto relevante",
        "50%": "postura inconsistente ou ruído frequente",
        "0%": "conduta grave ou recorrente",
    },
}


def band_multiplier(pct: float) -> float:
    return pay_band_multiplier(pct, PAY_BANDS)


def band_label(mult: float) -> str:
    return pct_br(mult * 100, 0)


def pct_help(label: str) -> str:
    return (
        f"Defina o **resultado (%)** do quesito **{label}**. "
        "O pagamento é aplicado por **faixas** (0/25/50/75/100%)."
    )


def just_area(label: str, default: str, placeholder: str, key: str):
    if key not in st.session_state:
        st.session_state[key] = str(default or "")

    txt = st.text_area(
        f"Justificativa — {label}*",
        height=95,
        placeholder=placeholder,
        key=key,
    )
    st.caption(f"Caracteres: {len(txt.strip())} (recomendado ≥ 25)")
    return txt


def safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return float(default)


def safe_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return int(default)


def normalize_text(s: str) -> str:
    return str(s or "").strip()


def get_prev_defaults_row(employee_id: int, ws_iso: str):
    existing = get_weekly_eval(employee_id, ws_iso)
    if not existing.empty:
        return existing.iloc[0], "current"
    prev = get_last_weekly_eval(employee_id, ws_iso)
    if not prev.empty:
        return prev.iloc[0], "previous"
    return None, None


def empty_weekly_payload(source: str | None = None) -> dict:
    return {
        "source": source,
        "assiduidade": 100.0,
        "qualidade": 100.0,
        "taxa_erros": 100.0,
        "produtividade": 100.0,
        "comportamento": 100.0,
        "items_count": 0,
        "notes": "",
        "evaluator": "",
        "justs": {
            "assiduidade": "",
            "qualidade": "",
            "taxa_erros": "",
            "produtividade": "",
            "comportamento": "",
        }
    }


def weekly_payload_from_row(row: pd.Series, source: str | None = None) -> dict:
    payload = empty_weekly_payload(source)
    payload.update({
        "assiduidade": safe_float(row.get("assiduidade_pct", 100), 100),
        "qualidade": safe_float(row.get("qualidade_pct", 100), 100),
        "taxa_erros": safe_float(row.get("taxa_erros_pct", 100), 100),
        "produtividade": safe_float(row.get("produtividade_pct", 100), 100),
        "comportamento": safe_float(row.get("comportamento_pct", 100), 100),
        "items_count": safe_int(row.get("items_count", 0), 0),
        "notes": strip_embedded_justification_block(
            normalize_text(row.get("notes", "")),
            "JUSTIFICATIVAS (SEMANA)",
        ),
        "evaluator": normalize_text(row.get("evaluator", "")),
        "justs": {
            "assiduidade": normalize_text(row.get("assiduidade_just", "")),
            "qualidade": normalize_text(row.get("qualidade_just", "")),
            "taxa_erros": normalize_text(row.get("taxa_erros_just", "")),
            "produtividade": normalize_text(row.get("produtividade_just", "")),
            "comportamento": normalize_text(row.get("comportamento_just", "")),
        }
    })
    return payload


def build_default_payload(employee_id: int, ws_iso: str) -> dict:
    row, source = get_prev_defaults_row(employee_id, ws_iso)
    if row is None:
        return empty_weekly_payload(source)
    return weekly_payload_from_row(row, source)


def build_default_payloads(employee_ids, ws_iso: str) -> dict[int, dict]:
    basis = list_weekly_eval_basis([int(v) for v in employee_ids], ws_iso)
    payloads = {}
    if basis.empty:
        return payloads

    for _, row in basis.iterrows():
        source = normalize_text(row.get("basis_source", "")) or None
        payloads[int(row["employee_id"])] = weekly_payload_from_row(row, source)
    return payloads


def compute_quality_pct_from_errors(error_rows: list[dict], base: float = 100.0) -> float:
    score = float(base)

    for r in error_rows:
        sev = str(r.get("severity", "")).upper()
        qty = safe_int(r.get("qty", 1), 1)

        if sev == "CRITICO":
            score -= 40 * qty
        elif sev == "ALTO":
            score -= 18 * qty
        elif sev == "MEDIO":
            score -= 8 * qty
        elif sev == "BAIXO":
            score -= 3 * qty

    return max(0.0, min(100.0, score))


def compute_behavior_pct_from_errors(error_rows: list[dict], base: float = 100.0) -> float:
    score = float(base)

    for r in error_rows:
        sev = str(r.get("severity", "")).upper()
        qty = safe_int(r.get("qty", 1), 1)

        if sev == "CRITICO":
            score -= 20 * qty
        elif sev == "ALTO":
            score -= 10 * qty
        elif sev == "MEDIO":
            score -= 4 * qty

    return max(0.0, min(100.0, score))


def compute_productivity_pct(items_count: int, previous_pct: float = 100.0) -> float:
    # Heurística simples e conservadora:
    # - sem volume informado: mantém histórico
    # - com volume: puxa levemente para 100
    prev = safe_float(previous_pct, 100)
    if items_count <= 0:
        return prev
    if items_count >= 300:
        return min(100.0, max(prev, 95.0))
    if items_count >= 150:
        return min(100.0, max(prev, 90.0))
    if items_count >= 50:
        return min(100.0, max(prev, 85.0))
    return prev


def compute_assiduidade_pct(previous_pct: float = 100.0) -> float:
    return safe_float(previous_pct, 100.0)


def suggest_full_evaluation(role: str, items_count: int, error_rows: list[dict], previous_payload: dict) -> dict:
    prev_ass = previous_payload.get("assiduidade", 100.0)
    prev_qual = previous_payload.get("qualidade", 100.0)
    prev_prod = previous_payload.get("produtividade", 100.0)
    prev_comp = previous_payload.get("comportamento", 100.0)

    taxa_obj = suggest_taxa_erros_pct(
        role=str(role),
        items_count=int(items_count),
        weekly_errors_rows=[
            {
                "error_type": r.get("error_type"),
                "severity": r.get("severity"),
                "qty": r.get("qty"),
            }
            for r in error_rows
        ],
        strict_critical_zero=True,
        factor=12.0,
    )

    out = {
        "assiduidade": compute_assiduidade_pct(prev_ass),
        "qualidade": compute_quality_pct_from_errors(error_rows, prev_qual),
        "taxa_erros": float(taxa_obj.suggested_pct),
        "produtividade": compute_productivity_pct(items_count, prev_prod),
        "comportamento": compute_behavior_pct_from_errors(error_rows, prev_comp),
        "reason_taxa": str(taxa_obj.reason),
    }
    return out


def build_auto_justifications(
    employee_name: str,
    pcts: dict,
    items_count: int,
    error_rows: list[dict],
    previous_payload: dict,
) -> dict:
    qtd_erros = sum(safe_int(r.get("qty", 1), 1) for r in error_rows)
    criticos = sum(safe_int(r.get("qty", 1), 1) for r in error_rows if str(r.get("severity", "")).upper() == "CRITICO")
    altos = sum(safe_int(r.get("qty", 1), 1) for r in error_rows if str(r.get("severity", "")).upper() == "ALTO")
    medios = sum(safe_int(r.get("qty", 1), 1) for r in error_rows if str(r.get("severity", "")).upper() == "MEDIO")
    baixos = sum(safe_int(r.get("qty", 1), 1) for r in error_rows if str(r.get("severity", "")).upper() == "BAIXO")

    justs = {}

    ass = safe_float(pcts.get("assiduidade", 100), 100)
    if ass >= 95:
        justs["assiduidade"] = "Sem indícios de desvio relevante de assiduidade no período avaliado, mantendo regularidade compatível com a operação."
    elif ass >= 80:
        justs["assiduidade"] = "Apresentou pequenos desvios pontuais de assiduidade, sem impacto operacional relevante no período."
    else:
        justs["assiduidade"] = "Houve desvios relevantes de assiduidade no período, exigindo atenção e acompanhamento mais próximo."

    qual = safe_float(pcts.get("qualidade", 100), 100)
    if qtd_erros == 0 and qual >= 95:
        justs["qualidade"] = "Manteve boa qualidade na execução, sem registro de retrabalho ou divergência relevante no período."
    else:
        justs["qualidade"] = (
            f"Qualidade impactada pelo registro de {qtd_erros} ocorrência(s) no período "
            f"(baixo: {baixos}, médio: {medios}, alto: {altos}, crítico: {criticos}), "
            "demandando reforço de atenção e aderência ao processo."
        )

    taxa = safe_float(pcts.get("taxa_erros", 100), 100)
    if qtd_erros == 0 and taxa >= 95:
        justs["taxa_erros"] = "Sem registros relevantes no log de erros no período, mantendo desempenho compatível com o esperado para a operação."
    else:
        justs["taxa_erros"] = (
            f"A taxa de erros foi impactada por {qtd_erros} ocorrência(s) registradas no período, "
            "com necessidade de reforço em conferência, execução e prevenção de reincidência."
        )

    prod = safe_float(pcts.get("produtividade", 100), 100)
    if items_count > 0:
        if prod >= 95:
            justs["produtividade"] = f"Manteve bom ritmo operacional no período, com {items_count} item(ns)/peça(s) informados e aderência consistente ao fluxo esperado."
        elif prod >= 80:
            justs["produtividade"] = f"Apresentou produtividade adequada, porém com oscilação pontual no período de {items_count} item(ns)/peça(s) informados."
        else:
            justs["produtividade"] = f"Produtividade abaixo do esperado frente ao volume informado de {items_count} item(ns)/peça(s), exigindo acompanhamento mais próximo."
    else:
        justs["produtividade"] = "Sem volume informado no período, mantendo como referência o histórico recente e a percepção operacional."

    comp = safe_float(pcts.get("comportamento", 100), 100)
    if criticos == 0 and altos == 0 and comp >= 95:
        justs["comportamento"] = "Manteve postura compatível com a rotina operacional, com boa aderência ao fluxo, disciplina e colaboração com a equipe."
    elif comp >= 80:
        justs["comportamento"] = "Apresentou comportamento geral adequado, com pontos pontuais de ajuste e necessidade de reforço de consistência operacional."
    else:
        justs["comportamento"] = "O comportamento no período exigiu maior atenção, com necessidade de reforço de disciplina operacional, alinhamento e aderência ao processo."

    return justs


def build_template_justifications() -> dict:
    return build_criterion_template_justifications()


WEEKLY_JUSTIFICATION_MODELS = {
    "assiduidade": {
        "excelente": "Manteve assiduidade plena no período, sem faltas, atrasos ou saídas antecipadas que impactassem a rotina operacional.",
        "adequado": "Manteve assiduidade adequada, com eventual ajuste pontual controlado e sem impacto relevante para a operação.",
        "atencao": "Apresentou ocorrência pontual de assiduidade no período, exigindo acompanhamento para evitar reincidência.",
        "critico": "Teve desvios relevantes de assiduidade, com impacto na rotina e necessidade de alinhamento imediato.",
    },
    "qualidade": {
        "excelente": "Executou as atividades com padrão consistente de qualidade, sem retrabalho ou divergência relevante registrada.",
        "adequado": "Manteve qualidade adequada na execução, com pequenos ajustes pontuais dentro do esperado para a operação.",
        "atencao": "Apresentou desvios de qualidade que exigiram correção e reforço de atenção aos procedimentos.",
        "critico": "A qualidade ficou abaixo do esperado, com necessidade de acompanhamento próximo e plano de correção.",
    },
    "taxa_erros": {
        "excelente": "Não houve registro relevante no log de erros, mantendo desempenho compatível com o padrão esperado.",
        "adequado": "Houve ocorrência pontual controlada, sem impacto significativo no resultado geral da semana.",
        "atencao": "A taxa de erros foi impactada por ocorrências no período, exigindo reforço em conferência e prevenção de reincidência.",
        "critico": "Os erros registrados impactaram significativamente o resultado, exigindo ação corretiva imediata e acompanhamento.",
    },
    "produtividade": {
        "excelente": "Manteve ritmo produtivo consistente, com boa aderência ao fluxo e ao volume esperado para a semana.",
        "adequado": "Apresentou produtividade adequada, com oscilação pontual sem prejuízo relevante ao fluxo operacional.",
        "atencao": "A produtividade apresentou queda ou instabilidade no período, exigindo acompanhamento dos gargalos e rotina de execução.",
        "critico": "A produtividade ficou abaixo do esperado, com impacto no fluxo e necessidade de plano de recuperação.",
    },
    "comportamento": {
        "excelente": "Manteve postura adequada, colaborativa e aderente aos procedimentos e à disciplina operacional.",
        "adequado": "Apresentou comportamento geral adequado, com pontos pontuais de ajuste sem impacto relevante na equipe.",
        "atencao": "Foram observados pontos de comportamento que exigem alinhamento, reforço de disciplina e melhoria de comunicação.",
        "critico": "O comportamento no período exigiu intervenção, com necessidade de alinhamento imediato e acompanhamento próximo.",
    },
}


def evaluator_options_from_df(df: pd.DataFrame) -> list[str]:
    if df is None or df.empty or "name" not in df.columns:
        return []

    return sorted(
        {
            str(name).strip()
            for name in df["name"].dropna().astype(str).tolist()
            if str(name).strip()
        }
    )


def selected_evaluator_index(options: list[str], default: str = "") -> int:
    if not options:
        return 0

    cleaned = str(default or "").strip()
    if cleaned in options:
        return options.index(cleaned)

    return 0


def template_tier_from_pct(pct: float) -> str:
    p = safe_float(pct, 100)
    if p >= 91:
        return "excelente"
    if p >= 81:
        return "adequado"
    if p >= 71:
        return "atencao"
    return "critico"


def build_criterion_template_justifications(pcts: dict | None = None, model: str = "Resultado atual") -> dict:
    tier_by_model = {
        "Padrão 100%": "excelente",
        "Revisão pontual": "adequado",
        "Acompanhamento": "atencao",
        "Crítico": "critico",
    }

    pcts = pcts or {}
    out = {}
    for key, templates in WEEKLY_JUSTIFICATION_MODELS.items():
        tier = tier_by_model.get(model)
        if tier is None:
            pct_key = "taxa_erros" if key == "taxa_erros" else key
            tier = template_tier_from_pct(pcts.get(pct_key, 100))
        out[key] = templates[tier]
    return out


WEEKLY_JUST_AREA_KEYS = {
    "assiduidade": "wk_assid_just_area",
    "qualidade": "wk_qual_just_area",
    "taxa_erros": "wk_err_just_area",
    "produtividade": "wk_prod_just_area",
    "comportamento": "wk_comp_just_area",
}

WEEKLY_SLIDER_KEYS = ["assiduidade", "qualidade", "produtividade", "comportamento"]


def apply_weekly_pcts(pcts: dict):
    clean = {
        key: safe_float((pcts or {}).get(key, 100), 100)
        for key in WEEKLY_SLIDER_KEYS
    }
    st.session_state["wk_pcts"] = clean
    for key, value in clean.items():
        st.session_state[f"wk_{key}"] = int(round(value))


def apply_weekly_justifications(justs: dict):
    clean = {
        key: str((justs or {}).get(key, "") or "")
        for key in WEEKLY_JUST_AREA_KEYS
    }
    st.session_state["wk_justs"] = clean
    for key, area_key in WEEKLY_JUST_AREA_KEYS.items():
        st.session_state[area_key] = clean[key]


def apply_weekly_notes(notes: str):
    clean = str(notes or "")
    st.session_state["wk_notes"] = clean
    st.session_state["wk_notes_area"] = clean


def request_weekly_entry_sync():
    st.session_state["wk_sync_entry_inputs"] = True


def sync_weekly_entry_inputs(items_default: int, taxa_default: float):
    should_sync = bool(st.session_state.pop("wk_sync_entry_inputs", False))
    if should_sync or "wk_items_count_input" not in st.session_state:
        st.session_state["wk_items_count_input"] = int(st.session_state.get("wk_items_count", items_default))
    if should_sync or "wk_taxa_erros_pct_input" not in st.session_state:
        st.session_state["wk_taxa_erros_pct_input"] = float(st.session_state.get("wk_taxa_erros_pct", taxa_default))


def row_pcts_from_mass_row(row: pd.Series) -> dict:
    return {
        "assiduidade": safe_float(row.get("Assiduidade (%)", 100), 100),
        "qualidade": safe_float(row.get("Qualidade (%)", 100), 100),
        "taxa_erros": safe_float(row.get("Taxa Erros (%)", 100), 100),
        "produtividade": safe_float(row.get("Prod/Efic (%)", 100), 100),
        "comportamento": safe_float(row.get("Comportamento (%)", 100), 100),
    }


def apply_mass_template_justifications(df: pd.DataFrame, selected_mask, model: str) -> pd.DataFrame:
    out = df.copy()
    for idx in out[selected_mask].index:
        justs = build_criterion_template_justifications(row_pcts_from_mass_row(out.loc[idx]), model)
        out.loc[idx, "Assiduidade Just."] = justs["assiduidade"]
        out.loc[idx, "Qualidade Just."] = justs["qualidade"]
        out.loc[idx, "Taxa Erros Just."] = justs["taxa_erros"]
        out.loc[idx, "Produtividade Just."] = justs["produtividade"]
        out.loc[idx, "Comportamento Just."] = justs["comportamento"]
    return out


def score_from_pcts(pcts: dict) -> float:
    vals = [
        safe_float(pcts.get("assiduidade", 100), 100),
        safe_float(pcts.get("qualidade", 100), 100),
        safe_float(pcts.get("taxa_erros", 100), 100),
        safe_float(pcts.get("produtividade", 100), 100),
        safe_float(pcts.get("comportamento", 100), 100),
    ]
    return round(sum(vals) / len(vals), 1)


def exception_status(score: float, taxa_erros_pct: float, critical_errors: int) -> tuple[str, int]:
    if critical_errors > 0 or taxa_erros_pct <= 50 or score < 75:
        return "🔴 Analisar", 1
    if taxa_erros_pct < 90 or score < 90:
        return "🟡 Revisar", 2
    return "🟢 Auto", 3


def build_notes_with_justs(row: pd.Series) -> str:
    notes = strip_embedded_justification_block(
        str(row.get("Notas", "") or "").strip(),
        "JUSTIFICATIVAS (SEMANA)",
    )

    just_block = (
        "JUSTIFICATIVAS (SEMANA)\n"
        f"- Assiduidade: {str(row.get('Assiduidade Just.', '')).strip()}\n"
        f"- Qualidade: {str(row.get('Qualidade Just.', '')).strip()}\n"
        f"- Taxa de Erros: {str(row.get('Taxa Erros Just.', '')).strip()}\n"
        f"- Produtividade/Eficiência: {str(row.get('Produtividade Just.', '')).strip()}\n"
        f"- Comportamento: {str(row.get('Comportamento Just.', '')).strip()}\n"
    )

    return (notes + "\n\n" + just_block).strip()


def mass_row_to_weekly_payload(row: pd.Series, ws_iso: str) -> dict:
    return {
        "employee_id": int(row["employee_id"]),
        "week_start_iso": ws_iso,
        "evaluator": str(row.get("Avaliador", "") or "").strip(),
        "notes": build_notes_with_justs(row),
        "assiduidade_pct": float(row["Assiduidade (%)"]),
        "qualidade_pct": float(row["Qualidade (%)"]),
        "taxa_erros_pct": float(row["Taxa Erros (%)"]),
        "produtividade_pct": float(row["Prod/Efic (%)"]),
        "comportamento_pct": float(row["Comportamento (%)"]),
        "efficiency_pct": float(row["Prod/Efic (%)"]),
        "items_count": int(row["Itens"] or 0),
        "assiduidade_just": str(row.get("Assiduidade Just.", "") or "").strip(),
        "qualidade_just": str(row.get("Qualidade Just.", "") or "").strip(),
        "taxa_erros_just": str(row.get("Taxa Erros Just.", "") or "").strip(),
        "produtividade_just": str(row.get("Produtividade Just.", "") or "").strip(),
        "comportamento_just": str(row.get("Comportamento Just.", "") or "").strip(),
    }


def save_mass_selected_rows(selected_rows: pd.DataFrame, ws_iso: str) -> tuple[int, list[str]]:
    errors = []
    rows_to_save = []

    for _, row in selected_rows.iterrows():
        problems = validate_mass_row(row)
        if problems:
            errors.append(f"{row['Nome']}: " + "; ".join(problems))
            continue

        rows_to_save.append(mass_row_to_weekly_payload(row, ws_iso))

    if rows_to_save:
        upsert_weekly_evals(rows_to_save)

    return len(rows_to_save), errors


def validate_mass_row(row: pd.Series) -> list[str]:
    problems = []

    required_justs = [
        "Assiduidade Just.",
        "Qualidade Just.",
        "Taxa Erros Just.",
        "Produtividade Just.",
        "Comportamento Just.",
    ]

    for col in required_justs:
        if not str(row.get(col, "")).strip():
            problems.append(f"{col} vazio")

    pct_cols = [
        "Assiduidade (%)",
        "Qualidade (%)",
        "Taxa Erros (%)",
        "Prod/Efic (%)",
        "Comportamento (%)",
    ]

    for col in pct_cols:
        try:
            v = float(row.get(col, 0))
            if v < 0 or v > 100:
                problems.append(f"{col} fora de 0–100")
        except Exception:
            problems.append(f"{col} inválido")

    try:
        items = int(row.get("Itens", 0) or 0)
        if items < 0:
            problems.append("Itens negativo")
    except Exception:
        problems.append("Itens inválido")

    return problems


MASS_PCT_COLS = [
    "Assiduidade (%)",
    "Qualidade (%)",
    "Taxa Erros (%)",
    "Prod/Efic (%)",
    "Comportamento (%)",
]

MASS_JUST_COLS = [
    "Assiduidade Just.",
    "Qualidade Just.",
    "Taxa Erros Just.",
    "Produtividade Just.",
    "Comportamento Just.",
]


def now_br() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def format_pct(value) -> str:
    return pct_br(value, 1)


def mass_context_key(filtered_emp: pd.DataFrame, ws_iso: str, sector_filter: str, role_filter: str, only_monitors: bool) -> str:
    ids = ",".join(str(int(v)) for v in filtered_emp["id"].tolist())
    return f"{ws_iso}|{sector_filter}|{role_filter}|{int(bool(only_monitors))}|{ids}"


def bump_mass_editor_version():
    st.session_state["mass_editor_version"] = int(st.session_state.get("mass_editor_version", 0)) + 1


def normalize_mass_eval_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out

    if "Selecionar" in out.columns:
        out["Selecionar"] = out["Selecionar"].fillna(False).astype(bool)

    for col in MASS_PCT_COLS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).clip(0, 100).round(1)

    if "Itens" in out.columns:
        out["Itens"] = pd.to_numeric(out["Itens"], errors="coerce").fillna(0).clip(lower=0).round(0).astype(int)

    for col in ["Avaliador", "Notas", *MASS_JUST_COLS]:
        if col in out.columns:
            out[col] = out[col].fillna("").astype(str)

    for idx in out.index:
        pcts = row_pcts_from_mass_row(out.loc[idx])
        score = score_from_pcts(pcts)
        status, prioridade = exception_status(score, pcts["taxa_erros"], 0)
        out.loc[idx, "Score"] = score
        out.loc[idx, "Status"] = status
        out.loc[idx, "Prioridade"] = prioridade

    return out


def coerce_mass_evaluators(df: pd.DataFrame, evaluator_options: list[str]) -> pd.DataFrame:
    out = df.copy()
    if out.empty or "Avaliador" not in out.columns or not evaluator_options:
        return out

    allowed = set(evaluator_options)
    fallback = evaluator_options[0]
    out["Avaliador"] = out["Avaliador"].apply(
        lambda value: str(value).strip() if str(value or "").strip() in allowed else fallback
    )
    return out


def build_mass_validation_df(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if df.empty:
        return pd.DataFrame(columns=["Funcionário", "Status", "Pendência"])

    selected = df[df["Selecionar"].fillna(False).astype(bool)].copy()
    for _, row in selected.iterrows():
        problems = validate_mass_row(row)
        if problems:
            rows.append({
                "Funcionário": str(row.get("Nome", "")),
                "Status": str(row.get("Status", "")),
                "Pendência": "; ".join(problems),
            })

    return pd.DataFrame(rows)


def mass_total_preview(df: pd.DataFrame, competencia: str) -> float:
    selected = df[df["Selecionar"].fillna(False).astype(bool)].copy()
    total = 0.0
    for _, row in selected.iterrows():
        pcts = row_pcts_from_mass_row(row)
        for key, _label, _weekly_value, monthly_cap in WEEKLY_CRITERIA:
            pct_key = "produtividade" if key == "produtividade" else key
            pct = pcts.get(pct_key, 0)
            mult = band_multiplier(pct)
            week_value = monthly_cap_to_week_value(float(monthly_cap), competencia)
            total += float(week_value) * mult
    return total


def reset_mass_editor_with_df(df: pd.DataFrame, message: str = ""):
    st.session_state["mass_eval_df"] = normalize_mass_eval_df(df)
    if message:
        st.session_state["mass_feedback"] = message
    bump_mass_editor_version()
    st.rerun()


def apply_mass_editor_changes(df: pd.DataFrame, editor_state) -> pd.DataFrame:
    out = df.copy()
    if out.empty or not isinstance(editor_state, dict):
        return normalize_mass_eval_df(out)

    edited_rows = editor_state.get("edited_rows", {})
    if not isinstance(edited_rows, dict):
        return normalize_mass_eval_df(out)

    for row_position, changes in edited_rows.items():
        if not isinstance(changes, dict):
            continue
        try:
            row_idx = int(row_position)
        except (TypeError, ValueError):
            continue
        if row_idx < 0 or row_idx >= len(out):
            continue

        for col, value in changes.items():
            if col in out.columns:
                out.iat[row_idx, out.columns.get_loc(col)] = value

    return normalize_mass_eval_df(out)


def sync_mass_editor_from_state(editor_key: str):
    current_df = st.session_state.get("mass_eval_df")
    if not isinstance(current_df, pd.DataFrame):
        return

    st.session_state["mass_eval_df"] = apply_mass_editor_changes(
        current_df,
        st.session_state.get(editor_key, {}),
    )


def queue_mass_operation(kind: str, ctx_key: str):
    st.session_state["mass_pending_action"] = {
        "kind": kind,
        "ctx_key": ctx_key,
        "queued_at": now_br(),
    }
    st.rerun()


def process_pending_mass_operation(
    filtered_emp: pd.DataFrame,
    ws_iso: str,
    ws_date,
    ctx_key: str,
    evaluator_options: list[str],
) -> bool:
    pending = st.session_state.pop("mass_pending_action", None)
    if not pending:
        return False

    if pending.get("ctx_key") != ctx_key:
        st.session_state["mass_feedback"] = "A operação foi cancelada porque os filtros mudaram antes do processamento."
        st.rerun()

    kind = pending.get("kind")

    try:
        if kind == "copy_previous":
            base_df = st.session_state.get("mass_eval_df", pd.DataFrame()).copy()
            selected_mask = base_df["Selecionar"].fillna(False).astype(bool)
            with st.spinner("Buscando últimas avaliações no banco e bloqueando a tabela até concluir..."):
                payloads = build_default_payloads(base_df.loc[selected_mask, "employee_id"].tolist(), ws_iso)
                for idx in base_df[selected_mask].index:
                    employee_id = int(base_df.loc[idx, "employee_id"])
                    prev = payloads.get(employee_id, empty_weekly_payload())
                    base_df.loc[idx, "Itens"] = prev["items_count"]
                    base_df.loc[idx, "Assiduidade (%)"] = prev["assiduidade"]
                    base_df.loc[idx, "Qualidade (%)"] = prev["qualidade"]
                    base_df.loc[idx, "Taxa Erros (%)"] = prev["taxa_erros"]
                    base_df.loc[idx, "Prod/Efic (%)"] = prev["produtividade"]
                    base_df.loc[idx, "Comportamento (%)"] = prev["comportamento"]
                    base_df.loc[idx, "Avaliador"] = prev["evaluator"]
                    base_df.loc[idx, "Assiduidade Just."] = prev["justs"]["assiduidade"]
                    base_df.loc[idx, "Qualidade Just."] = prev["justs"]["qualidade"]
                    base_df.loc[idx, "Taxa Erros Just."] = prev["justs"]["taxa_erros"]
                    base_df.loc[idx, "Produtividade Just."] = prev["justs"]["produtividade"]
                    base_df.loc[idx, "Comportamento Just."] = prev["justs"]["comportamento"]
                    base_df.loc[idx, "Notas"] = prev["notes"]
            st.session_state["mass_eval_df"] = normalize_mass_eval_df(
                coerce_mass_evaluators(base_df, evaluator_options)
            )
            st.session_state["mass_feedback"] = "Última avaliação/base anterior copiada para os selecionados."
            bump_mass_editor_version()
            st.rerun()

        if kind == "reload_db":
            with st.spinner("Recarregando dados salvos no banco e bloqueando a tabela até concluir..."):
                loaded_df = coerce_mass_evaluators(
                    build_mass_eval_df(filtered_emp, ws_iso),
                    evaluator_options,
                )
            st.session_state["mass_eval_df"] = loaded_df
            st.session_state["mass_eval_loaded_df"] = loaded_df.copy()
            st.session_state["mass_eval_loaded_at"] = now_br()
            st.session_state["mass_feedback"] = "Dados recarregados do banco; edições não salvas foram descartadas."
            bump_mass_editor_version()
            st.rerun()

        if kind == "save_batch":
            edited = normalize_mass_eval_df(
                coerce_mass_evaluators(
                    st.session_state.get("mass_eval_df", pd.DataFrame()),
                    evaluator_options,
                )
            )
            selected_rows = edited[edited["Selecionar"].fillna(False).astype(bool)].copy()

            with st.spinner("Gravando avaliações selecionadas no banco e bloqueando a tabela até concluir..."):
                success_count, errors = save_mass_selected_rows(selected_rows, ws_iso)

            if errors:
                st.session_state["mass_save_errors"] = errors

            if success_count > 0:
                with st.spinner("Confirmando leitura dos dados gravados..."):
                    loaded_df = build_mass_eval_df(filtered_emp, ws_iso)
                st.session_state["mass_eval_df"] = loaded_df
                st.session_state["mass_eval_loaded_df"] = loaded_df.copy()
                st.session_state["mass_eval_loaded_at"] = now_br()
                bump_mass_editor_version()
                mark_operation_status(
                    "Avaliações em massa gravadas no banco",
                    f"{success_count} registro(s) salvo(s) para a semana {week_label(ws_date)}.",
                    "success",
                )
            else:
                st.session_state["mass_feedback"] = "Nenhuma avaliação foi salva. Confira a seleção e as pendências."
            st.rerun()

    except Exception as exc:
        st.session_state["mass_feedback"] = f"Operação interrompida: {exc}"
        st.rerun()

    return True


def build_mass_eval_df(employees_df: pd.DataFrame, ws_iso: str) -> pd.DataFrame:
    rows = []
    payloads = build_default_payloads(employees_df["id"].tolist(), ws_iso)

    for _, emp_row in employees_df.iterrows():
        emp_id = int(emp_row["id"])
        payload = payloads.get(emp_id, empty_weekly_payload())
        source_label = {
            "current": "Banco",
            "previous": "Base anterior",
        }.get(payload.get("source"), "Novo")
        defaults = {
            "assiduidade_pct": payload["assiduidade"],
            "qualidade_pct": payload["qualidade"],
            "taxa_erros_pct": payload["taxa_erros"],
            "produtividade_pct": payload["produtividade"],
            "comportamento_pct": payload["comportamento"],
            "items_count": payload["items_count"],
            "evaluator": payload["evaluator"],
            "notes": payload["notes"],
            "assiduidade_just": payload["justs"]["assiduidade"],
            "qualidade_just": payload["justs"]["qualidade"],
            "taxa_erros_just": payload["justs"]["taxa_erros"],
            "produtividade_just": payload["justs"]["produtividade"],
            "comportamento_just": payload["justs"]["comportamento"],
        }

        score = round((
            defaults["assiduidade_pct"]
            + defaults["qualidade_pct"]
            + defaults["taxa_erros_pct"]
            + defaults["produtividade_pct"]
            + defaults["comportamento_pct"]
        ) / 5, 1)

        status, prioridade = exception_status(score, defaults["taxa_erros_pct"], 0)

        rows.append({
            "Selecionar": False,
            "Prioridade": prioridade,
            "Status": status,
            "Origem": source_label,
            "employee_id": emp_id,
            "Nome": str(emp_row["name"]),
            "Setor": str(emp_row["sector"]),
            "Função": str(emp_row["role"]),
            "Monitor": "SIM" if int(emp_row.get("is_monitor", 0)) == 1 else "NÃO",
            "Score": score,
            "Itens": defaults["items_count"],
            "Assiduidade (%)": defaults["assiduidade_pct"],
            "Qualidade (%)": defaults["qualidade_pct"],
            "Taxa Erros (%)": defaults["taxa_erros_pct"],
            "Prod/Efic (%)": defaults["produtividade_pct"],
            "Comportamento (%)": defaults["comportamento_pct"],
            "Avaliador": defaults["evaluator"],
            "Assiduidade Just.": defaults["assiduidade_just"],
            "Qualidade Just.": defaults["qualidade_just"],
            "Taxa Erros Just.": defaults["taxa_erros_just"],
            "Produtividade Just.": defaults["produtividade_just"],
            "Comportamento Just.": defaults["comportamento_just"],
            "Notas": defaults["notes"],
        })

    out = pd.DataFrame(rows).sort_values(["Prioridade", "Score", "Nome"], ascending=[True, True, True]).reset_index(drop=True)
    return normalize_mass_eval_df(out)


def render_rules_block():
    with st.expander("Regras rápidas dos critérios"):
        for crit, rules in CRITERIA_RULES.items():
            st.markdown(f"**{crit}**")
            st.write(
                f"100% = {rules['100%']}  \n"
                f"80% = {rules['80%']}  \n"
                f"50% = {rules['50%']}  \n"
                f"0% = {rules['0%']}"
            )


def render_live_preview_sidebar(competencia, defaults):
    with st.sidebar:
        st.markdown("### 👁️ Prévia ao vivo")

        pcts = dict(st.session_state.get("wk_pcts", {}))
        for key in WEEKLY_SLIDER_KEYS:
            widget_key = f"wk_{key}"
            if widget_key in st.session_state:
                pcts[key] = st.session_state[widget_key]
        taxa_final = float(st.session_state.get(
            "wk_taxa_erros_pct_input",
            st.session_state.get("wk_taxa_erros_pct", defaults["taxa_erros"]),
        ))

        total = 0.0
        short_labels = {
            "assiduidade": "Assid.",
            "qualidade": "Qualid.",
            "taxa_erros": "Erros",
            "produtividade": "Prod/Efic",
            "comportamento": "Comp.",
        }

        for key, label, _weekly_value, monthly_cap in WEEKLY_CRITERIA:
            if key == "taxa_erros":
                pct = taxa_final
            elif key == "produtividade":
                pct = float(pcts.get("produtividade", defaults["produtividade"]))
                label = "Produtividade / Eficiência"
            else:
                pct = float(pcts.get(key, defaults[key]))

            mult = band_multiplier(pct)
            week_value = monthly_cap_to_week_value(float(monthly_cap), competencia)
            pay = float(week_value) * mult
            total += pay

            st.caption(f"**{short_labels.get(key, label)}** · {pct_br(pct, 0)} · faixa {band_label(mult)} · {brl(pay)}")

        score = score_from_pcts({
            "assiduidade": pcts.get("assiduidade", defaults["assiduidade"]),
            "qualidade": pcts.get("qualidade", defaults["qualidade"]),
            "taxa_erros": taxa_final,
            "produtividade": pcts.get("produtividade", defaults["produtividade"]),
            "comportamento": pcts.get("comportamento", defaults["comportamento"]),
        })
        st.metric("Score geral", pct_br(score, 1))
        st.metric("Total estimado", brl(total))


def render_week_priority_ranking(emp: pd.DataFrame, ws_iso: str):
    rows = []
    payloads = build_default_payloads(emp["id"].tolist(), ws_iso)
    for _, r in emp.iterrows():
        payload = payloads.get(int(r["id"]), empty_weekly_payload())
        score = score_from_pcts(payload)
        status, prioridade = exception_status(score, payload["taxa_erros"], 0)

        rows.append({
            "Prioridade": prioridade,
            "Status": status,
            "Funcionário": str(r["name"]),
            "Setor": str(r["sector"]),
            "Função": str(r["role"]),
            "Score": score,
            "Taxa de Erros": payload["taxa_erros"],
            "Prod/Efic": payload["produtividade"],
        })

    df = pd.DataFrame(rows).sort_values(["Prioridade", "Score", "Taxa de Erros", "Funcionário"], ascending=[True, True, True, True]).reset_index(drop=True)
    df_display = df.copy()
    for col in ["Score", "Taxa de Erros", "Prod/Efic"]:
        df_display[col] = df_display[col].map(lambda v: pct_br(v, 1))

    with st.expander("Prioridade de avaliação da semana"):
        st.caption("Ordenação por exceção: analisar primeiro quem foge mais do padrão.")
        st.dataframe(df_display, width="stretch", hide_index=True)


def render_mass_weekly_tab(emp: pd.DataFrame, evaluator_options: list[str]):
    render_section_header(
        "Avaliação em massa",
        "Selecione vários funcionários, edite em formato de tabela e salve tudo em lote.",
        "Lote",
    )

    top1, top2, top3 = st.columns([1.2, 1.2, 1], gap="medium")
    with top1:
        d_mass = st.date_input("Data de referência (massa)", value=date.today(), format="DD/MM/YYYY", key="mass_date")
        ws_mass = monday_of(d_mass)
        ws_mass_iso = ws_mass.isoformat()
        competencia = competencia_from_week_start(ws_mass)
        st.caption(f"Semana: {week_label(ws_mass)}")
        st.caption(f"Competência: {month_label_to_br(competencia)}")

    with top2:
        sector_opts = ["(Todos)"] + sorted(emp["sector"].dropna().astype(str).unique().tolist())
        sector_filter = st.selectbox("Filtrar setor", sector_opts, key="mass_sector_filter")

        role_opts = ["(Todas)"] + sorted(emp["role"].dropna().astype(str).unique().tolist())
        role_filter = st.selectbox("Filtrar função", role_opts, key="mass_role_filter")

    with top3:
        only_monitors = st.toggle("Só monitores", value=False, key="mass_only_monitors")
        if st.session_state.get("mass_evaluator") not in evaluator_options:
            st.session_state["mass_evaluator"] = evaluator_options[0]
        evaluator_mass = st.selectbox(
            "Avaliador padrão",
            evaluator_options,
            key="mass_evaluator",
        )

    filtered_emp = emp.copy()

    if sector_filter != "(Todos)":
        filtered_emp = filtered_emp[filtered_emp["sector"] == sector_filter]

    if role_filter != "(Todas)":
        filtered_emp = filtered_emp[filtered_emp["role"] == role_filter]

    if only_monitors:
        filtered_emp = filtered_emp[filtered_emp["is_monitor"].astype(int) == 1]

    if filtered_emp.empty:
        st.info("Nenhum funcionário encontrado com os filtros atuais.")
        return

    ctx_key = mass_context_key(filtered_emp, ws_mass_iso, sector_filter, role_filter, only_monitors)
    if "mass_editor_version" not in st.session_state:
        st.session_state["mass_editor_version"] = 0

    if st.session_state.get("mass_eval_context") != ctx_key or "mass_eval_df" not in st.session_state:
        with st.spinner("Carregando avaliações e bases anteriores do banco..."):
            loaded_df = coerce_mass_evaluators(
                build_mass_eval_df(filtered_emp, ws_mass_iso),
                evaluator_options,
            )
        st.session_state["mass_eval_df"] = loaded_df
        st.session_state["mass_eval_loaded_df"] = loaded_df.copy()
        st.session_state["mass_eval_context"] = ctx_key
        st.session_state["mass_eval_loaded_at"] = now_br()
        bump_mass_editor_version()

    if process_pending_mass_operation(filtered_emp, ws_mass_iso, ws_mass, ctx_key, evaluator_options):
        return

    if st.session_state.get("mass_feedback"):
        render_status_notice(
            "Ação aplicada na tabela",
            st.session_state.pop("mass_feedback"),
            "success",
            "A alteração ainda fica em memória até salvar no banco.",
        )

    mass_save_errors = st.session_state.pop("mass_save_errors", [])
    if mass_save_errors:
        render_status_notice(
            "Algumas linhas não foram salvas",
            "Corrija as pendências e salve novamente.",
            "warning",
            f"{len(mass_save_errors)} pendência(s)",
        )
        with st.expander("Ver pendências do último salvamento"):
            for err in mass_save_errors:
                st.write(f"- {err}")

    render_status_notice(
        "Tabela carregada para edição",
        f"Semana {week_label(ws_mass)} | Competência {month_label_to_br(competencia)} | {len(filtered_emp)} funcionário(s) no filtro.",
        "info",
        f"Leitura do banco em {st.session_state.get('mass_eval_loaded_at', '-')}",
    )

    current_mass_df = normalize_mass_eval_df(st.session_state["mass_eval_df"].copy())
    selected_count = int(current_mass_df["Selecionar"].fillna(False).astype(bool).sum())
    invalid_df = build_mass_validation_df(current_mass_df)
    invalid_count = int(len(invalid_df))
    avg_score = current_mass_df["Score"].mean() if not current_mass_df.empty else 0.0
    selected_total = mass_total_preview(current_mass_df, competencia)
    ready_count = max(0, selected_count - invalid_count)
    ready_progress = round((ready_count / selected_count) * 100, 1) if selected_count else 0.0

    render_progress_panel(
        "Progresso do lote",
        f"{ready_count}/{selected_count} selecionados prontos" if selected_count else "Nenhuma linha selecionada",
        "Marque as linhas que serão salvas; a validação aparece aqui antes do salvamento.",
        progress=ready_progress,
        tone="success" if selected_count and invalid_count == 0 else ("warning" if selected_count else "neutral"),
        meta=f"{ready_progress:.1f}% pronto" if selected_count else "Selecione linhas",
    )
    render_stage_grid([
        {
            "status": "Ativo",
            "title": "Filtros",
            "detail": f"{len(filtered_emp)} funcionários no recorte atual.",
            "tone": "info",
        },
        {
            "status": "Selecionados" if selected_count else "Pendente",
            "title": "Seleção",
            "detail": f"{selected_count} linhas marcadas para operação.",
            "tone": "success" if selected_count else "neutral",
        },
        {
            "status": "Pronto" if invalid_count == 0 else "Atenção",
            "title": "Validação",
            "detail": f"{invalid_count} pendências nos selecionados.",
            "tone": "success" if invalid_count == 0 else "warning",
        },
        {
            "status": "Prévia",
            "title": "Pagamento",
            "detail": f"{brl(selected_total)} estimado para selecionados.",
            "tone": "success" if selected_total else "neutral",
        },
    ])
    if invalid_count:
        render_focus_strip(
            "Corrigir pendências antes de salvar o lote.",
            "As linhas selecionadas precisam de percentuais válidos, avaliador e justificativas obrigatórias.",
            [
                {"label": f"{invalid_count} pendências", "tone": "danger"},
                {"label": f"Score médio {format_pct(avg_score)}", "tone": "warning"},
            ],
            "danger",
        )

    edit_tab, detail_tab = st.tabs(["Edição do lote", "Detalhes & KPIs"])

    with edit_tab:
        render_divider()
        render_section_header(
            "Ações rápidas",
            "As ações abaixo atualizam a tabela imediatamente e mantêm as alterações em memória até salvar.",
            "Operação",
        )

        base_df = coerce_mass_evaluators(st.session_state["mass_eval_df"].copy(), evaluator_options)
        a1, a2, a3, a4, a5, a6, a7 = st.columns(7, gap="small")

        if a1.button("Marcar todos", key="mass_select_all"):
            base_df["Selecionar"] = True
            reset_mass_editor_with_df(base_df, "Todos os funcionários visíveis foram selecionados.")

        if a2.button("Desmarcar", key="mass_unselect_all"):
            base_df["Selecionar"] = False
            reset_mass_editor_with_df(base_df, "Seleção removida.")

        if a3.button("Aplicar 100%", key="mass_apply_100"):
            selected_mask = base_df["Selecionar"].fillna(False).astype(bool)
            if not bool(selected_mask.any()):
                st.warning("Selecione pelo menos 1 funcionário.")
            else:
                base_df.loc[selected_mask, MASS_PCT_COLS] = 100
                reset_mass_editor_with_df(base_df, "Percentuais dos selecionados ajustados para 100%.")

        if a4.button("Aplicar 80%", key="mass_apply_80"):
            selected_mask = base_df["Selecionar"].fillna(False).astype(bool)
            if not bool(selected_mask.any()):
                st.warning("Selecione pelo menos 1 funcionário.")
            else:
                base_df.loc[selected_mask, MASS_PCT_COLS] = 80
                reset_mass_editor_with_df(base_df, "Percentuais dos selecionados ajustados para 80%.")

        if a5.button("Avaliador", key="mass_apply_evaluator"):
            selected_mask = base_df["Selecionar"].fillna(False).astype(bool)
            if not bool(selected_mask.any()):
                st.warning("Selecione pelo menos 1 funcionário.")
            else:
                base_df.loc[selected_mask, "Avaliador"] = str(evaluator_mass).strip()
                reset_mass_editor_with_df(base_df, "Avaliador padrão aplicado aos selecionados.")

        if a6.button("Última base", key="mass_copy_previous"):
            selected_mask = base_df["Selecionar"].fillna(False).astype(bool)
            if not bool(selected_mask.any()):
                st.warning("Selecione pelo menos 1 funcionário.")
            else:
                queue_mass_operation("copy_previous", ctx_key)

        if a7.button("Recarregar", key="mass_reload_db"):
            queue_mass_operation("reload_db", ctx_key)

        m1, m2 = st.columns([1.3, 1], gap="medium")
        with m1:
            mass_template_model = st.selectbox(
                "Modelo padrão de justificativa",
                ["Resultado atual", "Padrão 100%", "Revisão pontual", "Acompanhamento", "Crítico"],
                key="mass_template_model",
            )
        with m2:
            st.write("")
            if st.button("Aplicar justificativas aos selecionados", key="mass_apply_templates"):
                selected_mask = base_df["Selecionar"].fillna(False).astype(bool)
                if not bool(selected_mask.any()):
                    st.warning("Selecione pelo menos 1 funcionário.")
                else:
                    base_df = apply_mass_template_justifications(base_df, selected_mask, mass_template_model)
                    reset_mass_editor_with_df(base_df, "Justificativas padrão aplicadas aos selecionados.")

        render_divider()
        render_section_header(
            "Tabela de edição",
            "Altere uma vez e confira os indicadores abaixo; o banco só muda ao clicar em salvar.",
            "Edição",
        )

        mass_editor_key = f"mass_editor_{st.session_state.get('mass_editor_version', 0)}"
        st.data_editor(
            st.session_state["mass_eval_df"],
            width="stretch",
            hide_index=True,
            num_rows="fixed",
            column_order=[
                "Selecionar",
                "Status",
                "Origem",
                "Nome",
                "Setor",
                "Função",
                "Monitor",
                "Score",
                "Itens",
                "Assiduidade (%)",
                "Qualidade (%)",
                "Taxa Erros (%)",
                "Prod/Efic (%)",
                "Comportamento (%)",
                "Avaliador",
                "Assiduidade Just.",
                "Qualidade Just.",
                "Taxa Erros Just.",
                "Produtividade Just.",
                "Comportamento Just.",
                "Notas",
            ],
            column_config={
                "Selecionar": st.column_config.CheckboxColumn("Selecionar", pinned=True),
                "Prioridade": st.column_config.NumberColumn("Prioridade", disabled=True),
                "Status": st.column_config.TextColumn("Status", disabled=True),
                "Origem": st.column_config.TextColumn("Origem", disabled=True),
                "employee_id": st.column_config.NumberColumn("employee_id", disabled=True),
                "Nome": st.column_config.TextColumn("Nome", disabled=True, pinned=True),
                "Setor": st.column_config.TextColumn("Setor", disabled=True),
                "Função": st.column_config.TextColumn("Função", disabled=True),
                "Monitor": st.column_config.TextColumn("Monitor", disabled=True),
                "Score": st.column_config.NumberColumn("Score", disabled=True, format="%.1f"),
                "Itens": st.column_config.NumberColumn("Itens", min_value=0, step=1),
                "Assiduidade (%)": st.column_config.NumberColumn("Assiduidade (%)", min_value=0, max_value=100, step=5, format="%d"),
                "Qualidade (%)": st.column_config.NumberColumn("Qualidade (%)", min_value=0, max_value=100, step=5, format="%d"),
                "Taxa Erros (%)": st.column_config.NumberColumn("Taxa de Erros (%)", min_value=0, max_value=100, step=5, format="%d"),
                "Prod/Efic (%)": st.column_config.NumberColumn("Prod/Efic (%)", min_value=0, max_value=100, step=5, format="%d"),
                "Comportamento (%)": st.column_config.NumberColumn("Comportamento (%)", min_value=0, max_value=100, step=5, format="%d"),
                "Avaliador": st.column_config.SelectboxColumn(
                    "Avaliador",
                    options=evaluator_options,
                    width="medium",
                ),
                "Assiduidade Just.": st.column_config.TextColumn("Assiduidade Just.", width="large"),
                "Qualidade Just.": st.column_config.TextColumn("Qualidade Just.", width="large"),
                "Taxa Erros Just.": st.column_config.TextColumn("Taxa Erros Just.", width="large"),
                "Produtividade Just.": st.column_config.TextColumn("Produtividade Just.", width="large"),
                "Comportamento Just.": st.column_config.TextColumn("Comportamento Just.", width="large"),
                "Notas": st.column_config.TextColumn("Notas", width="large"),
            },
            key=mass_editor_key,
            on_change=sync_mass_editor_from_state,
            args=(mass_editor_key,),
        )

        edited = normalize_mass_eval_df(st.session_state["mass_eval_df"])
        st.session_state["mass_eval_df"] = edited.copy()

        selected_count = int(edited["Selecionar"].fillna(False).astype(bool).sum())
        invalid_df = build_mass_validation_df(edited)
        invalid_count = len(invalid_df)
        avg_score = edited["Score"].mean() if not edited.empty else 0
        selected_total = mass_total_preview(edited, competencia)

        render_status_cards([
            {
                "title": "Seleção",
                "value": f"{selected_count} funcionário(s)",
                "detail": "Somente selecionados entram no salvamento em lote.",
                "tone": "success" if selected_count else "neutral",
            },
            {
                "title": "Validação",
                "value": "Pronto" if invalid_count == 0 else f"{invalid_count} pendência(s)",
                "detail": "Justificativas, percentuais e itens são checados antes de gravar.",
                "tone": "success" if invalid_count == 0 else "warning",
            },
            {
                "title": "Score médio",
                "value": format_pct(avg_score),
                "detail": "Recalculado em memória a cada edição.",
                "tone": "info",
            },
            {
                "title": "Prévia selecionada",
                "value": brl(selected_total),
                "detail": "Estimativa semanal dos selecionados.",
                "tone": "info",
            },
        ])

        render_divider()
        render_section_header(
            "Salvar em lote",
            "Ao salvar, a aplicação grava cada avaliação selecionada na tabela weekly_evaluations.",
            "Banco",
        )

        if invalid_count:
            st.warning("Existem pendências nos selecionados. Veja a aba **Detalhes & KPIs** antes de salvar.")

        if st.button("Salvar selecionados no banco", type="primary", key="mass_save_batch"):
            selected_rows = edited[edited["Selecionar"] == True].copy()

            if selected_rows.empty:
                st.error("Selecione pelo menos 1 funcionário.")
                st.stop()

            queue_mass_operation("save_batch", ctx_key)

    with detail_tab:
        detail_df = st.session_state["mass_eval_df"].copy()
        selected_detail = detail_df[detail_df["Selecionar"].fillna(False).astype(bool)].copy()
        invalid_df = build_mass_validation_df(detail_df)

        render_section_header(
            "Detalhes & KPIs",
            "Diagnóstico do lote, pendências e prévia financeira ficam aqui para não poluir a edição.",
            "Análise",
        )

        origem_counts = detail_df["Origem"].value_counts().to_dict() if "Origem" in detail_df.columns else {}
        render_status_cards([
            {
                "title": "Linhas no filtro",
                "value": len(detail_df),
                "detail": f"Banco: {origem_counts.get('Banco', 0)} | Base anterior: {origem_counts.get('Base anterior', 0)} | Novo: {origem_counts.get('Novo', 0)}",
                "tone": "info",
            },
            {
                "title": "Selecionados",
                "value": len(selected_detail),
                "detail": "Linhas que serão consideradas no próximo salvamento.",
                "tone": "success" if len(selected_detail) else "neutral",
            },
            {
                "title": "Pendências",
                "value": len(invalid_df),
                "detail": "Somente entre os selecionados.",
                "tone": "success" if invalid_df.empty else "warning",
            },
            {
                "title": "Total estimado",
                "value": brl(mass_total_preview(detail_df, competencia)),
                "detail": "Prévia semanal dos selecionados.",
                "tone": "info",
            },
        ])

        if invalid_df.empty:
            st.success("Selecionados prontos para gravação.")
        else:
            st.dataframe(invalid_df, width="stretch", hide_index=True)

        if not selected_detail.empty:
            cols = ["Nome", "Setor", "Função", "Status", "Score", "Origem", *MASS_PCT_COLS]
            st.dataframe(selected_detail[[c for c in cols if c in selected_detail.columns]], width="stretch", hide_index=True)


def render_weekly_history():
    render_section_header(
        "Histórico recente",
        "Últimas 12 avaliações salvas para conferência rápida.",
        "Auditoria",
    )

    last = list_last_weekly(12)
    if last.empty:
        st.info("Ainda não há avaliações salvas.")
        return

    show = last.copy()
    from utils import date_iso_to_br

    show["Semana"] = show["week_start"].apply(date_iso_to_br)
    show.drop(columns=["week_start"], inplace=True)
    show = show.rename(columns={
        "name": "Funcionário",
        "sector": "Setor",
        "role": "Função",
        "items_count": "Itens",
        "efficiency_pct": "Prod/Efic (%)",
        "taxa_erros_pct": "Taxa de Erros (%)",
        "assiduidade_pct": "Assiduidade (%)",
        "qualidade_pct": "Qualidade (%)",
        "produtividade_pct": "Produtividade (%)",
        "comportamento_pct": "Comportamento (%)",
        "evaluator": "Avaliador",
    })
    for col in ["Prod/Efic (%)", "Taxa de Erros (%)", "Assiduidade (%)", "Qualidade (%)", "Produtividade (%)", "Comportamento (%)"]:
        if col in show.columns:
            show[col] = show[col].map(lambda v: pct_br(v, 1))
    first_cols = ["Semana", "Funcionário", "Setor", "Função"]
    remaining_cols = [c for c in show.columns if c not in first_cols]
    show = show[first_cols + remaining_cols]
    st.dataframe(show, width="stretch", hide_index=True)


def page_weekly():
    render_page_header(
        title="Avaliação Semanal",
        subtitle="Escolha o modo de trabalho, registre exceções e salve a avaliação com prévia financeira.",
        icon="🗓️",
        kicker="Etapa 2",
    )
    render_operation_status()

    with st.spinner("Carregando funcionários ativos do banco..."):
        all_active_emp = list_active_employees()
        evaluator_options = evaluator_options_from_df(list_active_leadership_evaluators())
    emp = all_active_emp.copy()
    if "is_leadership" in emp.columns:
        emp = emp[emp["is_leadership"].fillna(0).astype(int) == 0].copy()
    if emp.empty:
        st.info("Cadastre funcionários avaliáveis primeiro.")
        return

    mode_options = ["Avaliar individual", "Avaliação em massa", "Histórico recente"]
    if hasattr(st, "segmented_control"):
        weekly_mode = st.segmented_control(
            "Modo",
            mode_options,
            default="Avaliar individual",
            selection_mode="single",
            key="weekly_mode",
        )
    else:
        weekly_mode = st.radio("Modo", mode_options, horizontal=True, key="weekly_mode")

    if weekly_mode in {"Avaliar individual", "Avaliação em massa"} and not evaluator_options:
        st.error("Cadastre ou ative pelo menos um funcionário como coordenação/supervisão para selecionar o avaliador.")
        return

    if weekly_mode == "Avaliação em massa":
        render_mass_weekly_tab(emp, evaluator_options)
        return

    if weekly_mode == "Histórico recente":
        render_weekly_history()
        return

    emp_label_to_id = {
        f'{r["name"]} • {r["sector"]} • {r["role"]}{" • MONITOR" if int(r["is_monitor"]) == 1 else ""}': int(r["id"])
        for _, r in emp.iterrows()
    }

    top1, top2 = st.columns([2, 1], gap="large")
    with top2:
        d = st.date_input("Data de referência", value=date.today(), format="DD/MM/YYYY")
        ws = monday_of(d)
        ws_iso = ws.isoformat()
        st.markdown(f"**Semana:** {week_label(ws)}")
        competencia = competencia_from_week_start(ws)
        st.caption(f"Competência: {month_label_to_br(competencia)}")

    with top1:
        selected_emp_label = st.selectbox("Funcionário", list(emp_label_to_id.keys()))

    employee_id = emp_label_to_id[selected_emp_label]
    role = emp[emp["id"] == employee_id].iloc[0]["role"]

    payload = build_default_payload(employee_id, ws_iso)

    defaults = {
        "assiduidade": payload["assiduidade"],
        "qualidade": payload["qualidade"],
        "taxa_erros": payload["taxa_erros"],
        "produtividade": payload["produtividade"],
        "comportamento": payload["comportamento"],
    }
    items_default = payload["items_count"]
    notes_default = payload["notes"]
    evaluator_default = payload["evaluator"]
    just_defaults = payload["justs"]
    
    current_eval_key = f"{employee_id}|{ws_iso}"

    if st.session_state.get("wk_eval_key") != current_eval_key:
        st.session_state["wk_eval_key"] = current_eval_key

        apply_weekly_pcts({
            "assiduidade": defaults["assiduidade"],
            "qualidade": defaults["qualidade"],
            "produtividade": defaults["produtividade"],
            "comportamento": defaults["comportamento"],
        })
        st.session_state["wk_taxa_erros_pct"] = defaults["taxa_erros"]
        st.session_state["wk_items_count"] = items_default
        st.session_state["wk_taxa_erros_pct_input"] = float(defaults["taxa_erros"])
        st.session_state["wk_items_count_input"] = int(items_default)
        apply_weekly_notes(notes_default)
        apply_weekly_justifications({
            "assiduidade": just_defaults.get("assiduidade", ""),
            "qualidade": just_defaults.get("qualidade", ""),
            "taxa_erros": just_defaults.get("taxa_erros", ""),
            "produtividade": just_defaults.get("produtividade", ""),
            "comportamento": just_defaults.get("comportamento", ""),
        })

        # limpa sugestões antigas que possam estar de outro colaborador/semana
        for k in ["wk_taxa_sug", "wk_taxa_sug_reason", "wk_auto_taxa_reason"]:
            if k in st.session_state:
                del st.session_state[k]

    existing_is_empty = payload.get("source") != "current"
    has_previous_basis = payload.get("source") == "previous"
    weekly_errors_df = list_weekly_errors(employee_id, ws_iso)
    weekly_errors_rows = weekly_errors_df.to_dict(orient="records") if not weekly_errors_df.empty else []

    with top1:
        evaluator = st.selectbox(
            "Avaliador",
            evaluator_options,
            index=selected_evaluator_index(evaluator_options, evaluator_default),
        )

    st.info("Use as abas para preencher; a prévia financeira fica sempre visível na lateral.")
    if existing_is_empty and has_previous_basis:
        st.info("Comentários e justificativas foram carregados da última avaliação deste funcionário como base.")

    render_rules_block()
    render_week_priority_ranking(emp, ws_iso)

    render_live_preview_sidebar(competencia, defaults)
    sync_weekly_entry_inputs(items_default, defaults["taxa_erros"])

    tabs = st.tabs([
        "1) Entrada",
        "2) Log de Erros",
        "3) Justificativas",
        "4) Prévia & Salvar",
    ])

    with tabs[0]:
        render_section_header(
            "Entrada",
            "Defina resultados, use sugestões e copie a base anterior quando fizer sentido.",
            "Passo 1",
        )

        act1, act2, act3 = st.columns(3, gap="medium")
        if act1.button("Copiar última avaliação", key="copy_prev_single"):
            prev = build_default_payload(employee_id, ws_iso)
            st.session_state["wk_items_count"] = prev["items_count"]
            st.session_state["wk_taxa_erros_pct"] = prev["taxa_erros"]
            request_weekly_entry_sync()
            apply_weekly_pcts({
                "assiduidade": prev["assiduidade"],
                "qualidade": prev["qualidade"],
                "produtividade": prev["produtividade"],
                "comportamento": prev["comportamento"],
            })
            apply_weekly_notes(prev["notes"])
            apply_weekly_justifications(prev["justs"])
            st.success("Última avaliação carregada como base.")
            st.rerun()

        if act2.button("Sugerir notas automaticamente", key="auto_suggest_single"):
            suggestion = suggest_full_evaluation(
                role=str(role),
                items_count=int(st.session_state.get("wk_items_count", items_default)),
                error_rows=weekly_errors_rows,
                previous_payload=payload,
            )
            st.session_state["wk_taxa_erros_pct"] = suggestion["taxa_erros"]
            request_weekly_entry_sync()
            apply_weekly_pcts({
                "assiduidade": suggestion["assiduidade"],
                "qualidade": suggestion["qualidade"],
                "produtividade": suggestion["produtividade"],
                "comportamento": suggestion["comportamento"],
            })
            st.session_state["wk_auto_taxa_reason"] = suggestion["reason_taxa"]
            st.success("Sugestão automática aplicada.")
            st.rerun()

        if act3.button("Aplicar padrão 100%", key="apply_100_single"):
            st.session_state["wk_taxa_erros_pct"] = 100.0
            request_weekly_entry_sync()
            apply_weekly_pcts({
                "assiduidade": 100.0,
                "qualidade": 100.0,
                "produtividade": 100.0,
                "comportamento": 100.0,
            })
            st.success("Padrão 100% aplicado.")
            st.rerun()

        colA, colB, colC = st.columns([1, 1, 1], gap="medium")

        with colA:
            items_count = st.number_input(
                "Itens/peças no período (opcional)",
                min_value=0,
                step=1,
                key="wk_items_count_input",
                help="Útil para produtividade e sugestão de taxa de erros."
            )

        with colB:
            taxa_erros_pct = st.number_input(
                "Taxa de Erros (%) — valor final",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                key="wk_taxa_erros_pct_input",
                help="Pode ser manual ou derivada da sugestão automática."
            )
            mult = band_multiplier(taxa_erros_pct)
            st.progress(mult)
            st.caption(f"Faixa aplicada: **{band_label(mult)}**")

        with colC:
            st.text_input("Função (snapshot)", value=str(role), disabled=True)

        if "wk_auto_taxa_reason" in st.session_state:
            st.info(f"Sugestão automática de taxa de erros: {st.session_state['wk_auto_taxa_reason']}")

        render_divider()
        st.markdown("#### Demais quesitos")
        cols = st.columns(4, gap="medium")
        pcts = dict(st.session_state.get("wk_pcts", {}))

        labels = {
            "assiduidade": "Assiduidade",
            "qualidade": "Qualidade",
            "produtividade": "Produtividade / Eficiência",
            "comportamento": "Comportamento",
        }

        for i, key in enumerate(WEEKLY_SLIDER_KEYS):
            monthly_cap = [x[3] for x in WEEKLY_CRITERIA if x[0] == key][0]
            week_value = monthly_cap_to_week_value(float(monthly_cap), competencia)

            with cols[i]:
                pcts[key] = st.slider(
                    labels[key],
                    0,
                    100,
                    step=5,
                    help=pct_help(labels[key]),
                    key=f"wk_{key}"
                )
                mult = band_multiplier(pcts[key])
                st.progress(mult)
                st.caption(f"Faixa: **{band_label(mult)}** | Valor semana: {brl(week_value)}")

        st.session_state["wk_items_count"] = int(items_count)
        st.session_state["wk_taxa_erros_pct"] = float(taxa_erros_pct)
        st.session_state["wk_pcts"] = dict(pcts)

    with tabs[1]:
        render_section_header(
            "Log de erros",
            "Registre ocorrências da semana; elas alimentam a sugestão automática.",
            "Passo 2",
        )

        with st.form("form_add_error", clear_on_submit=True):
            c1, c2, c3 = st.columns([1.4, 0.8, 0.6], gap="medium")
            with c1:
                error_type = st.selectbox("Tipo de erro", DEFAULT_ERROR_TYPES)
            with c2:
                severity = st.selectbox("Gravidade", SEVERITIES, index=1, format_func=severity_label)
            with c3:
                qty = st.number_input("Qtd", min_value=1, step=1, value=1)

            err_notes = st.text_input("Observação (opcional)", placeholder="Ex.: pedido 123 / romaneio 88 / causa raiz...")
            add = st.form_submit_button("Adicionar ao log")
            if add:
                with st.spinner("Gravando erro no banco..."):
                    add_weekly_error(
                        employee_id=employee_id,
                        week_start_iso=ws_iso,
                        role_snapshot=str(role),
                        error_type=error_type,
                        severity=severity,
                        qty=int(qty),
                        notes=err_notes,
                    )
                mark_operation_status(
                    "Erro gravado no log semanal",
                    f"{error_type} | {severity_label(severity)} | semana {week_label(ws)}.",
                    "success",
                )
                st.rerun()

        errs = list_weekly_errors(employee_id, ws_iso)
        if errs.empty:
            st.info("Sem registros no log nesta semana.")
            weekly_errors_rows = []
        else:
            errs_display = errs.rename(columns={
                "id": "ID",
                "error_type": "Tipo",
                "severity": "Gravidade",
                "qty": "Qtd",
                "notes": "Obs",
                "created_at": "Criado em",
            }).copy()
            errs_display["Gravidade"] = errs_display["Gravidade"].map(severity_label)
            errs_display["Criado em"] = errs_display["Criado em"].map(datetime_iso_to_br)
            st.dataframe(errs_display, width="stretch", hide_index=True)
            weekly_errors_rows = errs.to_dict(orient="records")

            with st.expander("Excluir um item do log"):
                del_id = st.number_input("ID do erro", min_value=0, step=1, value=0)
                if st.button("Excluir", type="secondary", key="del_weekly_error"):
                    if del_id > 0:
                        with st.spinner("Excluindo erro do banco..."):
                            delete_weekly_error(int(del_id))
                        mark_operation_status(
                            "Erro removido do log semanal",
                            f"ID {int(del_id)} excluído da semana {week_label(ws)}.",
                            "warning",
                        )
                        st.rerun()

        render_divider()
        st.markdown("#### Sugestão automática")
        cA, cB, cC = st.columns([1.2, 1.2, 1], gap="medium")
        with cA:
            strict_zero = st.checkbox("Crítico zera taxa", value=True)
        with cB:
            factor = st.slider("Fator para picking", 1.0, 30.0, 12.0, 1.0)
        with cC:
            if st.button("Calcular sugestão", type="primary", key="calc_taxa_sug"):
                sugg = suggest_taxa_erros_pct(
                    role=str(role),
                    items_count=int(st.session_state.get("wk_items_count", 0)),
                    weekly_errors_rows=[
                        {"error_type": r.get("error_type"), "severity": r.get("severity"), "qty": r.get("qty")}
                        for r in weekly_errors_rows
                    ],
                    strict_critical_zero=bool(strict_zero),
                    factor=float(factor),
                )
                st.session_state["wk_taxa_sug"] = float(sugg.suggested_pct)
                st.session_state["wk_taxa_sug_reason"] = sugg.reason

        if "wk_taxa_sug" in st.session_state:
            st.info(f"**Sugestão:** {pct_br(st.session_state['wk_taxa_sug'], 1)} — {st.session_state.get('wk_taxa_sug_reason', '')}")
            if st.button("Aplicar sugestão na taxa", key="apply_taxa_sug"):
                st.session_state["wk_taxa_erros_pct"] = float(st.session_state["wk_taxa_sug"])
                request_weekly_entry_sync()
                st.success("Sugestão aplicada.")
                st.rerun()

    with tabs[2]:
        render_section_header(
            "Justificativas",
            "Use modelos por critério, copie a última avaliação ou gere justificativas automaticamente.",
            "Passo 3",
        )

        current_pcts = {
            "assiduidade": st.session_state.get("wk_pcts", {}).get("assiduidade", defaults["assiduidade"]),
            "qualidade": st.session_state.get("wk_pcts", {}).get("qualidade", defaults["qualidade"]),
            "taxa_erros": st.session_state.get("wk_taxa_erros_pct", defaults["taxa_erros"]),
            "produtividade": st.session_state.get("wk_pcts", {}).get("produtividade", defaults["produtividade"]),
            "comportamento": st.session_state.get("wk_pcts", {}).get("comportamento", defaults["comportamento"]),
        }

        t0, t1, t2, t3 = st.columns([1.3, 1, 1, 1], gap="medium")
        with t0:
            template_model = st.selectbox(
                "Modelo padrão",
                ["Resultado atual", "Padrão 100%", "Revisão pontual", "Acompanhamento", "Crítico"],
                key="wk_template_model",
            )
        if t1.button("Aplicar templates rápidos", key="apply_templates"):
            apply_weekly_justifications(build_criterion_template_justifications(current_pcts, template_model))
            st.success("Templates aplicados.")
            st.rerun()

        if t2.button("Copiar última justificativa", key="copy_last_justs"):
            apply_weekly_justifications(just_defaults)
            st.success("Últimas justificativas carregadas.")
            st.rerun()

        if t3.button("Sugerir justificativas", key="suggest_justs"):
            auto_justs = build_auto_justifications(
                employee_name=str(selected_emp_label),
                pcts=current_pcts,
                items_count=int(st.session_state.get("wk_items_count", 0)),
                error_rows=weekly_errors_rows,
                previous_payload=payload,
            )
            apply_weekly_justifications(auto_justs)
            st.success("Justificativas sugeridas automaticamente.")
            st.rerun()

        if "wk_notes_area" not in st.session_state:
            st.session_state["wk_notes_area"] = st.session_state.get("wk_notes", notes_default)
        notes = st.text_area(
            "Notas gerais",
            height=90,
            placeholder="Ex.: contexto da semana, mudança de processo, pico de volume...",
            key="wk_notes_area"
        )
        st.session_state["wk_notes"] = str(notes or "")

        render_divider()
        j_ass = just_area(
            "Assiduidade",
            st.session_state.get("wk_justs", {}).get("assiduidade", ""),
            "Faltas/atrasos/saídas antecipadas + compensações.",
            key="wk_assid_just_area"
        )
        j_qual = just_area(
            "Qualidade",
            st.session_state.get("wk_justs", {}).get("qualidade", ""),
            "Retrabalho, divergências, auditorias.",
            key="wk_qual_just_area"
        )
        j_err = just_area(
            "Taxa de Erros",
            st.session_state.get("wk_justs", {}).get("taxa_erros", ""),
            "Cite erros do log, causa raiz e ação corretiva/preventiva.",
            key="wk_err_just_area"
        )
        j_prod = just_area(
            "Produtividade / Eficiência",
            st.session_state.get("wk_justs", {}).get("produtividade", ""),
            "Volume, aderência à meta, apoio em picos, gargalos.",
            key="wk_prod_just_area"
        )
        j_comp = just_area(
            "Comportamento",
            st.session_state.get("wk_justs", {}).get("comportamento", ""),
            "Disciplina operacional, colaboração, comunicação, POP.",
            key="wk_comp_just_area"
        )

        st.session_state["wk_justs"] = {
            "assiduidade": j_ass,
            "qualidade": j_qual,
            "taxa_erros": j_err,
            "produtividade": j_prod,
            "comportamento": j_comp,
        }

        filled = sum(1 for v in st.session_state["wk_justs"].values() if str(v).strip())
        st.info(f"Justificativas preenchidas: **{filled}/5**")

    with tabs[3]:
        render_section_header(
            "Prévia & Salvar",
            "Confira o pagamento estimado, pendências de justificativa e confirme o registro.",
            "Passo 4",
        )

        pcts = st.session_state.get("wk_pcts", {})
        taxa_final = float(st.session_state.get("wk_taxa_erros_pct", defaults["taxa_erros"]))
        items_count = int(st.session_state.get("wk_items_count", items_default))
        notes = st.session_state.get("wk_notes", notes_default)
        justs = st.session_state.get("wk_justs", {})

        preview_lines = []
        total = 0.0

        for key, label, _weekly_value, monthly_cap in WEEKLY_CRITERIA:
            if key == "taxa_erros":
                pct = taxa_final
            elif key == "produtividade":
                pct = float(pcts.get("produtividade", defaults["produtividade"]))
                label = "Produtividade / Eficiência"
            else:
                pct = float(pcts.get(key, defaults[key]))

            mult = band_multiplier(pct)
            week_value = monthly_cap_to_week_value(float(monthly_cap), competencia)
            pay = float(week_value) * mult
            total += pay

            preview_lines.append({
                "Critério": label,
                "Resultado (%)": pct_br(pct, 1),
                "Faixa paga": band_label(mult),
                "Valor semana": brl(float(week_value)),
                "Pagamento": brl(pay),
            })

        st.dataframe(pd.DataFrame(preview_lines), width="stretch", hide_index=True)

        score = score_from_pcts({
            "assiduidade": pcts.get("assiduidade", defaults["assiduidade"]),
            "qualidade": pcts.get("qualidade", defaults["qualidade"]),
            "taxa_erros": taxa_final,
            "produtividade": pcts.get("produtividade", defaults["produtividade"]),
            "comportamento": pcts.get("comportamento", defaults["comportamento"]),
        })
        status, _ = exception_status(score, taxa_final, 0)

        c1, c2 = st.columns(2)
        c1.metric("Total estimado (semana)", brl(total))
        c2.metric("Classificação", status)

        missing = []
        required_keys = ["assiduidade", "qualidade", "taxa_erros", "produtividade", "comportamento"]
        for k in required_keys:
            if not str(justs.get(k, "")).strip():
                missing.append(k)

        if missing:
            st.warning("⚠️ Para salvar, preencha todas as justificativas na aba **Justificativas**.")

        with st.form("form_save_weekly"):
            confirm = st.checkbox("Confirmo que revisei os resultados e justificativas.")
            save = st.form_submit_button("Salvar avaliação semanal")

            if save:
                if not confirm:
                    st.error("Marque a confirmação para salvar.")
                    st.stop()

                if missing:
                    st.error("Faltam justificativas. Preencha na aba **Justificativas**.")
                    st.stop()

                just_block = (
                    "JUSTIFICATIVAS (SEMANA)\n"
                    f"- Assiduidade: {justs['assiduidade'].strip()}\n"
                    f"- Qualidade: {justs['qualidade'].strip()}\n"
                    f"- Taxa de Erros: {justs['taxa_erros'].strip()}\n"
                    f"- Produtividade/Eficiência: {justs['produtividade'].strip()}\n"
                    f"- Comportamento: {justs['comportamento'].strip()}\n"
                )
                notes_clean = strip_embedded_justification_block(
                    str(notes).strip(),
                    "JUSTIFICATIVAS (SEMANA)",
                )
                notes_final = (notes_clean + "\n\n" + just_block).strip()

                with st.spinner("Gravando avaliação semanal no banco..."):
                    upsert_weekly_eval(
                        employee_id=employee_id,
                        week_start_iso=ws_iso,
                        evaluator=str(evaluator).strip(),
                        notes=notes_final,
                        assiduidade_pct=float(pcts.get("assiduidade", defaults["assiduidade"])),
                        qualidade_pct=float(pcts.get("qualidade", defaults["qualidade"])),
                        taxa_erros_pct=float(taxa_final),
                        produtividade_pct=float(pcts.get("produtividade", defaults["produtividade"])),
                        comportamento_pct=float(pcts.get("comportamento", defaults["comportamento"])),
                        efficiency_pct=float(pcts.get("produtividade", defaults["produtividade"])),
                        items_count=int(items_count),
                        assiduidade_just=str(justs["assiduidade"]).strip(),
                        qualidade_just=str(justs["qualidade"]).strip(),
                        taxa_erros_just=str(justs["taxa_erros"]).strip(),
                        produtividade_just=str(justs["produtividade"]).strip(),
                        comportamento_just=str(justs["comportamento"]).strip(),
                    )

                mark_operation_status(
                    "Avaliação semanal gravada no banco",
                    f"{selected_emp_label} | semana {week_label(ws)} | total estimado {brl(total)}.",
                    "success",
                )
                st.rerun()
