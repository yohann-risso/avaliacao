# db.py

import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import pandas as pd

APP_DIR = Path(__file__).resolve().parent
DB_PATH = str(APP_DIR / "avaliacoes.db")
PASSWORD_HASH_ITERATIONS = 600_000
VALID_LOGIN_ROLES = {"admin", "avaliador"}
COMMON_PASSWORDS = {
    "12345678",
    "admin123",
    "password",
    "password123",
    "senha123",
    "senha1234",
}
DATABASE_URL_ENV_KEYS = ("APP_DATABASE_URL", "DATABASE_URL", "SUPABASE_DB_URL")
DATABASE_CONFIG_ERROR = (
    "Banco Supabase/PostgreSQL não configurado. Defina APP_DATABASE_URL nos Secrets "
    "do Streamlit Cloud ou no ambiente local. O app não usa mais avaliacoes.db como fallback."
)


def get_database_url() -> str:
    for key in DATABASE_URL_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            return str(value).strip()

    try:
        import streamlit as st

        secrets_obj = st.secrets
    except Exception:
        return ""

    secret_paths = (
        ("APP_DATABASE_URL",),
        ("DATABASE_URL",),
        ("SUPABASE_DB_URL",),
        ("database", "url"),
        ("connections", "supabase", "url"),
        ("connections", "postgres", "url"),
    )
    for path in secret_paths:
        try:
            current = secrets_obj
            for key in path:
                current = current[key]
            if current:
                return str(current).strip()
        except Exception:
            continue

    return ""


def is_postgres_backend() -> bool:
    url = get_database_url().lower()
    return url.startswith(("postgres://", "postgresql://"))


def is_sqlite_test_backend() -> bool:
    return os.environ.get("AVALIACAO_ALLOW_SQLITE", "").strip() == "1"


def require_postgres_database_url() -> str:
    url = get_database_url()
    if not url:
        raise RuntimeError(DATABASE_CONFIG_ERROR)
    if not url.lower().startswith(("postgres://", "postgresql://")):
        raise RuntimeError("APP_DATABASE_URL deve ser uma connection string PostgreSQL/Supabase.")
    return url


def _database_url_with_ssl(url: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("sslmode", "require")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _connect_postgres():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "Para usar Supabase/PostgreSQL, instale as dependências com "
            "`python -m pip install -r requirements.txt`."
        ) from exc

    return psycopg.connect(
        _database_url_with_ssl(require_postgres_database_url()),
        connect_timeout=15,
        prepare_threshold=None,
    )


def _prepare_query(query: str) -> str:
    if not is_sqlite_test_backend():
        return str(query).replace("?", "%s")
    return str(query)


class CompatConnection:
    def __init__(self, con):
        self._con = con

    def execute(self, query: str, params: tuple | list = ()):
        return self._con.execute(_prepare_query(query), params or ())

    def executemany(self, query: str, params_seq):
        query = _prepare_query(query)
        if hasattr(self._con, "executemany"):
            return self._con.executemany(query, params_seq)
        with self._con.cursor() as cur:
            cur.executemany(query, params_seq)
            return cur

    def commit(self):
        return self._con.commit()

    def rollback(self):
        return self._con.rollback()

    def close(self):
        return self._con.close()


def _column_name(description) -> str:
    return str(getattr(description, "name", None) or description[0])


def _read_sql_query(con: CompatConnection, query: str, params: tuple = ()) -> pd.DataFrame:
    cur = con.execute(query, params)
    if not cur.description:
        return pd.DataFrame()
    columns = [_column_name(desc) for desc in cur.description]
    return pd.DataFrame(cur.fetchall(), columns=columns)


def sql_clean_text_expr(expr: str) -> str:
    newline_fn = "char" if is_sqlite_test_backend() else "CHR"
    return f"REPLACE(REPLACE(TRIM({expr}), {newline_fn}(13), ''), {newline_fn}(10), '')"


def sql_group_concat(expr: str, separator: str = ", ") -> str:
    safe_separator = separator.replace("'", "''")
    if is_sqlite_test_backend():
        return f"GROUP_CONCAT({expr}, '{safe_separator}')"
    return f"STRING_AGG(({expr})::text, '{safe_separator}')"


def sql_quote(expr: str) -> str:
    if is_sqlite_test_backend():
        return f"quote({expr})"
    return f"QUOTE_LITERAL({expr})"


