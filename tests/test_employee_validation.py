import pytest

import db


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "avaliacoes_test.db"))
    db.init_db()


def test_employee_requires_hire_date(isolated_db):
    with pytest.raises(ValueError, match="contratação"):
        db.insert_employee(
            name="Pessoa Teste",
            sector="Expedição",
            role="Separador",
            is_monitor=False,
        )


def test_leadership_cannot_be_monitor(isolated_db):
    with pytest.raises(ValueError, match="não pode ser monitor"):
        db.insert_employee(
            name="Pessoa Teste",
            sector="Expedição",
            role="Supervisor",
            is_monitor=True,
            hire_date="01/05/2026",
            is_leadership=True,
            monitor_start_date="01/05/2026",
            leadership_start_date="01/05/2026",
        )


def test_role_dates_are_required_when_flags_are_true(isolated_db):
    with pytest.raises(ValueError, match="início como monitor"):
        db.insert_employee(
            name="Pessoa Monitor",
            sector="Expedição",
            role="Monitor",
            is_monitor=True,
            hire_date="01/05/2026",
        )

    with pytest.raises(ValueError, match="coordenação/supervisão"):
        db.insert_employee(
            name="Pessoa Liderança",
            sector="Expedição",
            role="Supervisor",
            is_monitor=False,
            hire_date="01/05/2026",
            is_leadership=True,
        )


def test_termination_date_deactivates_employee(isolated_db):
    db.insert_employee(
        name="Pessoa Desligada",
        sector="Expedição",
        role="Separador",
        is_monitor=False,
        hire_date="01/05/2026",
        termination_date="02/05/2026",
    )

    employees = db.list_employees(include_inactive=True)
    row = employees.iloc[0]

    assert int(row["active"]) == 0
    assert row["termination_date"] == "2026-05-02"
    assert str(row["deactivated_at"]).strip()
