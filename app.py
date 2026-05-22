import streamlit as st

from db import DATABASE_CONFIG_ERROR, fetch_df, init_db, normalize_month_label
from theme import apply_kaisan_admin_theme, render_sidebar_process
from ui_auth import current_user, is_admin_user, render_user_sidebar, require_login
from ui_employees import page_employees
from ui_weekly import page_weekly
from ui_monitor import render_monitor_page
from ui_report import build_closing_check_tables, render_report_page
from utils import current_month_br, month_label_to_br, weeks_for_competencia


def _sidebar_snapshot(active_menu: str, menu_options: list[str]) -> tuple[list[dict], list[dict], str]:
    month = normalize_month_label(current_month_br())
    month_br = month_label_to_br(month)

    active_count = 0
    monitor_count = 0
    leadership_count = 0
    expected = 0
    done = 0
    issues = 0
    missing_monitoria = 0

    try:
        people = fetch_df(
            """
            SELECT
                SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) AS active_count,
                SUM(CASE WHEN active = 1 AND is_monitor = 1 AND COALESCE(is_leadership, 0) = 0 THEN 1 ELSE 0 END) AS monitor_count,
                SUM(CASE WHEN active = 1 AND COALESCE(is_leadership, 0) = 1 THEN 1 ELSE 0 END) AS leadership_count
            FROM employees
            """
        )
        if not people.empty:
            row = people.iloc[0]
            active_count = int(row.get("active_count", 0) or 0)
            monitor_count = int(row.get("monitor_count", 0) or 0)
            leadership_count = int(row.get("leadership_count", 0) or 0)

        year, month_num = map(int, month.split("-"))
        weeks_iso = [w.isoformat() for w in weeks_for_competencia(year, month_num)]
        checks = build_closing_check_tables(month, weeks_iso)
        summary = checks.get("summary", {})
        expected = int(summary.get("expected", 0) or 0)
        done = int(summary.get("done", 0) or 0)
        issues = int(summary.get("issues", 0) or 0)
        missing_monitoria = int(len(checks.get("missing_monitoria", [])) + len(checks.get("missing_monitoria_justs", [])))
    except Exception:
        pass

    coverage = round((done / expected) * 100) if expected else 0
    employees_tone = "success" if active_count else "warning"
    weekly_tone = "success" if expected and done >= expected else ("warning" if done else "danger")
    monitor_tone = "success" if monitor_count == 0 or missing_monitoria == 0 else "warning"
    report_tone = "success" if expected and issues == 0 else ("danger" if issues else "warning")

    step_defs = {
        "1. Funcionários": {
            "title": "Funcionários",
            "detail": f"{active_count} ativos",
            "tone": employees_tone,
        },
        "2. Avaliação Semanal": {
            "title": "Avaliações",
            "detail": f"{coverage}% cobertura",
            "tone": weekly_tone,
        },
        "3. Monitoria Mensal": {
            "title": "Monitoria",
            "detail": f"{monitor_count} monitores",
            "tone": monitor_tone,
        },
        "4. Relatório Mensal": {
            "title": "Relatório",
            "detail": f"{issues} pendências",
            "tone": report_tone,
        },
    }

    steps = []
    for option in menu_options:
        step = dict(step_defs.get(option, {"title": option, "detail": "", "tone": "neutral"}))
        step["active"] = option == active_menu
        steps.append(step)

    stats = [
        {"label": "Cobertura semanal", "value": f"{coverage}%"},
        {"label": "Pendências críticas", "value": str(issues)},
        {"label": "Coord./Sup.", "value": str(leadership_count)},
    ]
    return steps, stats, month_br


st.set_page_config(
    page_title="Avaliação & Bonificação • Estoque e Expedição",
    layout="wide",
    initial_sidebar_state="auto",
)

try:
    init_db()
except RuntimeError as exc:
    st.error(str(exc) or DATABASE_CONFIG_ERROR)
    st.stop()

apply_kaisan_admin_theme()
require_login()

menu_options = []
if is_admin_user(current_user()):
    menu_options.append("1. Funcionários")
menu_options.extend([
    "2. Avaliação Semanal",
    "3. Monitoria Mensal",
    "4. Relatório Mensal",
])

current_menu = st.session_state.get("main_menu", menu_options[0])
if current_menu not in menu_options:
    current_menu = menu_options[0]

sidebar_steps, sidebar_stats, sidebar_month = _sidebar_snapshot(current_menu, menu_options)
render_sidebar_process(sidebar_month, sidebar_steps, sidebar_stats)
render_user_sidebar()

menu = st.sidebar.radio("Navegação", menu_options, key="main_menu")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Use a ordem do processo: base de pessoas, avaliação semanal, monitoria e fechamento."
)

if menu == "1. Funcionários":
    page_employees()

elif menu == "2. Avaliação Semanal":
    page_weekly()

elif menu == "3. Monitoria Mensal":
    render_monitor_page()

elif menu == "4. Relatório Mensal":
    render_report_page()
