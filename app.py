import streamlit as st

from db import init_db
from theme import apply_kaisan_admin_theme
from ui_auth import current_user, is_admin_user, render_user_sidebar, require_login
from ui_employees import page_employees
from ui_weekly import page_weekly
from ui_monitor import render_monitor_page
from ui_report import render_report_page


st.set_page_config(
    page_title="Avaliação & Bonificação • Estoque e Expedição",
    layout="wide",
    initial_sidebar_state="auto",
)

init_db()
apply_kaisan_admin_theme()
require_login()

st.sidebar.title("Avaliação & Bonificação")
st.sidebar.caption("Fluxo simples para avaliar, revisar e fechar o mês.")
render_user_sidebar()

menu_options = []
if is_admin_user(current_user()):
    menu_options.append("1. Funcionários")
menu_options.extend([
    "2. Avaliação Semanal",
    "3. Monitoria Mensal",
    "4. Relatório Mensal",
])

menu = st.sidebar.radio("Etapa", menu_options)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Use a ordem das etapas: cadastre, avalie a semana, lance monitoria e gere o fechamento."
)

if menu == "1. Funcionários":
    page_employees()

elif menu == "2. Avaliação Semanal":
    page_weekly()

elif menu == "3. Monitoria Mensal":
    render_monitor_page()

elif menu == "4. Relatório Mensal":
    render_report_page()
