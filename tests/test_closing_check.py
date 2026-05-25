import db
from ui_report import build_closing_check_tables


MAY_2026_WEEKS = ["2026-04-27", "2026-05-04", "2026-05-11", "2026-05-18"]


def _reset_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "avaliacoes_test.db"))
    db.init_db()
    build_closing_check_tables.clear()


def _employee_id(name: str) -> int:
    employees = db.list_employees(include_inactive=True)
    row = employees[employees["name"] == name].iloc[0]
    return int(row["id"])


def test_closing_check_reports_missing_weekly_justifications(tmp_path, monkeypatch):
    _reset_db(tmp_path, monkeypatch)
    db.insert_employee(
        name="Ana Expedição",
        sector="Expedição",
        role="Separador",
        is_monitor=False,
        hire_date="01/04/2026",
    )

    db.upsert_weekly_eval(
        employee_id=_employee_id("Ana Expedição"),
        week_start_iso="2026-04-27",
        evaluator="Yohann",
        notes="",
        assiduidade_pct=100,
        qualidade_pct=100,
        taxa_erros_pct=100,
        produtividade_pct=100,
        comportamento_pct=100,
        efficiency_pct=100,
        items_count=10,
        assiduidade_just="",
        qualidade_just="ok",
        taxa_erros_just="ok",
        produtividade_just="ok",
        comportamento_just="ok",
    )

    checks = build_closing_check_tables("2026-05", MAY_2026_WEEKS, "weekly-justs")

    missing = checks["missing_weekly_justs"]
    assert missing["Funcionário"].tolist() == ["Ana Expedição"]
    assert missing.iloc[0]["Justificativas faltantes"] == "Assiduidade"


def test_closing_check_reports_missing_monitoria_justifications(tmp_path, monkeypatch):
    _reset_db(tmp_path, monkeypatch)
    db.insert_employee(
        name="Bruno Monitor",
        sector="Estoque",
        role="Conferente",
        is_monitor=True,
        monitor_start_date="01/04/2026",
        is_leadership=False,
        hire_date="01/04/2026",
    )

    db.upsert_monitor_monthly_eval(
        employee_id=_employee_id("Bruno Monitor"),
        month="2026-05",
        evaluator="Yohann",
        notes="",
        pcts={
            "acomp_metas": 100,
            "org_fluxo": 100,
            "suporte_equipe": 100,
            "disciplina_oper": 100,
        },
        justs={
            "acomp_metas": "",
            "org_fluxo": "ok",
            "suporte_equipe": "ok",
            "disciplina_oper": "ok",
        },
    )

    checks = build_closing_check_tables("2026-05", MAY_2026_WEEKS, "monitor-justs")

    missing = checks["missing_monitoria_justs"]
    assert missing["Funcionário"].tolist() == ["Bruno Monitor"]
    assert missing.iloc[0]["Justificativas faltantes"] == "Acompanhamento de metas"


def test_closing_check_can_ignore_inactive_employees(tmp_path, monkeypatch):
    _reset_db(tmp_path, monkeypatch)
    db.insert_employee(
        name="Ana Ativa",
        sector="Expedição",
        role="Separador",
        is_monitor=False,
        hire_date="01/04/2026",
    )
    db.insert_employee(
        name="Bruno Desativado",
        sector="Expedição",
        role="Separador",
        is_monitor=False,
        hire_date="01/04/2026",
        termination_date="12/05/2026",
    )

    checks_all = build_closing_check_tables(
        "2026-05",
        MAY_2026_WEEKS,
        "inactive-included",
        include_inactive=True,
    )
    checks_active = build_closing_check_tables(
        "2026-05",
        MAY_2026_WEEKS,
        "inactive-excluded",
        include_inactive=False,
    )

    assert "Bruno Desativado" in checks_all["missing_weekly"]["Funcionário"].tolist()
    assert "Bruno Desativado" not in checks_active["missing_weekly"]["Funcionário"].tolist()
