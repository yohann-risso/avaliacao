from io import BytesIO

import pandas as pd
from openpyxl import load_workbook

import db
from weekly_eval_excel import (
    WEEKLY_EVAL_INSTRUCTIONS_SHEET_NAME,
    WEEKLY_EVAL_LISTS_SHEET_NAME,
    WEEKLY_EVAL_SHEET_NAME,
    build_weekly_eval_workbook_bytes,
    load_weekly_eval_import_file,
    prepare_weekly_eval_import,
)


def _employees() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "id": 10,
            "name": "Ana Expedição",
            "sector": "Expedição",
            "role": "Separador",
        },
        {
            "id": 20,
            "name": "Bruno Estoque",
            "sector": "Estoque",
            "role": "Conferente",
        },
    ])


def _mass_df() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Selecionar": True,
            "employee_id": 10,
            "Nome": "Ana Expedição",
            "Setor": "Expedição",
            "Função": "Separador",
            "Itens": 120,
            "Assiduidade (%)": 100,
            "Qualidade (%)": 85,
            "Taxa Erros (%)": 75,
            "Prod/Efic (%)": 90,
            "Comportamento (%)": 100,
            "Avaliador": "Líder Um",
            "Notas": "Semana de teste",
        },
        {
            "Selecionar": False,
            "employee_id": 20,
            "Nome": "Bruno Estoque",
            "Setor": "Estoque",
            "Função": "Conferente",
            "Itens": 80,
            "Assiduidade (%)": 100,
            "Qualidade (%)": 100,
            "Taxa Erros (%)": 100,
            "Prod/Efic (%)": 100,
            "Comportamento (%)": 100,
            "Avaliador": "Líder Um",
            "Notas": "",
        },
    ])


def test_build_weekly_eval_workbook_has_editable_template_and_validations():
    content = build_weekly_eval_workbook_bytes(
        _mass_df(),
        "2026-08-17",
        ["Líder Um", "Líder Dois"],
    )

    workbook = load_workbook(BytesIO(content), data_only=False)
    assert workbook.sheetnames == [
        WEEKLY_EVAL_SHEET_NAME,
        WEEKLY_EVAL_INSTRUCTIONS_SHEET_NAME,
        WEEKLY_EVAL_LISTS_SHEET_NAME,
    ]
    assert workbook[WEEKLY_EVAL_LISTS_SHEET_NAME].sheet_state == "hidden"

    sheet = workbook[WEEKLY_EVAL_SHEET_NAME]
    assert sheet["A2"].value == "SIM"
    assert sheet["A3"].value == "NÃO"
    assert sheet["B2"].value == 10
    assert sheet["F2"].value.date().isoformat() == "2026-08-17"
    assert sheet["M2"].value == '=IF(COUNTA(H2:L2)=0,"",ROUND(AVERAGE(H2:L2),1))'
    assert "Avaliadores" in workbook.defined_names
    assert {validation.type for validation in sheet.data_validations.dataValidation} == {"list", "decimal", "whole"}

    loaded = load_weekly_eval_import_file(BytesIO(content))
    assert list(loaded["employee_id"].astype(int)) == [10, 20]
    assert loaded.iloc[0]["Importar?"] == "SIM"
    preview = prepare_weekly_eval_import(
        loaded,
        _employees(),
        ["Líder Um", "Líder Dois"],
        "2026-08-17",
        "Resultado atual",
        default_evaluator="Líder Um",
    )
    assert preview["summary"] == {
        "total": 2,
        "selected": 1,
        "valid": 1,
        "invalid": 0,
        "ignored": 1,
    }


