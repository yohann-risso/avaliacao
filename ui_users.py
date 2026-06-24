# ui_users.py
import pandas as pd
import streamlit as st

from db import (
    create_login_user,
    list_active_leadership_evaluators,
    list_login_users,
    update_login_user,
)
from theme import (
    mark_operation_status,
    render_operation_status,
    render_page_header,
    render_section_header,
    render_status_cards,
    render_status_notice,
)
from ui_auth import current_user, require_admin
from utils import datetime_iso_to_br


ROLE_OPTIONS = {
    "Avaliador": "avaliador",
    "Administrador": "admin",
}
ROLE_LABELS = {value: label for label, value in ROLE_OPTIONS.items()}
EMPTY_EVALUATOR_LABEL = "(Sem vínculo)"


def _role_label(value: str) -> str:
    return ROLE_LABELS.get(str(value or "").strip().lower(), str(value or "").strip() or "-")


def _is_truthy(value) -> bool:
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    try:
        return int(value or 0) == 1
    except (TypeError, ValueError):
        return False


def _optional_int(value) -> int | None:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if value in (None, "", 0, "0"):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _evaluator_label(row: pd.Series) -> str:
    name = str(row.get("name", "")).strip()
    sector = str(row.get("sector", "")).strip()
    role = str(row.get("role", "")).strip()
    suffix = " · ".join(part for part in (sector, role) if part)
    return f"{name} ({suffix})" if suffix else name


def _append_evaluator_option(
    options: list[str],
    mapping: dict[str, int | None],
    label: str,
    employee_id: int | None,
) -> str:
    if employee_id is None:
        return EMPTY_EVALUATOR_LABEL

    label = str(label or "").strip() or f"Funcionário #{employee_id}"
    if label in mapping and mapping[label] == employee_id:
        return label

    if label in mapping:
        base_label = f"{label} · ID {employee_id}"
        label = base_label
        counter = 2
        while label in mapping and mapping[label] != employee_id:
            label = f"{base_label} ({counter})"
            counter += 1

    if label not in mapping:
        options.append(label)
    mapping[label] = employee_id
    return label


def _evaluator_options(evaluators: pd.DataFrame) -> tuple[list[str], dict[str, int | None]]:
    options = [EMPTY_EVALUATOR_LABEL]
    mapping: dict[str, int | None] = {EMPTY_EVALUATOR_LABEL: None}
    if evaluators is None or evaluators.empty:
        return options, mapping

    for _, row in evaluators.iterrows():
        label = _evaluator_label(row)
        employee_id = _optional_int(row.get("id"))
        if not label or employee_id is None:
            continue
        _append_evaluator_option(options, mapping, label, employee_id)
    return options, mapping


def _option_index(options: list[str], current: str) -> int:
    return options.index(current) if current in options else 0


def _label_for_evaluator_id(mapping: dict[str, int | None], evaluator_id) -> str:
    wanted_id = _optional_int(evaluator_id)
    if wanted_id is None:
        return EMPTY_EVALUATOR_LABEL

    for label, mapped_id in mapping.items():
        if mapped_id == wanted_id:
            return label
    return EMPTY_EVALUATOR_LABEL


def _edit_evaluator_options(
    evaluator_options: list[str],
    evaluator_map: dict[str, int | None],
    selected_row: pd.Series,
) -> tuple[list[str], dict[str, int | None], str, bool]:
    options = list(evaluator_options)
    mapping = dict(evaluator_map)

    current_id = _optional_int(selected_row.get("evaluator_employee_id"))
    current_label = _label_for_evaluator_id(mapping, current_id)
    if current_id is None or current_label != EMPTY_EVALUATOR_LABEL:
        return options, mapping, current_label, False

    linked_row = pd.Series({
        "name": selected_row.get("evaluator_name", ""),
        "sector": selected_row.get("evaluator_sector", ""),
        "role": selected_row.get("evaluator_role", ""),
    })
    label = _evaluator_label(linked_row)
    if label:
        label = f"{label} · vínculo atual"
    else:
        label = f"Funcionário #{current_id} · vínculo atual"

    current_label = _append_evaluator_option(options, mapping, label, current_id)
    return options, mapping, current_label, True


