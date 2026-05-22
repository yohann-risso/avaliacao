import db
from ui_report import build_sector_followup_pdf_bytes, build_sector_followup_tables


def _employee_id(name: str) -> int:
    employees = db.list_employees(include_inactive=True)
    row = employees[employees["name"] == name].iloc[0]
    return int(row["id"])


def _add_weekly_eval(employee_name: str, week_start: str, qualidade=80, taxa_erros=70):
    db.upsert_weekly_eval(
        employee_id=_employee_id(employee_name),
        week_start_iso=week_start,
        evaluator="Yohann",
        notes="",
        assiduidade_pct=100,
        qualidade_pct=qualidade,
        taxa_erros_pct=taxa_erros,
        produtividade_pct=90,
        comportamento_pct=100,
        efficiency_pct=90,
        items_count=50,
        assiduidade_just="ok",
        qualidade_just="ok",
        taxa_erros_just="ok",
        produtividade_just="ok",
        comportamento_just="ok",
    )


def test_sector_followup_filters_sector_and_flags_missing_weeks(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "avaliacoes_test.db"))
    db.init_db()

    db.insert_employee(
        name="Ana Expedição",
        sector="Expedição",
        role="Separador",
        is_monitor=False,
        hire_date="01/04/2026",
    )
    db.insert_employee(
        name="Bruno Estoque",
        sector="Estoque",
        role="Conferente",
        is_monitor=False,
        hire_date="01/04/2026",
    )

    _add_weekly_eval("Ana Expedição", "2026-05-04")

    summary_df, employee_df, weeks_iso = build_sector_followup_tables("05/2026", "Expedição")

    assert weeks_iso == ["2026-04-27", "2026-05-04", "2026-05-11", "2026-05-18"]
    assert employee_df["Funcionário"].tolist() == ["Ana Expedição"]

    row = employee_df.iloc[0]
    assert row["Indicador"] == "Regularizar"
    assert row["Semanas avaliadas/elegíveis"] == "1/4"
    assert row["Cobertura avaliações"] == "25,0%"
    assert int(row["Pendências"]) == 3
    assert row["Assiduidade (%)"] == "100,0%"
    assert row["Qualidade (%)"] == "80,0%"
    assert row["Taxa de Erros (%)"] == "70,0%"

    assert summary_df.iloc[0]["Setor"] == "Expedição"
    assert int(summary_df.iloc[0]["Prioritários"]) == 1

    pdf_bytes = build_sector_followup_pdf_bytes(
        summary_df=summary_df,
        employee_df=employee_df,
        month="2026-05",
        sector_label="Expedição",
        coordinator_name="Yohann",
        report_observation="Feedback mensal do setor.",
    )

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_sector_followup_feedback_uses_criterion_averages(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "avaliacoes_test.db"))
    db.init_db()

    db.insert_employee(
        name="Caio Expedição",
        sector="Expedição",
        role="Separador",
        is_monitor=False,
        hire_date="01/04/2026",
    )

    for week_start in ("2026-04-27", "2026-05-04", "2026-05-11", "2026-05-18"):
        _add_weekly_eval("Caio Expedição", week_start, qualidade=80, taxa_erros=70)

    _summary_df, employee_df, _weeks_iso = build_sector_followup_tables("05/2026", "Expedição")
    row = employee_df.iloc[0]

    assert row["Indicador"] == "Prioritário"
    assert "Taxa de Erros (70,0%)" in row["Foco do feedback"]
    assert "Qualidade (80,0%)" in row["Foco do feedback"]
    assert "Média geral 88,0%" in row["Feedback sugerido"]
