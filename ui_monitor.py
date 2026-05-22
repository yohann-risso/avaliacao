# ui_monitor.py

import streamlit as st
import pandas as pd
from datetime import date

from db import fetch_df, list_active_leadership_evaluators, normalize_month_label, upsert_monitor_monthly_eval
from constants import MONITOR_MONTHLY_CRITERIA, MONITOR_MONTHLY_TOTAL
from theme import (
    mark_operation_status,
    render_operation_status,
    render_page_header,
    render_progress_panel,
    render_section_header,
    render_stage_grid,
    render_status_cards,
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
    brl,
    current_month_br,
    date_iso_to_br,
    has_eligible_week_after_start_date,
    month_label_to_br,
    pay_band_multiplier,
    pct_br,
    strip_embedded_justification_block,
    weeks_for_competencia,
)
from ui_auth import current_evaluator_name, evaluator_options_for_current_user


def band_multiplier(pct: float) -> float:
    return pay_band_multiplier(pct, PAY_BANDS)


def band_label(mult: float) -> str:
    return pct_br(mult * 100, 0)


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
    cleaned = str(default or "").strip()
    return options.index(cleaned) if cleaned in options else 0


MONITOR_JUSTIFICATION_MODELS = {
    "acomp_metas": {
        "excelente": "Acompanhou as metas do mês de forma consistente, mantendo visão clara dos resultados e apoiando a equipe nos ajustes necessários.",
        "adequado": "Realizou acompanhamento adequado das metas, com pontos pontuais de melhoria na frequência ou profundidade das análises.",
        "atencao": "O acompanhamento das metas ocorreu de forma irregular, exigindo maior rotina de verificação, cobrança e registro dos desvios.",
        "critico": "Houve falha relevante no acompanhamento das metas, com impacto na previsibilidade e necessidade de alinhamento imediato.",
    },
    "org_fluxo": {
        "excelente": "Manteve boa organização do fluxo operacional, priorizando demandas e reduzindo gargalos durante o mês.",
        "adequado": "Organizou o fluxo de forma satisfatória, com ajustes pontuais necessários em priorização, distribuição ou acompanhamento das tarefas.",
        "atencao": "A organização do fluxo apresentou instabilidade, exigindo reforço na distribuição de prioridades e no acompanhamento da rotina.",
        "critico": "A organização do fluxo ficou abaixo do esperado, gerando impacto operacional e necessidade de correção estruturada.",
    },
    "suporte_equipe": {
        "excelente": "Prestou suporte efetivo à equipe, orientando dúvidas, apoiando a execução e contribuindo para a estabilidade da operação.",
        "adequado": "Prestou suporte adequado à equipe, com oportunidades pontuais de maior presença, orientação ou acompanhamento.",
        "atencao": "O suporte à equipe foi irregular, exigindo maior disponibilidade, comunicação e apoio na execução diária.",
        "critico": "Houve deficiência relevante no suporte à equipe, impactando a rotina e exigindo acompanhamento próximo.",
    },
    "disciplina_oper": {
        "excelente": "Manteve disciplina operacional consistente, reforçando procedimentos, organização e aderência aos padrões definidos.",
        "adequado": "Manteve disciplina operacional adequada, com pequenos ajustes necessários em constância, registro ou cobrança dos padrões.",
        "atencao": "A disciplina operacional apresentou falhas pontuais, exigindo reforço de padrões, rotina e acompanhamento.",
        "critico": "A disciplina operacional ficou abaixo do esperado, com necessidade de intervenção e plano de correção.",
    },
}


def monitor_template_tier_from_pct(pct: float) -> str:
    p = max(0.0, min(100.0, float(pct or 0)))
    if p >= 91:
        return "excelente"
    if p >= 81:
        return "adequado"
    if p >= 71:
        return "atencao"
    return "critico"


def build_monitor_template_justifications(pcts: dict | None = None, model: str = "Resultado atual") -> dict:
    tier_by_model = {
        "Padrão 100%": "excelente",
        "Revisão pontual": "adequado",
        "Acompanhamento": "atencao",
        "Crítico": "critico",
    }

    pcts = pcts or {}
    out = {}
    for key, templates in MONITOR_JUSTIFICATION_MODELS.items():
        tier = tier_by_model.get(model)
        if tier is None:
            tier = monitor_template_tier_from_pct(pcts.get(key, 100))
        out[key] = templates[tier]
    return out


MONITOR_JUST_AREA_KEYS = {
    key: f"mon_{key}_just_area"
    for key, _label, _value, _obs in MONITOR_MONTHLY_CRITERIA
}


def apply_monitor_justifications(justs: dict):
    clean = {
        key: str((justs or {}).get(key, "") or "")
        for key in MONITOR_JUST_AREA_KEYS
    }
    st.session_state["mon_justs"] = clean
    for key, area_key in MONITOR_JUST_AREA_KEYS.items():
        st.session_state[area_key] = clean[key]