def _current_evaluator_warning(selected_row: pd.Series) -> str:
    current_id = _optional_int(selected_row.get("evaluator_employee_id"))
    name = str(selected_row.get("evaluator_name", "") or "").strip() or f"ID {current_id}"
    reasons = []
    if not _is_truthy(selected_row.get("evaluator_active")):
        reasons.append("não está ativo")
    if not _is_truthy(selected_row.get("evaluator_is_leadership")):
        reasons.append("não está marcado como coordenação/supervisão")

    reason_text = " e ".join(reasons) if reasons else "não está na lista de avaliadores ativos"
    return (
        f"O vínculo atual ({name}) existe no banco, mas {reason_text}. "
        "Para salvar este usuário com vínculo válido, ajuste o cadastro do funcionário ou selecione outro avaliador."
    )


def page_users():
    require_admin()
    admin_user = current_user()
    admin_username = str(admin_user.get("username", "")).strip()
    admin_id = int(admin_user.get("id")) if admin_user.get("id") is not None else None

    render_page_header(
        title="Usuários",
        subtitle="Cadastro de acesso ao sistema com vínculo do login ao avaliador responsável.",
        icon="👥",
        kicker="Etapa 2",
        meta=[f"Admin: {admin_username}"] if admin_username else None,
    )
    render_operation_status()

    evaluators = list_active_leadership_evaluators()
    evaluator_options, evaluator_map = _evaluator_options(evaluators)

    tabs = st.tabs(["Cadastrar", "Listar & Gerenciar"])

    with tabs[0]:
        render_section_header(
            "Novo usuário",
            "Crie o login e associe a conta a um avaliador ativo de coordenação/supervisão.",
            "Cadastro",
        )

        if evaluators.empty:
            render_status_notice(
                "Nenhum avaliador ativo encontrado",
                "Cadastre ou ative um funcionário como coordenação/supervisão antes de criar usuários avaliadores.",
                "warning",
            )

        with st.form("form_new_login_user", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns([1.2, 1, 1.5, 0.7], gap="medium")
            with col1:
                username = st.text_input("Usuário*", placeholder="Ex.: joao.silva")
            with col2:
                role_label = st.selectbox(
                    "Perfil*",
                    list(ROLE_OPTIONS.keys()),
                    help="Usuários avaliadores precisam estar vinculados a uma coordenação/supervisão ativa.",
                )
            with col3:
                evaluator_label = st.selectbox(
                    "Avaliador vinculado*",
                    evaluator_options,
                    index=1 if len(evaluator_options) > 1 else 0,
                    help="Obrigatório para o perfil Avaliador; opcional para Administrador.",
                )
            with col4:
                active = st.toggle("Ativo", value=True)

            pass1, pass2 = st.columns(2, gap="medium")
            with pass1:
                password = st.text_input("Senha*", type="password")
            with pass2:
                password_confirm = st.text_input("Confirmar senha*", type="password")

            st.caption("Para perfil Avaliador, vincule o login a um avaliador ativo antes de cadastrar.")
            submitted = st.form_submit_button("Cadastrar usuário", type="primary")

        if submitted:
            role = ROLE_OPTIONS[role_label]
            evaluator_employee_id = evaluator_map.get(evaluator_label)

            if not username.strip():
                st.error("Preencha o **Usuário**.")
                st.stop()
            if password != password_confirm:
                st.error("As senhas não conferem.")
                st.stop()
            if role == "avaliador" and evaluator_employee_id is None:
                st.error("Vincule o usuário a um avaliador.")
                st.stop()

            try:
                with st.spinner("Gravando usuário no banco..."):
                    create_login_user(
                        username=username,
                        password=password,
                        role=role,
                        active=active,
                        evaluator_employee_id=evaluator_employee_id,
                    )
            except ValueError as exc:
                st.error(str(exc))
                st.stop()

            mark_operation_status(
                "Usuário gravado no banco",
                f"{username.strip()} foi cadastrado com vínculo de avaliador.",
                "success",
            )
            st.rerun()

    with tabs[1]:
        render_section_header(
            "Usuários de acesso",
            "Confira vínculos, altere perfil, status, avaliador e senha quando necessário.",
            "Gestão",
        )

        users = list_login_users()
        if users.empty:
            st.info("Nenhum usuário cadastrado.")
            return

        active_count = int(users["active"].fillna(0).astype(int).sum())
        linked_count = int(users["evaluator_employee_id"].notna().sum())
        admin_count = int((users["role"].fillna("").astype(str).str.lower() == "admin").sum())
        render_status_cards([
            {"title": "Usuários ativos", "value": str(active_count), "detail": "com acesso liberado", "tone": "success" if active_count else "warning"},
            {"title": "Vinculados", "value": str(linked_count), "detail": "com avaliador definido", "tone": "info"},
            {"title": "Administradores", "value": str(admin_count), "detail": "podem gerenciar cadastros", "tone": "violet"},
        ])

        show = users.copy()
        show["Status"] = show["active"].apply(lambda value: "ATIVO" if _is_truthy(value) else "INATIVO")
        show["Perfil"] = show["role"].apply(_role_label)
        show["Avaliador"] = show["evaluator_name"].fillna("").astype(str).replace("", "-")
        show["Último login"] = show["last_login_at"].apply(datetime_iso_to_br)
        show["Criado em"] = show["created_at"].apply(datetime_iso_to_br)
        show["Atualizado em"] = show["updated_at"].apply(datetime_iso_to_br)
        st.dataframe(
            show[["username", "Perfil", "Status", "Avaliador", "Último login", "Criado em", "Atualizado em"]].rename(columns={"username": "Usuário"}),
            width="stretch",
            hide_index=True,
        )

        st.markdown("### Editar usuário")
        user_labels = {}
        for _, row in users.iterrows():
            status = "ativo" if _is_truthy(row.get("active")) else "inativo"
            label = f"{row['username']} · {_role_label(row.get('role'))} · {status}"
            user_labels[label] = int(row["id"])

        selected_label = st.selectbox("Selecione o usuário", list(user_labels.keys()), key="login_user_edit_select")
        selected_id = user_labels[selected_label]
        selected_row = users[users["id"].astype(int) == int(selected_id)].iloc[0]
        current_role_label = ROLE_LABELS.get(str(selected_row.get("role", "admin")).strip().lower(), "Avaliador")
        edit_evaluator_options, edit_evaluator_map, current_evaluator_label, current_evaluator_needs_fix = _edit_evaluator_options(
            evaluator_options,
            evaluator_map,
            selected_row,
        )

        if current_evaluator_needs_fix:
            st.warning(_current_evaluator_warning(selected_row))

        with st.form(f"form_edit_login_user_{selected_id}"):
            col1, col2, col3, col4 = st.columns([1.2, 1, 1.5, 0.7], gap="medium")
            with col1:
                edit_username = st.text_input("Usuário*", value=str(selected_row.get("username", "")))
            with col2:
                edit_role_label = st.selectbox(
                    "Perfil*",
                    list(ROLE_OPTIONS.keys()),
                    index=_option_index(list(ROLE_OPTIONS.keys()), current_role_label),
                    help="Usuários avaliadores precisam estar vinculados a uma coordenação/supervisão ativa.",
                )
            with col3:
                edit_evaluator_label = st.selectbox(
                    "Avaliador vinculado*",
                    edit_evaluator_options,
                    index=_option_index(edit_evaluator_options, current_evaluator_label),
                    help="Obrigatório para o perfil Avaliador; opcional para Administrador.",
                )
            with col4:
                edit_active = st.toggle("Ativo", value=_is_truthy(selected_row.get("active")))

            pass1, pass2 = st.columns(2, gap="medium")
            with pass1:
                new_password = st.text_input("Nova senha", type="password", placeholder="Deixe em branco para manter")
            with pass2:
                new_password_confirm = st.text_input("Confirmar nova senha", type="password")

            st.caption("Para perfil Avaliador, mantenha um avaliador ativo vinculado ao login.")
            submitted_update = st.form_submit_button("Salvar usuário", type="primary")

        if submitted_update:
            role = ROLE_OPTIONS[edit_role_label]
            evaluator_employee_id = edit_evaluator_map.get(edit_evaluator_label)

            if not edit_username.strip():
                st.error("Preencha o **Usuário**.")
                st.stop()
            if new_password != new_password_confirm:
                st.error("As senhas não conferem.")
                st.stop()
            if role == "avaliador" and evaluator_employee_id is None:
                st.error("Vincule o usuário a um avaliador.")
                st.stop()
            if admin_id == int(selected_id) and (not edit_active or role != "admin"):
                st.error("Você não pode remover seu próprio acesso administrativo nesta sessão.")
                st.stop()

            try:
                with st.spinner("Atualizando usuário no banco..."):
                    update_login_user(
                        user_id=int(selected_id),
                        username=edit_username,
                        role=role,
                        active=edit_active,
                        evaluator_employee_id=evaluator_employee_id,
                        password=new_password,
                    )
            except ValueError as exc:
                st.error(str(exc))
                st.stop()

            mark_operation_status(
                "Usuário atualizado",
                f"{edit_username.strip()} foi salvo com o vínculo selecionado.",
                "success",
            )
            st.rerun()
