import pandas as pd

import db
from weekly_error_import import prepare_weekly_error_import


def test_prepare_weekly_error_import_matches_by_partial_name_and_defaults_week():
    employees = pd.DataFrame(
        [
            {
                "id": 10,
                "name": "Ana Expedição",
                "sector": "Expedição",
                "role": "Separador",
            }
        ]
    )
    raw = pd.DataFrame(
        [
            {
                "nome": "ana exped",
                "tipo": "Divergencia de Enderecamento",
                "gravidade": "médio",
                "qtd": "",
                "obs": "Endereco divergente no picking.",
            }
        ]
    )

    preview = prepare_weekly_error_import(raw, employees, default_week_start_iso="2026-06-01")

    assert preview["summary"] == {"total": 1, "valid": 1, "invalid": 0}
    row = preview["valid_rows"][0]
    assert row["employee_id"] == 10
    assert row["week_start_iso"] == "2026-06-01"
    assert row["role_snapshot"] == "Separador"
    assert row["error_type"] == "Divergência de Endereçamento"
    assert row["severity"] == "MEDIO"
    assert row["qty"] == 1

    display = preview["preview_df"].iloc[0]
    assert display["match"] == "nome_parcial"
    assert "week_start vazio" in display["mensagem"]


def test_prepare_weekly_error_import_blocks_ambiguous_name():
    employees = pd.DataFrame(
        [
            {"id": 1, "name": "João Silva", "sector": "A", "role": "Conferente"},
            {"id": 2, "name": "João Souza", "sector": "B", "role": "Separador"},
        ]
    )
    raw = pd.DataFrame(
        [
            {
                "funcionario": "joao",
                "week_start": "2026-06-01",
                "tipo_erro": "Erro de Picking",
                "severity": "ALTO",
                "qty": 1,
            }
        ]
    )

    preview = prepare_weekly_error_import(raw, employees)

    assert preview["summary"]["valid"] == 0
    assert preview["summary"]["invalid"] == 1
    assert preview["preview_df"].iloc[0]["status"] == "REVISAR"
    assert "employee_id" in preview["preview_df"].iloc[0]["mensagem"]


def test_add_weekly_errors_inserts_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "avaliacoes_test.db"))
    db.init_db()
    db.insert_employee(
        name="Bruno Estoque",
        sector="Estoque",
        role="Conferente",
        is_monitor=False,
        hire_date="01/04/2026",
    )
    employee_id = int(db.list_active_employees().iloc[0]["id"])

    imported = db.add_weekly_errors(
        [
            {
                "employee_id": employee_id,
                "week_start_iso": "2026-06-01",
                "role_snapshot": "Conferente",
                "error_type": "Erro de Picking",
                "severity": "ALTO",
                "qty": 2,
                "notes": "Teste importado",
                "created_at": "2026-06-23T10:00:00",
            }
        ]
    )

    assert imported == 1
    errors = db.list_weekly_errors(employee_id, "2026-06-01")
    assert len(errors) == 1
    assert errors.iloc[0]["error_type"] == "Erro de Picking"
    assert errors.iloc[0]["severity"] == "ALTO"
    assert int(errors.iloc[0]["qty"]) == 2