def apply_monitor_notes(notes: str):
    clean = str(notes or "")
    st.session_state["mon_notes"] = clean
    st.session_state["mon_notes_area"] = clean


def apply_monitor_pcts(pcts: dict):
    clean = {}
    for (key, _label, _value, _obs) in MONITOR_MONTHLY_CRITERIA:
        clean[key] = int(round(float((pcts or {}).get(key, 100) or 100)))
        st.session_state[f"mon_{key}"] = clean[key]
    st.session_state["mon_pcts"] = clean


def render_monitor_page():
    render_page_header(
        title="Monitoria Mensal",
        subtitle="Avaliação exclusiva para monitores, com critérios mensais, faixas e justificativas obrigatórias.",
        icon="🧭",
        kicker="Etapa 4",
    )
    render_operation_status()

    evaluator_options = evaluator_options_for_current_user(
        evaluator_options_from_df(list_active_leadership_evaluators())
    )
    if not evaluator_options:
        st.error("Cadastre ou ative pelo menos um funcionário como coordenação/supervisão para selecionar o avaliador.")
        return

    month_input = st.text_input("Mês (MM/AAAA)", value=current_month_br())
    try:
        month = normalize_month_label(month_input)
    except Exception:
        st.error("Mês inválido. Use MM/AAAA (ex.: 05/2026).")
        return
    month_br = month_label_to_br(month)
    year, month_num = map(int, month.split("-"))
    weeks_iso = [w.isoformat() for w in weeks_for_competencia(year, month_num)]

    monitors_all = fetch_df("""
        SELECT id, name, sector, role, monitor_start_date
        FROM employees
        WHERE active = 1 AND is_monitor = 1 AND COALESCE(is_leadership, 0) = 0
        ORDER BY sector, role, name
    """)

    if monitors_all.empty:
        st.info("Nenhum funcionário marcado como MONITOR.")
        return

    missing_monitor_start = monitors_all[
        monitors_all["monitor_start_date"].fillna("").astype(str).str.strip() == ""
    ]
    if not missing_monitor_start.empty:
        st.warning(
            "Há monitor(es) sem **Monitor desde** no cadastro. "
            "Preencha a data para liberar a avaliação de monitoria pela regra de tempo."
        )

    monitors = monitors_all[
        monitors_all["monitor_start_date"].apply(
            lambda value: has_eligible_week_after_start_date(
                str(value or ""),
                weeks_iso,
                missing_is_eligible=False,
            )
        )
    ].copy()

    if monitors.empty:
        st.info("Nenhum monitor elegível para a competência selecionada pela data **Monitor desde**.")
        return

    label_map = {
        f'{r["name"]} • {r["sector"]} • {r["role"]} • desde {date_iso_to_br(r["monitor_start_date"])}': int(r["id"])
        for _, r in monitors.iterrows()
    }

    top1, top2 = st.columns([2, 1], gap="large")
    with top1:
        selected = st.selectbox("Monitor", list(label_map.keys()))
        evaluator = st.selectbox(
            "Avaliador",
            evaluator_options,
            index=selected_evaluator_index(evaluator_options, current_evaluator_name()),
        )
    with top2:
        st.caption("Competência")
        st.write(month_br)
        st.caption("Regra: primeira semana como monitor não entra.")

    employee_id = label_map[selected]
    existing = fetch_df(
        """
        SELECT *
        FROM monitor_monthly_evaluations
        WHERE employee_id = ? AND month = ?
        """,
        (employee_id, month)
    )

    defaults = {k: 100 for (k, _label, _value, _obs) in MONITOR_MONTHLY_CRITERIA}
    just_defaults = {k: "" for (k, _label, _value, _obs) in MONITOR_MONTHLY_CRITERIA}
    notes_default = ""

    if not existing.empty:
        row = existing.iloc[0]
        notes_default = strip_embedded_justification_block(
            str(row.get("notes", "") or ""),
            "JUSTIFICATIVAS (MONITORIA)",
        )
        for (k, _label, _value, _obs) in MONITOR_MONTHLY_CRITERIA:
            defaults[k] = int(round(float(row.get(f"{k}_pct", 100) or 100)))
            colj = f"{k}_just"
            if colj in row.index:
                just_defaults[k] = str(row.get(colj) or "")

    mon_eval_key = f"{employee_id}|{month}"
    if st.session_state.get("mon_eval_key") != mon_eval_key:
        st.session_state["mon_eval_key"] = mon_eval_key
        apply_monitor_pcts(defaults)
        apply_monitor_notes(notes_default)
        apply_monitor_justifications(just_defaults)

    origem = "Registro existente no banco" if not existing.empty else "Novo registro para o mês"
    render_status_cards([
        {
            "title": "Mês",
            "value": month_br,
            "detail": "Competência no padrão brasileiro MM/AAAA.",
            "tone": "info",
        },
        {
            "title": "Origem",
            "value": origem,
            "detail": "A tela carrega valores salvos quando já existe avaliação.",
            "tone": "success" if not existing.empty else "neutral",
        },
        {
            "title": "Fluxo",
            "value": "3 etapas",
            "detail": "Critérios, justificativas e confirmação final.",
            "tone": "info",
        },
    ])

    current_monitor_justs = st.session_state.get("mon_justs", {})
    filled_monitor_justs = sum(1 for v in current_monitor_justs.values() if str(v).strip())
    monitor_progress = round((filled_monitor_justs / len(MONITOR_MONTHLY_CRITERIA)) * 100, 1)
    render_progress_panel(
        "Progresso da monitoria",
        f"{filled_monitor_justs}/{len(MONITOR_MONTHLY_CRITERIA)} justificativas preenchidas",
        "Critérios, evidências e confirmação precisam estar completos antes de salvar.",
        progress=monitor_progress,
        tone="success" if filled_monitor_justs == len(MONITOR_MONTHLY_CRITERIA) else "warning",
        meta=f"{monitor_progress:.1f}% pronto",
    )
    render_stage_grid([
        {
            "status": "Atual",
            "title": "Competência",
            "detail": month_br,
            "tone": "info",
        },
        {
            "status": "Carregado" if not existing.empty else "Novo",
            "title": "Origem",
            "detail": origem,
            "tone": "success" if not existing.empty else "neutral",
        },
        {
            "status": "Pendente" if filled_monitor_justs < len(MONITOR_MONTHLY_CRITERIA) else "Pronto",
            "title": "Evidências",
            "detail": f"{filled_monitor_justs} de {len(MONITOR_MONTHLY_CRITERIA)} justificativas.",
            "tone": "success" if filled_monitor_justs == len(MONITOR_MONTHLY_CRITERIA) else "warning",
        },
        {
            "status": "Revisar",
            "title": "Salvar",
            "detail": "Confirmação final grava a monitoria do mês.",
            "tone": "info",
        },
    ])

    tabs = st.tabs(["Critérios", "Justificativas", "Prévia & Salvar", "Detalhes & KPIs"])

    with tabs[0]:
        render_section_header(
            "Critérios",
            "Defina o resultado de cada critério e confira a faixa aplicada.",
            "Passo 1",
        )
        pcts = {}
        cols = st.columns(len(MONITOR_MONTHLY_CRITERIA), gap="medium")

        for i, (key, label, value, obs) in enumerate(MONITOR_MONTHLY_CRITERIA):
            with cols[i]:
                pcts[key] = st.slider(
                    label,
                    0,
                    100,
                    step=5,
                    key=f"mon_{key}",
                )
                mult = band_multiplier(pcts[key])
                st.progress(mult)
                st.caption(f"Faixa: **{band_label(mult)}** | {brl(float(value))} • {obs}")

        st.session_state["mon_pcts"] = dict(pcts)

    with tabs[1]:
        render_section_header(
            "Justificativas",
            "Use modelos rápidos e registre evidências observáveis para cada critério.",
            "Passo 2",
        )

        current_mon_pcts = st.session_state.get(
            "mon_pcts",
            {k: defaults[k] for k, _label, _value, _obs in MONITOR_MONTHLY_CRITERIA},
        )

        c1, c2 = st.columns([1.3, 1], gap="medium")
        with c1:
            monitor_template_model = st.selectbox(
                "Modelo padrão",
                ["Resultado atual", "Padrão 100%", "Revisão pontual", "Acompanhamento", "Crítico"],
                key="mon_template_model",
            )
        with c2:
            st.write("")
            if st.button("Aplicar modelos padrões", key="mon_apply_templates"):
                apply_monitor_justifications(
                    build_monitor_template_justifications(current_mon_pcts, monitor_template_model)
                )
                st.success("Modelos aplicados.")
                st.rerun()

        if "mon_notes_area" not in st.session_state:
            st.session_state["mon_notes_area"] = st.session_state.get("mon_notes", notes_default)
        notes = st.text_area(
            "Notas gerais (opcional)",
            height=90,
            placeholder="Ex.: contexto do mês, mudanças, pico, feedback...",
            key="mon_notes_area",
        )

        justs = {}
        for (key, label, _value, _obs) in MONITOR_MONTHLY_CRITERIA:
            area_key = MONITOR_JUST_AREA_KEYS[key]
            if area_key not in st.session_state:
                st.session_state[area_key] = st.session_state.get("mon_justs", just_defaults).get(key, "")
            justs[key] = st.text_area(
                f"Justificativa — {label}*",
                height=95,
                placeholder="Relate fatos observáveis: entregas, evidências, comportamento, impacto na operação.",
                key=area_key,
            )
            st.caption(f"Caracteres: {len(justs[key].strip())} (recomendado ≥ 25)")

        st.session_state["mon_notes"] = str(notes or "")
        st.session_state["mon_justs"] = dict(justs)

        filled = sum(1 for v in justs.values() if str(v).strip())
        st.info(f"Justificativas preenchidas: **{filled}/{len(MONITOR_MONTHLY_CRITERIA)}**")

    with tabs[2]:
        render_section_header(
            "Prévia & Salvar",
            "Confira o cálculo da monitoria e confirme que as justificativas foram revisadas.",
            "Passo 3",
        )
        pcts = st.session_state.get("mon_pcts", {k: defaults[k] for k,_,_,_ in MONITOR_MONTHLY_CRITERIA})
        justs = st.session_state.get("mon_justs", {})
        notes = st.session_state.get("mon_notes", notes_default)

        preview = []
        total = 0.0
        for (key, label, value, obs) in MONITOR_MONTHLY_CRITERIA:
            pct = float(pcts.get(key, 0))
            mult = band_multiplier(pct)
            paid = float(value) * mult
            total += paid
            preview.append({
                "Critério": label,
                "Resultado (%)": pct_br(pct, 1),
                "Faixa paga": band_label(mult),
                "Valor mês": brl(float(value)),
                "Pagamento": brl(paid),
                "Obs": obs,
            })

        st.dataframe(pd.DataFrame(preview), width="stretch", hide_index=True)
        st.metric("Total Monitoria (mês)", brl(total), f"Teto {brl(float(MONITOR_MONTHLY_TOTAL))}")

        missing = []
        for (key, label, _value, _obs) in MONITOR_MONTHLY_CRITERIA:
            if not str(justs.get(key, "")).strip():
                missing.append(label)

        if missing:
            st.warning("⚠️ Para salvar, preencha todas as justificativas na aba **Justificativas**.")

        with st.form("form_save_monitor"):
            confirm = st.checkbox("Confirmo que revisei os resultados e justificativas.")
            save = st.form_submit_button("Salvar avaliação mensal")

            if save:
                if not confirm:
                    st.error("Marque a confirmação para salvar.")
                    st.stop()
                if missing:
                    st.error("Faltam justificativas. Preencha na aba **Justificativas**.")
                    st.stop()

                just_block = "JUSTIFICATIVAS (MONITORIA)\n"
                for (key, label, _value, _obs) in MONITOR_MONTHLY_CRITERIA:
                    just_block += f"- {label}: {justs[key].strip()}\n"
                notes_clean = strip_embedded_justification_block(
                    str(notes).strip(),
                    "JUSTIFICATIVAS (MONITORIA)",
                )
                notes_final = (notes_clean + "\n\n" + just_block).strip()

                with st.spinner("Gravando monitoria mensal no banco..."):
                    upsert_monitor_monthly_eval(
                        employee_id=employee_id,
                        month=month,
                        evaluator=str(evaluator).strip(),
                        notes=notes_final,
                        pcts=pcts,
                        justs=justs,
                    )
                mark_operation_status(
                    "Monitoria mensal gravada no banco",
                    f"{selected} | competência {month_br} | total {brl(total)}.",
                    "success",
                )
                st.rerun()

    with tabs[3]:
        render_section_header(
            "Detalhes & KPIs",
            "Conferência do mês, faixas aplicadas e pendências ficam nesta aba.",
            "Análise",
        )
        pcts = st.session_state.get("mon_pcts", {k: defaults[k] for k,_,_,_ in MONITOR_MONTHLY_CRITERIA})
        justs = st.session_state.get("mon_justs", {})
        filled = sum(1 for v in justs.values() if str(v).strip())
        score = sum(float(pcts.get(k, 0) or 0) for k,_,_,_ in MONITOR_MONTHLY_CRITERIA) / len(MONITOR_MONTHLY_CRITERIA)
        total = sum(
            float(value) * band_multiplier(float(pcts.get(key, 0) or 0))
            for key, _label, value, _obs in MONITOR_MONTHLY_CRITERIA
        )
        render_status_cards([
            {
                "title": "Score médio",
                "value": pct_br(score, 1),
                "detail": "Média dos critérios de monitoria.",
                "tone": "info",
            },
            {
                "title": "Justificativas",
                "value": f"{filled}/{len(MONITOR_MONTHLY_CRITERIA)}",
                "detail": "Todas são obrigatórias para salvar.",
                "tone": "success" if filled == len(MONITOR_MONTHLY_CRITERIA) else "warning",
            },
            {
                "title": "Total estimado",
                "value": brl(total),
                "detail": f"Teto mensal: {brl(float(MONITOR_MONTHLY_TOTAL))}.",
                "tone": "success",
            },
        ])
