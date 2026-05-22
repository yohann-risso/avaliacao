import streamlit as st

from db import (
    DATABASE_CONFIG_ERROR,
    fetch_df,
    init_db,
    normalize_month_label,
    refresh_employee_active_statuses,
)
from security import log_sanitized_exception, redact_sensitive
from navigation import menu_options_for_user
from theme import apply_kaisan_admin_theme, render_sidebar_navigation
from ui_auth import current_user, render_user_sidebar, require_login
from utils import current_month_br, month_label_to_br, weeks_for_competencia


st.set_page_config(
    page_title="Avaliação & Bonificação • Estoque e Expedição",
    layout="wide",
    initial_sidebar_state="auto",
)

NAV_QUERY_KEY = "tela"
NAV_WIDGET_KEY = "main_menu_nav"


@st.cache_data(ttl=45, show_spinner=False)
def _sidebar_snapshot(
    menu_options_key: tuple[str, ...],
    data_marker: str = "",
) -> tuple[list[dict], list[dict], str]:
    menu_options = list(menu_options_key)
    month = normalize_month_label(current_month_br())
    month_br = month_label_to_br(month)

    active_count = 0
    monitor_count = 0
    leadership_count = 0
    user_count = 0
    linked_user_count = 0
    expected = 0
    done = 0
    issues = 0
    missing_monitoria = 0

    try:
        year, month_num = map(int, month.split("-"))
        weeks_iso = [w.isoformat() for w in weeks_for_competencia(year, month_num)]
        week_placeholders = ",".join(["?"] * len(weeks_iso))

        people = fetch_df(
            """
            SELECT
                SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) AS active_count,
                SUM(CASE WHEN active = 1 AND COALESCE(is_leadership, 0) = 0 THEN 1 ELSE 0 END) AS evaluable_count,
                SUM(CASE WHEN active = 1 AND is_monitor = 1 AND COALESCE(is_leadership, 0) = 0 THEN 1 ELSE 0 END) AS monitor_count,
                SUM(CASE WHEN active = 1 AND COALESCE(is_leadership, 0) = 1 THEN 1 ELSE 0 END) AS leadership_count
            FROM employees
            """
        )
        evaluable_count = 0
        if not people.empty:
            row = people.iloc[0]
            active_count = int(row.get("active_count", 0) or 0)
            evaluable_count = int(row.get("evaluable_count", 0) or 0)
            monitor_count = int(row.get("monitor_count", 0) or 0)
            leadership_count = int(row.get("leadership_count", 0) or 0)

        users = fetch_df(
            """
            SELECT
                COUNT(*) AS user_count,
                SUM(CASE WHEN evaluator_employee_id IS NOT NULL THEN 1 ELSE 0 END) AS linked_user_count
            FROM login_users
            """
        )
        if not users.empty:
            row = users.iloc[0]
            user_count = int(row.get("user_count", 0) or 0)
            linked_user_count = int(row.get("linked_user_count", 0) or 0)

        expected = int(evaluable_count * len(weeks_iso))
        if weeks_iso:
            weekly = fetch_df(
                f"""
                SELECT COUNT(*) AS done
                FROM (
                    SELECT
                        w.employee_id,
                        TRIM(CAST(w.week_start AS TEXT)) AS week_start
                    FROM weekly_evaluations w
                    JOIN employees e ON e.id = w.employee_id
                    WHERE COALESCE(e.active, 1) = 1
                      AND COALESCE(e.is_leadership, 0) = 0
                      AND TRIM(CAST(w.week_start AS TEXT)) IN ({week_placeholders})
                    GROUP BY w.employee_id, TRIM(CAST(w.week_start AS TEXT))
                ) coverage
                """,
                tuple(weeks_iso),
            )
            if not weekly.empty:
                done = int(weekly.iloc[0].get("done", 0) or 0)

        monitor_done = 0
        monitoria = fetch_df(
            """
            SELECT COUNT(DISTINCT m.employee_id) AS done
            FROM monitor_monthly_evaluations m
            JOIN employees e ON e.id = m.employee_id
            WHERE TRIM(CAST(m.month AS TEXT)) = ?
              AND COALESCE(e.active, 1) = 1
              AND COALESCE(e.is_monitor, 0) = 1
              AND COALESCE(e.is_leadership, 0) = 0
            """,
            (month,),
        )
        if not monitoria.empty:
            monitor_done = int(monitoria.iloc[0].get("done", 0) or 0)
        missing_monitoria = max(0, int(monitor_count) - monitor_done)
        issues = max(0, expected - done) + missing_monitoria
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
        "2. Usuários": {
            "title": "Usuários",
            "detail": f"{linked_user_count}/{user_count} vinculados",
            "tone": "success" if user_count and linked_user_count == user_count else ("warning" if user_count else "neutral"),
        },
        "3. Avaliação Semanal": {
            "title": "Avaliações",
            "detail": f"{coverage}% cobertura",
            "tone": weekly_tone,
        },
        "4. Monitoria Mensal": {
            "title": "Monitoria",
            "detail": f"{monitor_count} monitores",
            "tone": monitor_tone,
        },
        "5. Relatório Mensal": {
            "title": "Relatório",
            "detail": f"{issues} pendências",
            "tone": report_tone,
        },
    }

    steps = []
    for option in menu_options:
        step = dict(step_defs.get(option, {"title": option, "detail": "", "tone": "neutral"}))
        step["option"] = option
        steps.append(step)

    stats = [
        {"label": "Cobertura semanal", "value": f"{coverage}%"},
        {"label": "Pendências críticas", "value": str(issues)},
        {"label": "Coord./Sup.", "value": str(leadership_count)},
    ]
    return steps, stats, month_br