def normalize_week_start_iso(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    cleaned = str(value or "").replace("\r", "").replace("\n", "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError("Data inválida. Use DD/MM/AAAA.")


def normalize_month_label(value) -> str:
    cleaned = str(value or "").replace("\r", "").replace("\n", "").strip()
    for fmt in ("%m/%Y", "%Y-%m"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m")
        except ValueError:
            pass
    raise ValueError("Mês inválido. Use MM/AAAA.")


def normalize_hire_date_iso(value) -> str:
    return normalize_date_iso(value, "Data de contratação inválida. Use DD/MM/AAAA.")


def normalize_role_start_date_iso(value, label: str) -> str:
    return normalize_date_iso(value, f"{label} inválida. Use DD/MM/AAAA.")


def normalize_termination_date_iso(value) -> str:
    return normalize_date_iso(value, "Data de desligamento inválida. Use DD/MM/AAAA.")


def normalize_date_iso(value, error_message: str) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    cleaned = str(value or "").replace("\r", "").replace("\n", "").strip()
    if not cleaned:
        return ""

    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            pass

    raise ValueError(error_message)


def active_from_termination_date(termination_date: str) -> int:
    if not str(termination_date or "").strip():
        return 1
    try:
        term_date = datetime.strptime(str(termination_date).strip(), "%Y-%m-%d").date()
    except Exception:
        return 1
    return 0 if term_date <= date.today() else 1


def sync_employee_active_status(con):
    now = datetime.now().isoformat(timespec="seconds")
    today = date.today().isoformat()
    con.execute(
        """
        UPDATE employees
        SET active = 0,
            deactivated_at = CASE
                WHEN COALESCE(deactivated_at, '') = '' THEN ?
                ELSE deactivated_at
            END
        WHERE COALESCE(termination_date, '') <> ''
          AND termination_date <= ?
          AND active <> 0
        """,
        (now, today),
    )
    con.execute(
        """
        UPDATE employees
        SET active = 1,
            deactivated_at = ''
        WHERE COALESCE(termination_date, '') <> ''
          AND termination_date > ?
          AND active <> 1
        """,
        (today,),
    )


def refresh_employee_active_statuses():
    with db() as con:
        sync_employee_active_status(con)


@contextmanager
def db():
    if is_sqlite_test_backend():
        raw_con = sqlite3.connect(DB_PATH, timeout=30)
        raw_con.execute("PRAGMA foreign_keys = ON;")
        raw_con.execute("PRAGMA busy_timeout = 10000;")
    else:
        require_postgres_database_url()
        raw_con = _connect_postgres()

    con = CompatConnection(raw_con)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def fetch_df(query: str, params: tuple = ()) -> pd.DataFrame:
    with db() as con:
        return _read_sql_query(con, query, params=params)

def exec_sql(query: str, params: tuple = ()):
    with db() as con:
        con.execute(query, params)

def ensure_column(con, table: str, col: str, coldef: str):
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {coldef};")


def init_postgres_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS login_users (
            id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            evaluator_employee_id INTEGER,
            active INTEGER NOT NULL DEFAULT 1,
            last_login_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        );
        """)
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_login_users_username_lower ON login_users (LOWER(username));")
        con.execute("CREATE INDEX IF NOT EXISTS idx_login_users_active ON login_users(active, username);")

        con.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL,
            sector TEXT NOT NULL,
            role TEXT NOT NULL,
            hire_date TEXT NOT NULL DEFAULT '',
            monitor_start_date TEXT NOT NULL DEFAULT '',
            leadership_start_date TEXT NOT NULL DEFAULT '',
            termination_date TEXT NOT NULL DEFAULT '',
            picking_operator_name TEXT NOT NULL DEFAULT '',
            bybox_operator_name TEXT NOT NULL DEFAULT '',
            is_monitor INTEGER NOT NULL DEFAULT 0,
            is_leadership INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            deactivated_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            created_by_user_id INTEGER,
            created_by_username TEXT NOT NULL DEFAULT '',
            updated_by_user_id INTEGER,
            updated_by_username TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );
        """)
        con.execute("ALTER TABLE login_users ADD COLUMN IF NOT EXISTS evaluator_employee_id INTEGER;")
        con.execute("CREATE INDEX IF NOT EXISTS idx_login_users_evaluator_employee ON login_users(evaluator_employee_id);")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS hire_date TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS monitor_start_date TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS leadership_start_date TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS termination_date TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS picking_operator_name TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS bybox_operator_name TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS is_leadership INTEGER NOT NULL DEFAULT 0;")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS deactivated_at TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER;")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS created_by_username TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS updated_by_user_id INTEGER;")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS updated_by_username TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS updated_at TEXT NOT NULL DEFAULT '';")

        con.execute("""
        CREATE TABLE IF NOT EXISTS weekly_evaluations (
            id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
            week_start TEXT NOT NULL,
            evaluator TEXT,
            notes TEXT,
            assiduidade_pct REAL NOT NULL DEFAULT 100,
            qualidade_pct REAL NOT NULL DEFAULT 100,
            taxa_erros_pct REAL NOT NULL DEFAULT 100,
            produtividade_pct REAL NOT NULL DEFAULT 100,
            comportamento_pct REAL NOT NULL DEFAULT 100,
            efficiency_pct REAL NOT NULL DEFAULT 100,
            items_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            assiduidade_just TEXT NOT NULL DEFAULT '',
            qualidade_just TEXT NOT NULL DEFAULT '',
            taxa_erros_just TEXT NOT NULL DEFAULT '',
            produtividade_just TEXT NOT NULL DEFAULT '',
            comportamento_just TEXT NOT NULL DEFAULT '',
            UNIQUE(employee_id, week_start)
        );
        """)
        con.execute("ALTER TABLE weekly_evaluations ADD COLUMN IF NOT EXISTS efficiency_pct REAL NOT NULL DEFAULT 100;")
        con.execute("ALTER TABLE weekly_evaluations ADD COLUMN IF NOT EXISTS items_count INTEGER NOT NULL DEFAULT 0;")
        con.execute("ALTER TABLE weekly_evaluations ADD COLUMN IF NOT EXISTS assiduidade_just TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE weekly_evaluations ADD COLUMN IF NOT EXISTS qualidade_just TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE weekly_evaluations ADD COLUMN IF NOT EXISTS taxa_erros_just TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE weekly_evaluations ADD COLUMN IF NOT EXISTS produtividade_just TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE weekly_evaluations ADD COLUMN IF NOT EXISTS comportamento_just TEXT NOT NULL DEFAULT '';")

        con.execute("""
        CREATE TABLE IF NOT EXISTS monitor_monthly_evaluations (
            id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
            month TEXT NOT NULL,
            evaluator TEXT,
            notes TEXT,
            acomp_metas_pct REAL NOT NULL DEFAULT 100,
            org_fluxo_pct REAL NOT NULL DEFAULT 100,
            suporte_equipe_pct REAL NOT NULL DEFAULT 100,
            disciplina_oper_pct REAL NOT NULL DEFAULT 100,
            created_at TEXT NOT NULL,
            acomp_metas_just TEXT NOT NULL DEFAULT '',
            org_fluxo_just TEXT NOT NULL DEFAULT '',
            suporte_equipe_just TEXT NOT NULL DEFAULT '',
            disciplina_oper_just TEXT NOT NULL DEFAULT '',
            UNIQUE(employee_id, month)
        );
        """)
        con.execute("ALTER TABLE monitor_monthly_evaluations ADD COLUMN IF NOT EXISTS acomp_metas_just TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE monitor_monthly_evaluations ADD COLUMN IF NOT EXISTS org_fluxo_just TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE monitor_monthly_evaluations ADD COLUMN IF NOT EXISTS suporte_equipe_just TEXT NOT NULL DEFAULT '';")
        con.execute("ALTER TABLE monitor_monthly_evaluations ADD COLUMN IF NOT EXISTS disciplina_oper_just TEXT NOT NULL DEFAULT '';")

        con.execute("""
        CREATE TABLE IF NOT EXISTS weekly_errors (
            id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
            week_start TEXT NOT NULL,
            role_snapshot TEXT NOT NULL,
            error_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            qty INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            created_at TEXT NOT NULL
        );
        """)

        con.execute("""
            UPDATE employees
            SET termination_date = substring(deactivated_at from 1 for 10)
            WHERE active = 0
              AND COALESCE(termination_date, '') = ''
              AND COALESCE(deactivated_at, '') <> ''
        """)
        con.execute("""
            UPDATE employees
            SET is_monitor = 0,
                monitor_start_date = ''
            WHERE COALESCE(is_leadership, 0) = 1
              AND COALESCE(is_monitor, 0) = 1
        """)
        sync_employee_active_status(con)

        con.execute("CREATE INDEX IF NOT EXISTS idx_employees_active_role ON employees(active, is_leadership, sector, role, name);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_weekly_eval_employee_week ON weekly_evaluations(employee_id, week_start);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_weekly_eval_employee_week_desc ON weekly_evaluations(employee_id, week_start DESC);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_weekly_errors_employee_week ON weekly_errors(employee_id, week_start);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_monitor_eval_employee_month ON monitor_monthly_evaluations(employee_id, month);")

        for table in (
            "login_users",
            "employees",
            "weekly_evaluations",
            "weekly_errors",
            "monitor_monthly_evaluations",
        ):
            con.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        con.execute("""
        -- Supabase has these API roles, but plain PostgreSQL deployments may not.
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                EXECUTE '
                    REVOKE ALL ON TABLE
                        login_users,
                        employees,
                        weekly_evaluations,
                        weekly_errors,
                        monitor_monthly_evaluations
                    FROM anon
                ';
            END IF;

            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                EXECUTE '
                    REVOKE ALL ON TABLE
                        login_users,
                        employees,
                        weekly_evaluations,
                        weekly_errors,
                        monitor_monthly_evaluations
                    FROM authenticated
                ';
            END IF;
        END $$;
        """)


