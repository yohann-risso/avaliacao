# ui_employees.py

import streamlit as st
import pandas as pd

from db import (
    insert_employee,
    deactivate_employee,
    list_employees,
    reactivate_employee,
    update_employee,
)
from constants import TENURE_BONUS_PER_YEAR
from theme import (
    mark_operation_status,
    render_divider,
    render_focus_strip,
    render_operation_status,
    render_page_header,
    render_section_header,
    render_status_cards,
)
from ui_auth import current_user, require_admin
from utils import date_iso_to_br, datetime_iso_to_br, brl


def _years_in_company(hire_date_iso: str) -> int:
    from datetime import date, datetime

    if not str(hire_date_iso or "").strip():
        return 0
    try:
        hire_date = datetime.strptime(str(hire_date_iso).strip(), "%Y-%m-%d").date()
    except Exception:
        return 0

    today = date.today()
    years = today.year - hire_date.year
    if (today.month, today.day) < (hire_date.month, hire_date.day):
        years -= 1
    return max(0, years)


def page_employees():
    require_admin()
    admin_user = current_user()
    admin_id = int(admin_user.get("id")) if admin_user.get("id") is not None else None
    admin_username = str(admin_user.get("username", "")).strip()

    render_page_header(
        title="Funcionários",
        subtitle="Cadastro administrativo de colaboradores com trilha de auditoria do usuário logado.",
        icon="👤",
        kicker="Etapa 1",
        meta=[f"Admin: {admin_username}"] if admin_username else None,
    )
    render_operation_status()

    tabs = st.tabs(["Cadastrar", "Listar & Gerenciar"])

    # =========================================================
    # TAB 1: Cadastro
    # =========================================================
    with tabs[0]:
        render_section_header(
            "Novo funcionário",
            "Preencha apenas os dados necessários para liberar a pessoa nos fluxos de avaliação.",
            "Cadastro",
        )

        with st.form("form_new_employee", clear_on_submit=True):
            col1, col2, col3, col4, col5 = st.columns([1.5, 1.1, 1.1, 1, 1], gap="medium")

            with col1:
                name = st.text_input("Nome*", placeholder="Ex.: Kaique Teixeira")
            with col2:
                sector = st.text_input("Setor*", placeholder="Ex.: Expedição")
            with col3:
                role = st.text_input("Função*", placeholder="Ex.: Separador")
            with col4:
                hire_date = st.text_input("Contratação", placeholder="DD/MM/AAAA")
            with col5:
                termination_date = st.text_input("Desligamento", placeholder="DD/MM/AAAA")

            cA, cB, cC, cD = st.columns([1, 1, 1.3, 1], gap="medium")
            with cA:
                is_monitor = st.toggle("É MONITOR?", value=False)
            with cB:
                monitor_start_date = st.text_input("Monitor desde", placeholder="DD/MM/AAAA")
            with cC:
                is_leadership = st.toggle("Coord./Supervisão?", value=False)
                st.caption("Coordenação/supervisão entra no relatório separado, com base padrão e sem avaliação semanal.")
            with cD:
                leadership_start_date = st.text_input("Coord./Sup. desde", placeholder="DD/MM/AAAA")
                st.caption("Preencha a data quando marcar monitor ou coord./supervisão.")

            p1, p2 = st.columns(2, gap="medium")
            with p1:
                picking_operator_name = st.text_input(
                    "Operador Picking",
                    placeholder="Vazio usa o Nome",
                    help="Nome do operador no picking-kaisan/admin.",
                )
            with p2:
                bybox_operator_name = st.text_input(
                    "Operador By-Box",
                    placeholder="Vazio usa o Nome",
                    help="Nome do operador no picking-by-box-kaisan/admin.",
                )

            submitted = st.form_submit_button("Cadastrar funcionário")

            if submitted:
                if not name.strip():
                    st.error("Preencha o **Nome**.")
                    st.stop()
                if not sector.strip():
                    st.error("Preencha o **Setor**.")
                    st.stop()
                if not role.strip():
                    st.error("Preencha a **Função**.")
                    st.stop()
                if not str(hire_date or "").strip():
                    st.error("Preencha a **Contratação**.")
                    st.stop()
                if is_monitor and is_leadership:
                    st.error("Coordenação/supervisão não pode ser monitor.")
                    st.stop()
                if is_monitor and not str(monitor_start_date or "").strip():
                    st.error("Preencha **Monitor desde**.")
                    st.stop()
                if is_leadership and not str(leadership_start_date or "").strip():
                    st.error("Preencha **Coord./Sup. desde**.")
                    st.stop()

                try:
                    with st.spinner("Gravando funcionário no banco..."):
                        insert_employee(
                            name=name,
                            sector=sector,
                            role=role,
                            is_monitor=is_monitor,
                            hire_date=hire_date,
                            is_leadership=is_leadership,
                            monitor_start_date=monitor_start_date,
                            leadership_start_date=leadership_start_date,
                            termination_date=termination_date,
                            picking_operator_name=picking_operator_name,
                            bybox_operator_name=bybox_operator_name,
                            created_by_user_id=admin_id,
                            created_by_username=admin_username,
                        )
                except ValueError as exc:
                    st.error(str(exc))
                    st.stop()
                mark_operation_status(
                    "Funcionário gravado no banco",
                    f"{name.strip()} foi cadastrado e liberado para os fluxos aplicáveis.",
                    "success",
                )
                st.rerun()

        st.info("Depois de cadastrar, use **Listar & Gerenciar** para conferir, filtrar, editar, desativar ou reativar.")

    # =========================================================
    # TAB 2: Listar & Gerenciar
    # =========================================================
    with tabs[1]:
        render_section_header(
            "Funcionários",
            "Filtre, confira indicadores do cadastro e edite dados sem apagar histórico.",
            "Gestão",
        )

        df = list_employees(include_inactive=True)
        if df.empty:
            st.info("Nenhum funcionário cadastrado.")
            return

        # Normaliza colunas para UI
        show = df.copy()
        show["Status"] = show["active"].apply(lambda x: "ATIVO" if int(x) == 1 else "DESATIVADO")
        show["Monitor"] = show["is_monitor"].apply(lambda x: "SIM" if int(x) == 1 else "NÃO")
        show["Coord./Supervisão"] = show["is_leadership"].apply(lambda x: "SIM" if int(x) == 1 else "NÃO")
        show["Contratação"] = show["hire_date"].apply(date_iso_to_br)
        show["Monitor desde"] = show["monitor_start_date"].apply(date_iso_to_br)
        show["Coord./Supervisão desde"] = show["leadership_start_date"].apply(date_iso_to_br)
        show["Desligamento"] = show["termination_date"].apply(date_iso_to_br)
        show["Desativado em"] = show["deactivated_at"].apply(datetime_iso_to_br)
        show["Criado por"] = show["created_by_username"].fillna("").astype(str).replace("", "-")
        show["Atualizado por"] = show["updated_by_username"].fillna("").astype(str).replace("", "-")
        show["Atualizado em"] = show["updated_at"].apply(datetime_iso_to_br)
        show["Anos empresa"] = show["hire_date"].apply(_years_in_company)
        show["Adicional tempo"] = show["Anos empresa"].apply(lambda years: brl(float(years * TENURE_BONUS_PER_YEAR)))
        show["Operador Picking"] = show["picking_operator_name"].fillna("").astype(str).replace("", "-")
        show["Operador By-Box"] = show["bybox_operator_name"].fillna("").astype(str).replace("", "-")
        show = show.rename(columns={"name": "Nome", "sector": "Setor", "role": "Função"})

        # ---------- Filtros ----------
        f1, f2, f3, f4, f5 = st.columns([1.5, 1.1, 1.1, 1, 1], gap="medium")

        with f1:
            q = st.text_input("Busca", placeholder="Digite nome, setor ou função...")
        with f2:
            sectors = ["(Todos)"] + sorted(show["Setor"].dropna().astype(str).unique().tolist())
            sector_filter = st.selectbox("Setor", sectors)
        with f3:
            roles = ["(Todas)"] + sorted(show["Função"].dropna().astype(str).unique().tolist())
            role_filter = st.selectbox("Função", roles)
        with f4:
            monitor_only = st.toggle("Só monitores", value=False)
        with f5:
            status_filter = st.selectbox("Status", ["Ativos", "Todos", "Desativados"])

        filtered = show.copy()

        if q.strip():
            qq = q.strip().lower()
            filtered = filtered[
                filtered["Nome"].astype(str).str.lower().str.contains(qq, regex=False, na=False)
                | filtered["Setor"].astype(str).str.lower().str.contains(qq, regex=False, na=False)
                | filtered["Função"].astype(str).str.lower().str.contains(qq, regex=False, na=False)
            ]

        if sector_filter != "(Todos)":
            filtered = filtered[filtered["Setor"] == sector_filter]

        if role_filter != "(Todas)":
            filtered = filtered[filtered["Função"] == role_filter]

        if monitor_only:
            filtered = filtered[filtered["Monitor"] == "SIM"]

        if status_filter == "Ativos":
            filtered = filtered[filtered["Status"] == "ATIVO"]
        elif status_filter == "Desativados":
            filtered = filtered[filtered["Status"] == "DESATIVADO"]

        # ---------- Resumo ----------
        missing_hire = int((show["Contratação"].astype(str).str.strip().isin(["", "-"])).sum())
        missing_monitor_start = int(((show["Monitor"] == "SIM") & (show["Monitor desde"].astype(str).str.strip().isin(["", "-"]))).sum())
        missing_leadership_start = int(((show["Coord./Supervisão"] == "SIM") & (show["Coord./Supervisão desde"].astype(str).str.strip().isin(["", "-"]))).sum())
        cadastro_issues = missing_hire + missing_monitor_start + missing_leadership_start

        render_status_cards([
            {
                "title": "Ativos",
                "value": int((show["Status"] == "ATIVO").sum()),
                "detail": "Entram nos fluxos da competência.",
                "tone": "success",
            },
            {
                "title": "Exibidos",
                "value": len(filtered),
                "detail": "Resultado do filtro atual.",
                "tone": "info",
            },
            {
                "title": "Monitores",
                "value": int((show["Monitor"] == "SIM").sum()),
                "detail": "Elegíveis para monitoria mensal quando data permitir.",
                "tone": "info",
            },
            {
                "title": "Coord./Sup.",
                "value": int((show["Coord./Supervisão"] == "SIM").sum()),
                "detail": "Aparecem no relatório separado.",
                "tone": "violet",
            },
            {
                "title": "Pendências cadastro",
                "value": cadastro_issues,
                "detail": "Datas obrigatórias que podem travar fechamento.",
                "tone": "success" if cadastro_issues == 0 else "warning",
            },
        ])

        if cadastro_issues:
            render_focus_strip(
                "Completar datas obrigatórias do cadastro.",
                "Contratação, Monitor desde e Coord./Sup. desde controlam elegibilidade e fechamento.",
                [
                    {"label": f"{missing_hire} contratação", "tone": "warning"},
                    {"label": f"{missing_monitor_start} monitor", "tone": "warning"},
                    {"label": f"{missing_leadership_start} coord./sup.", "tone": "warning"},
                ],
                "warning",
            )

        render_divider()

        st.dataframe(
            filtered[[
                "id", "Nome", "Setor", "Função", "Status", "Contratação", "Desativado em",
                "Desligamento", "Anos empresa", "Adicional tempo", "Monitor", "Monitor desde",
                "Coord./Supervisão", "Coord./Supervisão desde", "Operador Picking", "Operador By-Box",
                "Criado por", "Atualizado por", "Atualizado em",
            ]],
            width="stretch",
            hide_index=True
        )

        render_divider()
        render_section_header(
            "Editar funcionário",
            "Atualize cadastro, setor, função e marcações sem apagar o histórico.",
            "Manutenção",
        )

        base_for_select = filtered if not filtered.empty else show
        emp_map = {
            f'{r["Nome"]} • {r["Setor"]} • {r["Função"]} • MONITOR:{r["Monitor"]} • COORD:{r["Coord./Supervisão"]}': int(r["id"])
            for _, r in base_for_select.iterrows()
        }

        if not emp_map:
            st.info("Nenhum funcionário disponível para editar.")
            return

        selected_edit_label = st.selectbox(
            "Selecione o funcionário para editar",
            list(emp_map.keys()),
            key="employee_edit_select"
        )

        selected_edit_id = emp_map[selected_edit_label]
        edit_row = df[df["id"] == selected_edit_id].iloc[0]

        with st.form("form_edit_employee"):
            e1, e2, e3, e4, e5 = st.columns([1.5, 1.1, 1.1, 1, 1], gap="medium")

            with e1:
                edit_name = st.text_input(
                    "Nome*",
                    value=str(edit_row["name"]),
                    placeholder="Ex.: Kaique Teixeira"
                )

            with e2:
                edit_sector = st.text_input(
                    "Setor*",
                    value=str(edit_row["sector"]),
                    placeholder="Ex.: Expedição"
                )

            with e3:
                edit_role = st.text_input(
                    "Função*",
                    value=str(edit_row["role"]),
                    placeholder="Ex.: Separador"
                )
            with e4:
                edit_hire_date = st.text_input(
                    "Contratação",
                    value=date_iso_to_br(str(edit_row.get("hire_date", "") or "")) if str(edit_row.get("hire_date", "") or "").strip() else "",
                    placeholder="DD/MM/AAAA"
                )
            with e5:
                edit_termination_date = st.text_input(
                    "Desligamento",
                    value=date_iso_to_br(str(edit_row.get("termination_date", "") or "")) if str(edit_row.get("termination_date", "") or "").strip() else "",
                    placeholder="DD/MM/AAAA",
                )

            cA, cB, cC, cD = st.columns([1, 1, 1.3, 1], gap="medium")
            with cA:
                edit_is_monitor = st.toggle(
                    "É MONITOR?",
                    value=bool(int(edit_row["is_monitor"]))
                )
            with cB:
                edit_monitor_start_date = st.text_input(
                    "Monitor desde",
                    value=date_iso_to_br(str(edit_row.get("monitor_start_date", "") or "")) if str(edit_row.get("monitor_start_date", "") or "").strip() else "",
                    placeholder="DD/MM/AAAA",
                )
            with cC:
                edit_is_leadership = st.toggle(
                    "Coord./Supervisão?",
                    value=bool(int(edit_row.get("is_leadership", 0)))
                )
                st.caption("Se marcado, não entra em avaliação semanal/monitoria.")
            with cD:
                edit_leadership_start_date = st.text_input(
                    "Coord./Sup. desde",
                    value=date_iso_to_br(str(edit_row.get("leadership_start_date", "") or "")) if str(edit_row.get("leadership_start_date", "") or "").strip() else "",
                    placeholder="DD/MM/AAAA",
                )
                st.caption("Atualize a data quando a função mudar.")

            p1, p2 = st.columns(2, gap="medium")
            with p1:
                edit_picking_operator_name = st.text_input(
                    "Operador Picking",
                    value=str(edit_row.get("picking_operator_name", "") or ""),
                    placeholder="Vazio usa o Nome",
                    help="Nome do operador no picking-kaisan/admin.",
                )
            with p2:
                edit_bybox_operator_name = st.text_input(
                    "Operador By-Box",
                    value=str(edit_row.get("bybox_operator_name", "") or ""),
                    placeholder="Vazio usa o Nome",
                    help="Nome do operador no picking-by-box-kaisan/admin.",
                )

            save_edit = st.form_submit_button("Salvar alterações")

            if save_edit:
                if not edit_name.strip():
                    st.error("Preencha o **Nome**.")
                    st.stop()
                if not edit_sector.strip():
                    st.error("Preencha o **Setor**.")
                    st.stop()
                if not edit_role.strip():
                    st.error("Preencha a **Função**.")
                    st.stop()
                if not str(edit_hire_date or "").strip():
                    st.error("Preencha a **Contratação**.")
                    st.stop()
                if edit_is_monitor and edit_is_leadership:
                    st.error("Coordenação/supervisão não pode ser monitor.")
                    st.stop()
                if edit_is_monitor and not str(edit_monitor_start_date or "").strip():
                    st.error("Preencha **Monitor desde**.")
                    st.stop()
                if edit_is_leadership and not str(edit_leadership_start_date or "").strip():
                    st.error("Preencha **Coord./Sup. desde**.")
                    st.stop()

                try:
                    with st.spinner("Atualizando cadastro no banco..."):
                        update_employee(
                            employee_id=int(selected_edit_id),
                            name=edit_name,
                            sector=edit_sector,
                            role=edit_role,
                            is_monitor=edit_is_monitor,
                            hire_date=edit_hire_date,
                            is_leadership=edit_is_leadership,
                            monitor_start_date=edit_monitor_start_date,
                            leadership_start_date=edit_leadership_start_date,
                            termination_date=edit_termination_date,
                            picking_operator_name=edit_picking_operator_name,
                            bybox_operator_name=edit_bybox_operator_name,
                            updated_by_user_id=admin_id,
                            updated_by_username=admin_username,
                        )
                except ValueError as exc:
                    st.error(str(exc))
                    st.stop()
                mark_operation_status(
                    "Cadastro atualizado no banco",
                    f"{edit_name.strip()} foi atualizado com os dados informados.",
                    "success",
                )
                st.rerun()

        render_divider()
        render_section_header(
            "Status do funcionário",
            "Desativar apenas muda o status; cadastro e histórico permanecem consultáveis.",
            "Ativação",
        )

        active_for_action = show[show["Status"] == "ATIVO"].copy()
        inactive_for_action = show[show["Status"] == "DESATIVADO"].copy()

        colD1, colD2 = st.columns([2, 1], gap="medium")
        with colD1:
            active_map = {
                f'{r["Nome"]} • {r["Setor"]} • {r["Função"]}': int(r["id"])
                for _, r in active_for_action.iterrows()
            }
            selected_deactivate = st.selectbox("Selecione para desativar", list(active_map.keys()), key="employee_deactivate_select") if active_map else None
        with colD2:
            confirm = st.checkbox("Confirmar desativação", key="employee_deactivate_confirm")

        if st.button("Desativar selecionado", type="secondary"):
            if not selected_deactivate:
                st.error("Não há funcionário ativo para desativar.")
                st.stop()
            if not confirm:
                st.error("Marque **Confirmar desativação** para continuar.")
                st.stop()

            with st.spinner("Atualizando status no banco..."):
                deactivate_employee(
                    active_map[selected_deactivate],
                    updated_by_user_id=admin_id,
                    updated_by_username=admin_username,
                )
            mark_operation_status(
                "Funcionário desativado",
                f"{selected_deactivate} permanece no histórico e sai dos fluxos ativos.",
                "warning",
            )
            st.rerun()

        st.markdown("#### Reativar funcionário")
        colR1, colR2 = st.columns([2, 1], gap="medium")
        with colR1:
            inactive_map = {
                f'{r["Nome"]} • {r["Setor"]} • {r["Função"]}': int(r["id"])
                for _, r in inactive_for_action.iterrows()
            }
            selected_reactivate = st.selectbox("Selecione para reativar", list(inactive_map.keys()), key="employee_reactivate_select") if inactive_map else None
        with colR2:
            confirm_reactivate = st.checkbox("Confirmar reativação", key="employee_reactivate_confirm")

        if st.button("Reativar selecionado", type="secondary"):
            if not selected_reactivate:
                st.error("Não há funcionário desativado para reativar.")
                st.stop()
            if not confirm_reactivate:
                st.error("Marque **Confirmar reativação** para continuar.")
                st.stop()

            with st.spinner("Atualizando status no banco..."):
                reactivate_employee(
                    inactive_map[selected_reactivate],
                    updated_by_user_id=admin_id,
                    updated_by_username=admin_username,
                )
            mark_operation_status(
                "Funcionário reativado",
                f"{selected_reactivate} voltou para os fluxos ativos.",
                "success",
            )
            st.rerun()