def test_prepare_weekly_eval_import_generates_justifications_from_selected_model():
    raw = pd.DataFrame([
        {
            "Importar?": "SIM",
            "employee_id": 10,
            "Nome": "Ana Expedição",
            "Semana": "2026-08-17",
            "Itens": 120,
            "Assiduidade (%)": 100,
            "Qualidade (%)": 85,
            "Taxa Erros (%)": 75,
            "Prod/Efic (%)": 90,
            "Comportamento (%)": 70,
            "Avaliador": pd.NA,
            "Notas": "Acompanhamento registrado.",
        },
        {
            "Importar?": "NÃO",
            "employee_id": 20,
            "Semana": "2026-08-17",
            "Itens": 80,
            "Assiduidade (%)": 100,
            "Qualidade (%)": 100,
            "Taxa Erros (%)": 100,
            "Prod/Efic (%)": 100,
            "Comportamento (%)": 100,
            "Avaliador": "Líder Um",
        },
    ])

    preview = prepare_weekly_eval_import(
        raw,
        _employees(),
        ["Líder Um"],
        "2026-08-17",
        "Resultado atual",
        default_evaluator="Líder Um",
    )

    assert preview["summary"] == {
        "total": 2,
        "selected": 1,
        "valid": 1,
        "invalid": 0,
        "ignored": 1,
    }
    payload = preview["valid_rows"][0]
    assert payload["employee_id"] == 10
    assert payload["evaluator"] == "Líder Um"
    assert "assiduidade plena" in payload["assiduidade_just"]
    assert "qualidade adequada" in payload["qualidade_just"]
    assert "taxa de erros foi impactada" in payload["taxa_erros_just"].lower()
    assert "produtividade adequada" in payload["produtividade_just"].lower()
    assert "intervenção" in payload["comportamento_just"]
    assert payload["notes"].startswith("Acompanhamento registrado.")
    assert "JUSTIFICATIVAS (SEMANA)" in payload["notes"]
    assert preview["preview_df"].iloc[0]["Score (%)"] == 84.0


def test_prepare_weekly_eval_import_blocks_wrong_week_duplicates_and_invalid_values():
    raw = pd.DataFrame([
        {
            "Importar?": "SIM",
            "employee_id": 10,
            "Semana": "2026-08-10",
            "Itens": -1,
            "Assiduidade (%)": 101,
            "Qualidade (%)": 80,
            "Taxa Erros (%)": 80,
            "Prod/Efic (%)": 80,
            "Comportamento (%)": 80,
            "Avaliador": "Desconhecido",
        },
        {
            "Importar?": "SIM",
            "employee_id": 10,
            "Semana": "2026-08-10",
            "Itens": 1,
            "Assiduidade (%)": 80,
            "Qualidade (%)": 80,
            "Taxa Erros (%)": 80,
            "Prod/Efic (%)": 80,
            "Comportamento (%)": 80,
            "Avaliador": "Líder Um",
        },
    ])

    preview = prepare_weekly_eval_import(
        raw,
        _employees(),
        ["Líder Um"],
        "2026-08-17",
        "Acompanhamento",
        default_evaluator="Líder Um",
    )

    assert preview["summary"]["valid"] == 0
    assert preview["summary"]["invalid"] == 2
    messages = " | ".join(preview["preview_df"]["Mensagem"].tolist())
    assert "Semana deve ser 2026-08-17" in messages
    assert "fora de 0–100" in messages
    assert "inteiro não negativo" in messages
    assert "duplicado" in messages
    assert "Avaliador" in messages


def test_import_payload_can_be_persisted_as_weekly_evaluation(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "avaliacoes_excel.db"))
    db.init_db()
    db.insert_employee(
        name="Ana Expedição",
        sector="Expedição",
        role="Separador",
        is_monitor=False,
        hire_date="01/08/2026",
    )
    employee = db.list_active_employees().iloc[0]
    employee_id = int(employee["id"])
    employees = pd.DataFrame([employee])
    raw = pd.DataFrame([{
        "Importar?": "SIM",
        "employee_id": employee_id,
        "Semana": "2026-08-17",
        "Itens": 55,
        "Assiduidade (%)": 100,
        "Qualidade (%)": 80,
        "Taxa Erros (%)": 80,
        "Prod/Efic (%)": 80,
        "Comportamento (%)": 100,
        "Avaliador": "Líder Um",
        "Notas": "Importada do Excel",
    }])

    preview = prepare_weekly_eval_import(
        raw,
        employees,
        ["Líder Um"],
        "2026-08-17",
        "Revisão pontual",
        default_evaluator="Líder Um",
    )
    db.upsert_weekly_evals(preview["valid_rows"])

    saved = db.get_weekly_eval(employee_id, "2026-08-17").iloc[0]
    assert saved["evaluator"] == "Líder Um"
    assert int(saved["items_count"]) == 55
    assert float(saved["qualidade_pct"]) == 80
    assert "qualidade adequada" in saved["qualidade_just"].lower()
    assert "Importada do Excel" in saved["notes"]