def init_db():
    if not is_sqlite_test_backend():
        try:
            require_postgres_database_url()
            init_postgres_db()
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                "Falha ao conectar ou preparar o banco PostgreSQL/Supabase. "
                "Confira APP_DATABASE_URL nos Secrets, senha, host, porta e sslmode=require. "
                f"Detalhe técnico: {exc}"
            ) from exc
        return

    with db() as con:
        con.execute("PRAGMA journal_mode = WAL;")
        con.execute("PRAGMA synchronous = NORMAL;")

        con.execute("""
        CREATE TABLE IF NOT EXISTS login_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            evaluator_employee_id INTEGER,
            active INTEGER NOT NULL DEFAULT 1,
            last_login_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        );
        """)
        ensure_column(con, "login_users", "evaluator_employee_id", "evaluator_employee_id INTEGER")
        con.execute("CREATE INDEX IF NOT EXISTS idx_login_users_active ON login_users(active, username);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_login_users_evaluator_employee ON login_users(evaluator_employee_id);")

        con.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sector TEXT NOT NULL,
            role TEXT NOT NULL,
            hire_date TEXT NOT NULL DEFAULT '',
            monitor_start_date TEXT NOT NULL DEFAULT '',
            leadership_start_date TEXT NOT NULL DEFAULT '',
            termination_date TEXT NOT NULL DEFAULT '',
            picking_operator_name TEXT NOT NULL DEFAULT '',
            bybox_operator_name TEXT NOT NULL DEFAULT '',
            is_monitor INTEGER NOT NULL DEFAULT 0,
            is_leadership INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            deactivated_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        """)

        ensure_column(con, "employees", "hire_date", "hire_date TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "employees", "monitor_start_date", "monitor_start_date TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "employees", "leadership_start_date", "leadership_start_date TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "employees", "termination_date", "termination_date TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "employees", "picking_operator_name", "picking_operator_name TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "employees", "bybox_operator_name", "bybox_operator_name TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "employees", "is_leadership", "is_leadership INTEGER NOT NULL DEFAULT 0")
        ensure_column(con, "employees", "deactivated_at", "deactivated_at TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "employees", "created_by_user_id", "created_by_user_id INTEGER")
        ensure_column(con, "employees", "created_by_username", "created_by_username TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "employees", "updated_by_user_id", "updated_by_user_id INTEGER")
        ensure_column(con, "employees", "updated_by_username", "updated_by_username TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "employees", "updated_at", "updated_at TEXT NOT NULL DEFAULT ''")
        con.execute("""
            UPDATE employees
            SET termination_date = substr(deactivated_at, 1, 10)
            WHERE active = 0
              AND COALESCE(termination_date, '') = ''
              AND COALESCE(deactivated_at, '') <> ''
        """)
        con.execute("""
            UPDATE employees
            SET is_monitor = 0,
                monitor_start_date = ''
            WHERE COALESCE(is_leadership, 0) = 1
              AND COALESCE(is_monitor, 0) = 1
        """)
        sync_employee_active_status(con)

        con.execute("""
        CREATE TABLE IF NOT EXISTS weekly_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            week_start TEXT NOT NULL,            -- YYYY-MM-DD (segunda)
            evaluator TEXT,
            notes TEXT,

            assiduidade_pct REAL NOT NULL DEFAULT 100,
            qualidade_pct REAL NOT NULL DEFAULT 100,
            taxa_erros_pct REAL NOT NULL DEFAULT 100,   -- taxa final (0-100), pode ser manual
            produtividade_pct REAL NOT NULL DEFAULT 100,
            comportamento_pct REAL NOT NULL DEFAULT 100,

            efficiency_pct REAL NOT NULL DEFAULT 100,   -- eficiência (0-100)
            items_count INTEGER NOT NULL DEFAULT 0,     -- itens/peças no período (opcional)
            created_at TEXT NOT NULL,

            UNIQUE(employee_id, week_start),
            FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        """)

        # Migrações (caso já exista DB antigo)
        ensure_column(con, "weekly_evaluations", "efficiency_pct", "efficiency_pct REAL NOT NULL DEFAULT 100")
        ensure_column(con, "weekly_evaluations", "items_count", "items_count INTEGER NOT NULL DEFAULT 0")
        
        # Justificativas semanais (obrigatórias na UI)
        ensure_column(con, "weekly_evaluations", "assiduidade_just", "assiduidade_just TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "weekly_evaluations", "qualidade_just", "qualidade_just TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "weekly_evaluations", "taxa_erros_just", "taxa_erros_just TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "weekly_evaluations", "produtividade_just", "produtividade_just TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "weekly_evaluations", "comportamento_just", "comportamento_just TEXT NOT NULL DEFAULT ''")


        con.execute("""
        CREATE TABLE IF NOT EXISTS monitor_monthly_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            month TEXT NOT NULL,                 -- YYYY-MM
            evaluator TEXT,
            notes TEXT,

            acomp_metas_pct REAL NOT NULL DEFAULT 100,
            org_fluxo_pct REAL NOT NULL DEFAULT 100,
            suporte_equipe_pct REAL NOT NULL DEFAULT 100,
            disciplina_oper_pct REAL NOT NULL DEFAULT 100,

            created_at TEXT NOT NULL,

            UNIQUE(employee_id, month),
            FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        """)
        
        # Justificativas monitoria (mensal)
        ensure_column(con, "monitor_monthly_evaluations", "acomp_metas_just", "acomp_metas_just TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "monitor_monthly_evaluations", "org_fluxo_just", "org_fluxo_just TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "monitor_monthly_evaluations", "suporte_equipe_just", "suporte_equipe_just TEXT NOT NULL DEFAULT ''")
        ensure_column(con, "monitor_monthly_evaluations", "disciplina_oper_just", "disciplina_oper_just TEXT NOT NULL DEFAULT ''")

        # Log detalhado de erros por semana
        con.execute("""
        CREATE TABLE IF NOT EXISTS weekly_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            week_start TEXT NOT NULL,             -- YYYY-MM-DD (segunda)
            role_snapshot TEXT NOT NULL,          -- guarda função da época
            error_type TEXT NOT NULL,             -- ex: "Pedido enviado errado"
            severity TEXT NOT NULL,               -- BAIXO|MEDIO|ALTO|CRITICO
            qty INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        """)

        con.execute("CREATE INDEX IF NOT EXISTS idx_employees_active_role ON employees(active, is_leadership, sector, role, name);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_weekly_eval_employee_week ON weekly_evaluations(employee_id, week_start);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_weekly_eval_employee_week_desc ON weekly_evaluations(employee_id, week_start DESC);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_weekly_errors_employee_week ON weekly_errors(employee_id, week_start);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_monitor_eval_employee_month ON monitor_monthly_evaluations(employee_id, month);")

# ----------------------
# Login users
# ----------------------
def normalize_username(username: str) -> str:
    cleaned = str(username or "").replace("\r", "").replace("\n", "").strip().lower()
    if not cleaned:
        raise ValueError("Informe o usuário.")
    if len(cleaned) < 3:
        raise ValueError("O usuário deve ter pelo menos 3 caracteres.")
    return cleaned


def normalize_login_role(role: str) -> str:
    cleaned = str(role or "admin").strip().lower() or "admin"
    if cleaned not in VALID_LOGIN_ROLES:
        raise ValueError("Perfil de usuário inválido.")
    return cleaned


def validate_password_strength(password: str) -> str:
    password = str(password or "")
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    if password.strip().lower() in COMMON_PASSWORDS:
        raise ValueError("Use uma senha menos previsível.")
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        raise ValueError("A senha deve combinar letras e números.")
    return password


def hash_password(password: str) -> str:
    password = validate_password_strength(password)

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = str(stored_hash or "").split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            str(password or "").encode("utf-8"),
            salt,
            int(iterations),
        )
        return hmac.compare_digest(candidate, expected)
    except Exception:
        return False


def login_user_count() -> int:
    with db() as con:
        row = con.execute("SELECT COUNT(*) FROM login_users").fetchone()
    return int(row[0] or 0)


def _normalize_evaluator_employee_id(con, evaluator_employee_id) -> int | None:
    if evaluator_employee_id in (None, "", 0, "0"):
        return None

    try:
        employee_id = int(evaluator_employee_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Selecione um avaliador válido.") from exc

    row = con.execute(
        """
        SELECT id
        FROM employees
        WHERE id = ?
          AND active = 1
          AND COALESCE(is_leadership, 0) = 1
        LIMIT 1
        """,
        (employee_id,),
    ).fetchone()
    if not row:
        raise ValueError("Selecione um funcionário ativo de coordenação/supervisão como avaliador.")

    return int(row[0])


def list_login_users() -> pd.DataFrame:
    return fetch_df("""
        SELECT
            u.id,
            u.username,
            u.role,
            u.active,
            u.evaluator_employee_id,
            COALESCE(e.name, '') AS evaluator_name,
            COALESCE(e.sector, '') AS evaluator_sector,
            COALESCE(e.role, '') AS evaluator_role,
            COALESCE(e.active, 0) AS evaluator_active,
            COALESCE(e.is_leadership, 0) AS evaluator_is_leadership,
            u.last_login_at,
            u.created_at,
            u.updated_at
        FROM login_users u
        LEFT JOIN employees e ON e.id = u.evaluator_employee_id
        ORDER BY u.active DESC, LOWER(u.username)
    """)


def create_login_user(
    username: str,
    password: str,
    role: str = "admin",
    active: bool = True,
    evaluator_employee_id: int | None = None,
) -> int:
    username = normalize_username(username)
    password_hash = hash_password(password)
    role = normalize_login_role(role)
    now = datetime.now().isoformat(timespec="seconds")

    try:
        with db() as con:
            evaluator_employee_id = _normalize_evaluator_employee_id(con, evaluator_employee_id)
            params = (username, password_hash, role, evaluator_employee_id, 1 if active else 0, now, now)
            if is_postgres_backend():
                cur = con.execute(
                    """
                    INSERT INTO login_users (
                        username, password_hash, role, evaluator_employee_id, active, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    RETURNING id
                    """,
                    params,
                )
                return int(cur.fetchone()[0])

            cur = con.execute(
                """
                INSERT INTO login_users (
                    username, password_hash, role, evaluator_employee_id, active, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                params,
            )
            return int(cur.lastrowid)
    except Exception as exc:
        if isinstance(exc, sqlite3.IntegrityError) or getattr(exc, "sqlstate", "") == "23505":
            raise ValueError("Usuário de login já cadastrado.") from exc
        raise


def update_login_user(
    user_id: int,
    username: str,
    role: str,
    active: bool,
    evaluator_employee_id: int | None = None,
    password: str = "",
) -> None:
    username = normalize_username(username)
    role = normalize_login_role(role)
    now = datetime.now().isoformat(timespec="seconds")

    try:
        with db() as con:
            evaluator_employee_id = _normalize_evaluator_employee_id(con, evaluator_employee_id)
            password = str(password or "")
            if password:
                con.execute(
                    """
                    UPDATE login_users
                    SET username = ?,
                        password_hash = ?,
                        role = ?,
                        evaluator_employee_id = ?,
                        active = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        username,
                        hash_password(password),
                        role,
                        evaluator_employee_id,
                        1 if active else 0,
                        now,
                        int(user_id),
                    ),
                )
                return

            con.execute(
                """
                UPDATE login_users
                SET username = ?,
                    role = ?,
                    evaluator_employee_id = ?,
                    active = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    username,
                    role,
                    evaluator_employee_id,
                    1 if active else 0,
                    now,
                    int(user_id),
                ),
            )
    except Exception as exc:
        if isinstance(exc, sqlite3.IntegrityError) or getattr(exc, "sqlstate", "") == "23505":
            raise ValueError("Usuário de login já cadastrado.") from exc
        raise


