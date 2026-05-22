import sqlite3

import pytest

import db


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "avaliacoes_test.db"))
    db.init_db()


def _create_evaluator(name: str = "Yohann Liderança") -> int:
    db.insert_employee(
        name=name,
        sector="Expedição",
        role="Supervisor",
        is_monitor=False,
        hire_date="01/05/2026",
        is_leadership=True,
        leadership_start_date="01/05/2026",
    )
    return int(db.list_active_leadership_evaluators().iloc[0]["id"])


def test_create_login_user_hashes_password(isolated_db):
    user_id = db.create_login_user("Admin", "senha-forte-123")

    assert user_id > 0
    assert db.login_user_count() == 1

    with sqlite3.connect(db.DB_PATH) as con:
        row = con.execute(
            "SELECT username, password_hash, role, active FROM login_users"
        ).fetchone()

    assert row[0] == "admin"
    assert row[1] != "senha-forte-123"
    assert row[1].startswith("pbkdf2_sha256$")
    assert row[2] == "admin"
    assert int(row[3]) == 1


def test_authenticate_login_accepts_valid_password(isolated_db):
    db.create_login_user("admin", "senha-forte-123")

    user = db.authenticate_login("ADMIN", "senha-forte-123")

    assert user is not None
    assert user["username"] == "admin"
    assert user["role"] == "admin"


def test_authenticate_login_rejects_invalid_password(isolated_db):
    db.create_login_user("admin", "senha-forte-123")

    assert db.authenticate_login("admin", "senha-errada") is None


def test_create_login_user_rejects_duplicate_username(isolated_db):
    db.create_login_user("admin", "senha-forte-123")

    with pytest.raises(ValueError, match="já cadastrado"):
        db.create_login_user("ADMIN", "outra-senha-123")


def test_create_login_user_rejects_weak_password(isolated_db):
    with pytest.raises(ValueError, match="letras e números"):
        db.create_login_user("admin", "senhafraca")


def test_create_login_user_rejects_invalid_role(isolated_db):
    with pytest.raises(ValueError, match="Perfil"):
        db.create_login_user("admin", "senha-forte-123", role="superadmin")


def test_create_login_user_links_evaluator(isolated_db):
    evaluator_id = _create_evaluator()

    db.create_login_user(
        "avaliador",
        "senha-forte-123",
        role="avaliador",
        evaluator_employee_id=evaluator_id,
    )

    row = db.list_login_users().iloc[0]
    assert int(row["evaluator_employee_id"]) == evaluator_id
    assert row["evaluator_name"] == "Yohann Liderança"

    user = db.authenticate_login("avaliador", "senha-forte-123")
    assert user["evaluator_employee_id"] == evaluator_id
    assert user["evaluator_name"] == "Yohann Liderança"


def test_create_login_user_requires_active_leadership_evaluator(isolated_db):
    db.insert_employee(
        name="Pessoa Operacional",
        sector="Estoque",
        role="Separador",
        is_monitor=False,
        hire_date="01/05/2026",
    )
    employee_id = int(db.list_employees(include_inactive=True).iloc[0]["id"])

    with pytest.raises(ValueError, match="coordenação/supervisão"):
        db.create_login_user(
            "operacional",
            "senha-forte-123",
            role="avaliador",
            evaluator_employee_id=employee_id,
        )


def test_update_login_user_changes_evaluator_and_password(isolated_db):
    evaluator_id = _create_evaluator()
    user_id = db.create_login_user("lider", "senha-forte-123")

    db.update_login_user(
        user_id=user_id,
        username="lider",
        role="avaliador",
        active=True,
        evaluator_employee_id=evaluator_id,
        password="nova-senha-123",
    )

    assert db.authenticate_login("lider", "senha-forte-123") is None
    user = db.authenticate_login("lider", "nova-senha-123")
    assert user["role"] == "avaliador"
    assert user["evaluator_employee_id"] == evaluator_id
