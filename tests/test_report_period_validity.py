import db
from ui_report import build_month_df


def test_month_report_only_lists_employees_valid_for_period(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "avaliacoes_test.db"))
    db.init_db()
    build_month_df.clear()

    db.insert_employee(
        name="Colaborador Valido",
        sector="Expedição",
        role="Separador",
        is_monitor=False,
        hire_date="01/05/2026",
    )
    db.insert_employee(
        name="Colaborador Futuro",
        sector="Expedição",
        role="Separador",
        is_monitor=False,
        hire_date="29/05/2026",
    )
    db.insert_employee(
        name="Supervisor Futuro",
        sector="Expedição",
        role="Supervisor",
        is_monitor=False,
        hire_date="01/05/2026",
        is_leadership=True,
        leadership_start_date="29/05/2026",
    )
    db.insert_employee(
        name="Colaborador Desligado Antes",
        sector="Expedição",
        role="Separador",
        is_monitor=False,
        hire_date="01/04/2026",
        termination_date="24/04/2026",
    )
    db.insert_employee(
        name="Colaborador Desligado No Mes",
        sector="Expedição",
        role="Separador",
        is_monitor=False,
        hire_date="01/04/2026",
        termination_date="12/05/2026",
    )

    report, _weeks = build_month_df("05/2026")

    assert report["Funcionário"].tolist() == [
        "Colaborador Desligado No Mes",
        "Colaborador Valido",
    ]

    active_report, _weeks = build_month_df("05/2026", include_inactive=False)
    assert active_report["Funcionário"].tolist() == ["Colaborador Valido"]
