import sqlite3

import pytest

import db


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "avaliacoes_test.db"))
    db.init_db()


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