def authenticate_login(username: str, password: str) -> dict | None:
    username = normalize_username(username)
    with db() as con:
        row = con.execute(
            """
            SELECT
                u.id,
                u.username,
                u.password_hash,
                u.role,
                u.active,
                u.evaluator_employee_id,
                COALESCE(e.name, '') AS evaluator_name
            FROM login_users u
            LEFT JOIN employees e ON e.id = u.evaluator_employee_id
            WHERE u.username = ?
            LIMIT 1
            """,
            (username,),
        ).fetchone()

        if not row:
            return None

        user_id, stored_username, stored_hash, role, active, evaluator_employee_id, evaluator_name = row
        if int(active or 0) != 1 or not verify_password(password, stored_hash):
            return None

        con.execute(
            "UPDATE login_users SET last_login_at = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), int(user_id)),
        )

    return {
        "id": int(user_id),
        "username": str(stored_username),
        "role": str(role or "admin"),
        "evaluator_employee_id": int(evaluator_employee_id) if evaluator_employee_id else None,
        "evaluator_name": str(evaluator_name or ""),
    }


# ----------------------
# Employees
# ----------------------
def _normalize_employee_role_dates(
    is_monitor: bool,
    is_leadership: bool,
    monitor_start_date: str = "",
    leadership_start_date: str = "",
) -> tuple[int, int, str, str]:
    if is_monitor and is_leadership:
        raise ValueError("Coordenação/supervisão não pode ser monitor.")

    is_leadership_value = 1 if is_leadership else 0
    is_monitor_value = 1 if is_monitor else 0

    monitor_start_date = normalize_role_start_date_iso(monitor_start_date, "Data de início como monitor")
    leadership_start_date = normalize_role_start_date_iso(leadership_start_date, "Data de início em coordenação/supervisão")

    if is_monitor_value and not monitor_start_date:
        raise ValueError("Preencha a data de início como monitor.")
    if is_leadership_value and not leadership_start_date:
        raise ValueError("Preencha a data de início em coordenação/supervisão.")

    if not is_monitor_value:
        monitor_start_date = ""
    if not is_leadership_value:
        leadership_start_date = ""

    return is_monitor_value, is_leadership_value, monitor_start_date, leadership_start_date