@st.cache_resource(show_spinner=False)
def _ensure_database_initialized() -> bool:
    init_db()
    return True


@st.cache_data(ttl=300, show_spinner=False)
def _refresh_employee_active_statuses() -> bool:
    refresh_employee_active_statuses()
    return True

try:
    _ensure_database_initialized()
    _refresh_employee_active_statuses()
except RuntimeError as exc:
    st.error(redact_sensitive(str(exc) or DATABASE_CONFIG_ERROR))
    st.stop()
except Exception as exc:
    log_sanitized_exception("Falha ao inicializar banco", exc)
    st.error(
        "Não foi possível inicializar o banco. Confira a configuração do "
        "Supabase/PostgreSQL nos Secrets."
    )
    st.stop()

apply_kaisan_admin_theme()
require_login()

menu_options = menu_options_for_user(current_user())

query_menu = st.query_params.get(NAV_QUERY_KEY, "")
if isinstance(query_menu, list):
    query_menu = query_menu[0] if query_menu else ""

if "main_menu" not in st.session_state:
    st.session_state["main_menu"] = query_menu if query_menu in menu_options else menu_options[0]

current_menu = st.session_state.get("main_menu", menu_options[0])
if current_menu not in menu_options:
    current_menu = menu_options[0]
st.session_state["main_menu"] = current_menu
if st.session_state.get(NAV_WIDGET_KEY) not in menu_options:
    st.session_state[NAV_WIDGET_KEY] = current_menu

operation_status = st.session_state.get("kaisan_operation_status") or {}
sidebar_marker = str(operation_status.get("time", ""))
sidebar_steps, sidebar_stats, sidebar_month = _sidebar_snapshot(
    tuple(menu_options),
    sidebar_marker,
)
for step in sidebar_steps:
    step["active"] = step.get("option") == current_menu

selected_menu = render_sidebar_navigation(
    sidebar_month,
    sidebar_steps,
    sidebar_stats,
    query_key=NAV_QUERY_KEY,
    key=NAV_WIDGET_KEY,
)
if selected_menu and selected_menu != current_menu:
    st.session_state["main_menu"] = selected_menu
    st.query_params[NAV_QUERY_KEY] = selected_menu
    st.rerun()

render_user_sidebar()

menu = current_menu

st.sidebar.markdown("---")
st.sidebar.caption(
    "Fluxo: pessoas, usuários, semanal, monitoria e fechamento."
)

if menu == "1. Funcionários":
    from ui_employees import page_employees

    page_employees()

elif menu == "2. Usuários":
    from ui_users import page_users

    page_users()

elif menu == "3. Avaliação Semanal":
    from ui_weekly import page_weekly

    page_weekly()

elif menu == "4. Monitoria Mensal":
    from ui_monitor import render_monitor_page

    render_monitor_page()

elif menu == "5. Relatório Mensal":
    from ui_report import render_report_page

    render_report_page()
