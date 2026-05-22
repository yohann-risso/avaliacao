import streamlit as st

from db import authenticate_login, create_login_user, login_user_count
from theme import render_page_header, render_status_notice


AUTH_STATE_KEY = "auth_user"


def _set_auth_user(user: dict):
    st.session_state[AUTH_STATE_KEY] = {
        "id": int(user["id"]),
        "username": str(user["username"]),
        "role": str(user.get("role", "admin")),
    }


def _render_first_admin_form():
    render_page_header(
        "Configurar login",
        "Crie o primeiro administrador para proteger o acesso ao aplicativo.",
        kicker="Primeiro acesso",
    )
    render_status_notice(
        "Nenhum usuário de login cadastrado",
        "Cadastre o primeiro administrador antes de usar o sistema.",
        "warning",
    )

    with st.form("form_first_admin"):
        username = st.text_input("Usuário", value="admin")
        password = st.text_input("Senha", type="password")
        password_confirm = st.text_input("Confirmar senha", type="password")
        submitted = st.form_submit_button("Criar administrador", type="primary")

    if not submitted:
        return

    if password != password_confirm:
        st.error("As senhas não conferem.")
        return

    try:
        user_id = create_login_user(username, password, role="admin", active=True)
    except ValueError as exc:
        st.error(str(exc))
        return

    _set_auth_user({"id": user_id, "username": username.strip().lower(), "role": "admin"})
    st.success("Administrador criado.")
    st.rerun()


def _render_login_form():
    render_page_header(
        "Acesso restrito",
        "Entre com seu usuário e senha para continuar.",
        kicker="Login",
    )

    with st.form("form_login"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar", type="primary")

    if not submitted:
        return

    try:
        user = authenticate_login(username, password)
    except ValueError:
        user = None

    if not user:
        st.error("Usuário ou senha inválidos.")
        return

    _set_auth_user(user)
    st.rerun()


def require_login():
    if st.session_state.get(AUTH_STATE_KEY):
        return

    if login_user_count() == 0:
        _render_first_admin_form()
    else:
        _render_login_form()
    st.stop()


def current_user() -> dict:
    return st.session_state.get(AUTH_STATE_KEY) or {}


def is_admin_user(user: dict | None = None) -> bool:
    user = user if user is not None else current_user()
    return str((user or {}).get("role", "")).strip().lower() == "admin"


def require_admin():
    if is_admin_user():
        return

    render_page_header(
        "Acesso administrativo",
        "Esta área é exclusiva para usuários administradores.",
        kicker="Permissão",
    )
    render_status_notice(
        "Usuário sem permissão",
        "Entre com uma conta de administrador para cadastrar ou alterar funcionários.",
        "warning",
    )
    st.stop()


def render_user_sidebar():
    user = st.session_state.get(AUTH_STATE_KEY) or {}
    username = str(user.get("username", "")).strip()
    if username:
        role = str(user.get("role", "")).strip()
        suffix = f" ({role})" if role else ""
        st.sidebar.caption(f"Logado como {username}{suffix}")

    if st.sidebar.button("Sair", type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