def insert_employee(
    name: str,
    sector: str,
    role: str,
    is_monitor: bool,
    hire_date: str = "",
    is_leadership: bool = False,
    monitor_start_date: str = "",
    leadership_start_date: str = "",
    termination_date: str = "",
    picking_operator_name: str = "",
    bybox_operator_name: str = "",
    created_by_user_id: int | None = None,
    created_by_username: str = "",
):
    hire_date = normalize_hire_date_iso(hire_date)
    if not hire_date:
        raise ValueError("Preencha a data de contratação.")
    termination_date = normalize_termination_date_iso(termination_date)
    active_value = active_from_termination_date(termination_date)
    deactivated_at = datetime.now().isoformat(timespec="seconds") if active_value == 0 else ""
    is_monitor_value, is_leadership_value, monitor_start_date, leadership_start_date = _normalize_employee_role_dates(
        is_monitor=is_monitor,
        is_leadership=is_leadership,
        monitor_start_date=monitor_start_date,
        leadership_start_date=leadership_start_date,
    )
    exec_sql(
        """
        INSERT INTO employees (
            name, sector, role, hire_date, monitor_start_date, leadership_start_date, termination_date,
            picking_operator_name, bybox_operator_name,
            is_monitor, is_leadership, active, deactivated_at, created_at,
            created_by_user_id, created_by_username, updated_by_user_id, updated_by_username, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name.strip(),
            sector.strip(),
            role.strip(),
            hire_date,
            monitor_start_date,
            leadership_start_date,
            termination_date,
            str(picking_operator_name or "").strip(),
            str(bybox_operator_name or "").strip(),
            is_monitor_value,
            is_leadership_value,
            active_value,
            deactivated_at,
            datetime.now().isoformat(timespec="seconds"),
            created_by_user_id,
            str(created_by_username or "").strip(),
            created_by_user_id,
            str(created_by_username or "").strip(),
            datetime.now().isoformat(timespec="seconds"),
        )
    )

def deactivate_employee(employee_id: int, updated_by_user_id: int | None = None, updated_by_username: str = ""):
    today = date.today().isoformat()
    exec_sql(
        """
        UPDATE employees
        SET active=0,
            termination_date=?,
            deactivated_at=?,
            updated_by_user_id=?,
            updated_by_username=?,
            updated_at=?
        WHERE id=?
        """,
        (
            today,
            datetime.now().isoformat(timespec="seconds"),
            updated_by_user_id,
            str(updated_by_username or "").strip(),
            datetime.now().isoformat(timespec="seconds"),
            int(employee_id),
        ),
    )


def reactivate_employee(employee_id: int, updated_by_user_id: int | None = None, updated_by_username: str = ""):
    exec_sql(
        """
        UPDATE employees
        SET active=1,
            termination_date='',
            deactivated_at='',
            updated_by_user_id=?,
            updated_by_username=?,
            updated_at=?
        WHERE id=?
        """,
        (
            updated_by_user_id,
            str(updated_by_username or "").strip(),
            datetime.now().isoformat(timespec="seconds"),
            int(employee_id),
        ),
    )


def list_employees(include_inactive: bool = True):
    if include_inactive:
        return fetch_df("""
            SELECT
                id, name, sector, role, hire_date, monitor_start_date, leadership_start_date, termination_date,
                picking_operator_name, bybox_operator_name,
                is_monitor, is_leadership, active, deactivated_at,
                created_by_user_id, created_by_username, updated_by_user_id, updated_by_username, updated_at
            FROM employees
            ORDER BY active DESC, sector, role, name
        """)

    return list_active_employees()

def list_active_employees():
    return fetch_df("""
        SELECT
            id, name, sector, role, hire_date, monitor_start_date, leadership_start_date, termination_date,
            picking_operator_name, bybox_operator_name,
            is_monitor, is_leadership, active, deactivated_at,
            created_by_user_id, created_by_username, updated_by_user_id, updated_by_username, updated_at
        FROM employees
        WHERE active=1
        ORDER BY sector, role, name
    """)


def list_active_leadership_evaluators():
    return fetch_df("""
        SELECT id, name, sector, role
        FROM employees
        WHERE active = 1
          AND COALESCE(is_leadership, 0) = 1
        ORDER BY name
    """)

# ----------------------
# Weekly Eval
# ----------------------
def get_weekly_eval(employee_id: int, week_start_iso: str) -> pd.DataFrame:
    week_start_iso = normalize_week_start_iso(week_start_iso)
    return fetch_df(
        "SELECT * FROM weekly_evaluations WHERE employee_id=? AND week_start=?",
        (employee_id, week_start_iso)
    )

def get_last_weekly_eval(employee_id: int, before_week_start_iso: str | None = None) -> pd.DataFrame:
    if before_week_start_iso:
        before_week_start_iso = normalize_week_start_iso(before_week_start_iso)
        return fetch_df(
            """
            SELECT *
            FROM weekly_evaluations
            WHERE employee_id = ?
              AND week_start < ?
            ORDER BY week_start DESC
            LIMIT 1
            """,
            (employee_id, before_week_start_iso),
        )

    return fetch_df(
        """
        SELECT *
        FROM weekly_evaluations
        WHERE employee_id = ?
        ORDER BY week_start DESC
        LIMIT 1
        """,
        (employee_id,),
    )


def list_weekly_eval_basis(employee_ids: list[int], week_start_iso: str) -> pd.DataFrame:
    ids = [int(employee_id) for employee_id in employee_ids if employee_id is not None]
    if not ids:
        return pd.DataFrame()

    week_start_iso = normalize_week_start_iso(week_start_iso)
    placeholders = ",".join("?" for _ in ids)

    with db() as con:
        current = _read_sql_query(
            con,
            f"""
            SELECT w.*, 'current' AS basis_source
            FROM weekly_evaluations w
            WHERE w.week_start = ?
              AND w.employee_id IN ({placeholders})
            """,
            params=(week_start_iso, *ids),
        )

        previous = _read_sql_query(
            con,
            f"""
            SELECT ranked.*, 'previous' AS basis_source
            FROM (
                SELECT
                    w.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY w.employee_id
                        ORDER BY w.week_start DESC, w.id DESC
                    ) AS rn
                FROM weekly_evaluations w
                WHERE w.week_start < ?
                  AND w.employee_id IN ({placeholders})
            ) ranked
            WHERE ranked.rn = 1
            """,
            params=(week_start_iso, *ids),
        )

    if "rn" in previous.columns:
        previous = previous.drop(columns=["rn"])

    if not current.empty:
        current_ids = set(current["employee_id"].astype(int).tolist())
        previous = previous[~previous["employee_id"].astype(int).isin(current_ids)]

    frames = [frame for frame in (current, previous) if not frame.empty]
    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


WEEKLY_EVAL_UPSERT_SQL = """
INSERT INTO weekly_evaluations (
    employee_id, week_start, evaluator, notes,
    assiduidade_pct, qualidade_pct, taxa_erros_pct, produtividade_pct, comportamento_pct,
    efficiency_pct, items_count,
    assiduidade_just, qualidade_just, taxa_erros_just, produtividade_just, comportamento_just,
    created_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(employee_id, week_start) DO UPDATE SET
    evaluator=excluded.evaluator,
    notes=excluded.notes,

    assiduidade_pct=excluded.assiduidade_pct,
    qualidade_pct=excluded.qualidade_pct,
    taxa_erros_pct=excluded.taxa_erros_pct,
    produtividade_pct=excluded.produtividade_pct,
    comportamento_pct=excluded.comportamento_pct,

    efficiency_pct=excluded.efficiency_pct,
    items_count=excluded.items_count,

    assiduidade_just=excluded.assiduidade_just,
    qualidade_just=excluded.qualidade_just,
    taxa_erros_just=excluded.taxa_erros_just,
    produtividade_just=excluded.produtividade_just,
    comportamento_just=excluded.comportamento_just
;
"""


def upsert_weekly_evals(rows: list[dict]):
    if not rows:
        return

    now = datetime.now().isoformat(timespec="seconds")
    params = []

    for row in rows:
        week_start_iso = normalize_week_start_iso(row.get("week_start_iso"))
        params.append((
            int(row.get("employee_id")),
            str(week_start_iso),
            str(row.get("evaluator", "")).strip(),
            str(row.get("notes", "")).strip(),

            float(row.get("assiduidade_pct", 100)),
            float(row.get("qualidade_pct", 100)),
            float(row.get("taxa_erros_pct", 100)),
            float(row.get("produtividade_pct", 100)),
            float(row.get("comportamento_pct", 100)),

            float(row.get("efficiency_pct", row.get("produtividade_pct", 100))),
            int(row.get("items_count", 0)),

            str(row.get("assiduidade_just", "")).strip(),
            str(row.get("qualidade_just", "")).strip(),
            str(row.get("taxa_erros_just", "")).strip(),
            str(row.get("produtividade_just", "")).strip(),
            str(row.get("comportamento_just", "")).strip(),

            now,
        ))

    with db() as con:
        con.executemany(WEEKLY_EVAL_UPSERT_SQL, params)


def upsert_weekly_eval(
    employee_id: int,
    week_start_iso: str,
    evaluator: str,
    notes: str,
    assiduidade_pct: float,
    qualidade_pct: float,
    taxa_erros_pct: float,
    produtividade_pct: float,
    comportamento_pct: float,
    efficiency_pct: float,
    items_count: int,
    assiduidade_just: str,
    qualidade_just: str,
    taxa_erros_just: str,
    produtividade_just: str,
    comportamento_just: str,
):
    upsert_weekly_evals([{
        "employee_id": employee_id,
        "week_start_iso": week_start_iso,
        "evaluator": evaluator,
        "notes": notes,
        "assiduidade_pct": assiduidade_pct,
        "qualidade_pct": qualidade_pct,
        "taxa_erros_pct": taxa_erros_pct,
        "produtividade_pct": produtividade_pct,
        "comportamento_pct": comportamento_pct,
        "efficiency_pct": efficiency_pct,
        "items_count": items_count,
        "assiduidade_just": assiduidade_just,
        "qualidade_just": qualidade_just,
        "taxa_erros_just": taxa_erros_just,
        "produtividade_just": produtividade_just,
        "comportamento_just": comportamento_just,
    }])

def list_last_weekly(limit: int = 12):
    return fetch_df(f"""
        SELECT w.week_start AS week_start, e.name AS name, e.sector AS sector, e.role AS role,
               w.items_count, w.efficiency_pct, w.taxa_erros_pct,
               w.assiduidade_pct, w.qualidade_pct, w.produtividade_pct, w.comportamento_pct,
               COALESCE(w.evaluator,'') AS evaluator
        FROM weekly_evaluations w
        JOIN employees e ON e.id = w.employee_id
        ORDER BY w.week_start DESC
        LIMIT {int(limit)}
    """)

# ----------------------
# Weekly Errors (log)
# ----------------------
WEEKLY_ERROR_INSERT_SQL = """
INSERT INTO weekly_errors (
    employee_id, week_start, role_snapshot, error_type, severity, qty, notes, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


def add_weekly_error(employee_id: int, week_start_iso: str, role_snapshot: str, error_type: str, severity: str, qty: int, notes: str):
    now = datetime.now().isoformat(timespec="seconds")
    week_start_iso = normalize_week_start_iso(week_start_iso)
    exec_sql(WEEKLY_ERROR_INSERT_SQL, (employee_id, week_start_iso, role_snapshot, error_type, severity, int(qty), notes.strip(), now))


def add_weekly_errors(rows: list[dict]) -> int:
    if not rows:
        return 0

    now = datetime.now().isoformat(timespec="seconds")
    params = []
    for row in rows:
        week_start_iso = normalize_week_start_iso(row.get("week_start_iso") or row.get("week_start"))
        created_at = str(row.get("created_at") or "").strip() or now
        params.append((
            int(row.get("employee_id")),
            str(week_start_iso),
            str(row.get("role_snapshot", "")).strip(),
            str(row.get("error_type", "")).strip(),
            str(row.get("severity", "")).strip(),
            int(row.get("qty", 1)),
            str(row.get("notes", "")).strip(),
            created_at,
        ))

    with db() as con:
        con.executemany(WEEKLY_ERROR_INSERT_SQL, params)

    return len(params)


def list_weekly_errors(employee_id: int, week_start_iso: str) -> pd.DataFrame:
    week_start_iso = normalize_week_start_iso(week_start_iso)
    return fetch_df("""
        SELECT id, error_type, severity, qty, COALESCE(notes,'') AS notes, created_at
        FROM weekly_errors
        WHERE employee_id=? AND week_start=?
        ORDER BY id DESC
    """, (employee_id, week_start_iso))

def delete_weekly_error(error_id: int):
    exec_sql("DELETE FROM weekly_errors WHERE id=?", (error_id,))

# ----------------------
# Monitor Monthly Eval
# ----------------------
def upsert_monitor_monthly_eval(
    employee_id: int,
    month: str,
    evaluator: str,
    notes: str,
    pcts: dict,
    justs: dict,
):
    now = datetime.now().isoformat(timespec="seconds")
    month = normalize_month_label(month)

    with db() as con:
        con.execute("""
        INSERT INTO monitor_monthly_evaluations (
            employee_id, month, evaluator, notes,
            acomp_metas_pct, org_fluxo_pct, suporte_equipe_pct, disciplina_oper_pct,
            acomp_metas_just, org_fluxo_just, suporte_equipe_just, disciplina_oper_just,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(employee_id, month) DO UPDATE SET
            evaluator=excluded.evaluator,
            notes=excluded.notes,
            acomp_metas_pct=excluded.acomp_metas_pct,
            org_fluxo_pct=excluded.org_fluxo_pct,
            suporte_equipe_pct=excluded.suporte_equipe_pct,
            disciplina_oper_pct=excluded.disciplina_oper_pct,
            acomp_metas_just=excluded.acomp_metas_just,
            org_fluxo_just=excluded.org_fluxo_just,
            suporte_equipe_just=excluded.suporte_equipe_just,
            disciplina_oper_just=excluded.disciplina_oper_just
        ;
        """, (
            int(employee_id),
            str(month),
            str(evaluator).strip(),
            str(notes).strip(),

            float(pcts.get("acomp_metas", 100)),
            float(pcts.get("org_fluxo", 100)),
            float(pcts.get("suporte_equipe", 100)),
            float(pcts.get("disciplina_oper", 100)),

            str(justs.get("acomp_metas", "")).strip(),
            str(justs.get("org_fluxo", "")).strip(),
            str(justs.get("suporte_equipe", "")).strip(),
            str(justs.get("disciplina_oper", "")).strip(),

            now,
        ))

def update_employee(
    employee_id: int,
    name: str,
    sector: str,
    role: str,
    is_monitor: bool,
    hire_date: str = "",
    is_leadership: bool = False,
    monitor_start_date: str = "",
    leadership_start_date: str = "",
    termination_date: str = "",
    picking_operator_name: str = "",
    bybox_operator_name: str = "",
    updated_by_user_id: int | None = None,
    updated_by_username: str = "",
):
    hire_date = normalize_hire_date_iso(hire_date)
    if not hire_date:
        raise ValueError("Preencha a data de contratação.")
    termination_date = normalize_termination_date_iso(termination_date)
    active_value = active_from_termination_date(termination_date)
    deactivated_at = datetime.now().isoformat(timespec="seconds") if active_value == 0 else ""
    is_monitor_value, is_leadership_value, monitor_start_date, leadership_start_date = _normalize_employee_role_dates(
        is_monitor=is_monitor,
        is_leadership=is_leadership,
        monitor_start_date=monitor_start_date,
        leadership_start_date=leadership_start_date,
    )
    exec_sql(
        """
        UPDATE employees
        SET
            name = ?,
            sector = ?,
            role = ?,
            hire_date = ?,
            monitor_start_date = ?,
            leadership_start_date = ?,
            termination_date = ?,
            picking_operator_name = ?,
            bybox_operator_name = ?,
            is_monitor = ?,
            is_leadership = ?,
            active = ?,
            deactivated_at = ?,
            updated_by_user_id = ?,
            updated_by_username = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            name.strip(),
            sector.strip(),
            role.strip(),
            hire_date,
            monitor_start_date,
            leadership_start_date,
            termination_date,
            str(picking_operator_name or "").strip(),
            str(bybox_operator_name or "").strip(),
            is_monitor_value,
            is_leadership_value,
            active_value,
            deactivated_at,
            updated_by_user_id,
            str(updated_by_username or "").strip(),
            datetime.now().isoformat(timespec="seconds"),
            int(employee_id),
        ),
    )
