import streamlit as st

from db import init_db
from theme import apply_kaisan_admin_theme
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

st.sidebar.title("Avaliação & Bonificação")
st.sidebar.caption("Fluxo simples para avaliar, revisar e fechar o mês.")

menu = st.sidebar.radio(
    "Etapa",
    [
        "1. Funcionários",
        "2. Avaliação Semanal",
        "3. Monitoria Mensal",
        "4. Relatório Mensal",
    ],
)

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
