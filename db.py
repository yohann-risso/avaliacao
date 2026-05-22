# db.py

import hashlib
import hmac
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
import pandas as pd

APP_DIR = Path(__file__).resolve().parent
DB_PATH = str(APP_DIR / "avaliacoes.db")
PASSWORD_HASH_ITERATIONS = 390_000


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


@contextmanager
def db():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.execute("PRAGMA foreign_keys = ON;")
    con.execute("PRAGMA busy_timeout = 10000;")
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
        return pd.read_sql_query(query, con, params=params)

def exec_sql(query: str, params: tuple = ()):
    with db() as con:
        con.execute(query, params)

def ensure_column(con, table: str, col: str, coldef: str):
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {coldef};")

def init_db():
    with db() as con:
        con.execute("PRAGMA journal_mode = WAL;")
        con.execute("PRAGMA synchronous = NORMAL;")

        con.execute("""
        CREATE TABLE IF NOT EXISTS login_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            active INTEGER NOT NULL DEFAULT 1,
            last_login_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        );
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_login_users_active ON login_users(active, username);")

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
        ensure_column(con, "employees", "is_leadership", "is_leadership INTEGER NOT NULL DEFAULT 0")
        ensure_column(con, "employees", "deactivated_at", "deactivated_at TEXT NOT NULL DEFAULT ''")
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


def hash_password(password: str) -> str:
    password = str(password or "")
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")

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


def create_login_user(username: str, password: str, role: str = "admin", active: bool = True) -> int:
    username = normalize_username(username)
    password_hash = hash_password(password)
    role = str(role or "admin").strip().lower() or "admin"
    now = datetime.now().isoformat(timespec="seconds")

    try:
        with db() as con:
            cur = con.execute(
                """
                INSERT INTO login_users (
                    username, password_hash, role, active, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (username, password_hash, role, 1 if active else 0, now, now),
            )
            return int(cur.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise ValueError("Usuário de login já cadastrado.") from exc


def authenticate_login(username: str, password: str) -> dict | None:
    username = normalize_username(username)
    with db() as con:
        row = con.execute(
            """
            SELECT id, username, password_hash, role, active
            FROM login_users
            WHERE username = ?
            LIMIT 1
            """,
            (username,),
        ).fetchone()

        if not row:
            return None

        user_id, stored_username, stored_hash, role, active = row
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
            is_monitor, is_leadership, active, deactivated_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name.strip(),
            sector.strip(),
            role.strip(),
            hire_date,
            monitor_start_date,
            leadership_start_date,
            termination_date,
            is_monitor_value,
            is_leadership_value,
            active_value,
            deactivated_at,
            datetime.now().isoformat(timespec="seconds"),
        )
    )

def deactivate_employee(employee_id: int):
    today = date.today().isoformat()
    exec_sql(
        "UPDATE employees SET active=0, termination_date=?, deactivated_at=? WHERE id=?",
        (today, datetime.now().isoformat(timespec="seconds"), int(employee_id)),
    )


def reactivate_employee(employee_id: int):
    exec_sql("UPDATE employees SET active=1, termination_date='', deactivated_at='' WHERE id=?", (int(employee_id),))


def list_employees(include_inactive: bool = True):
    if include_inactive:
        return fetch_df("""
            SELECT
                id, name, sector, role, hire_date, monitor_start_date, leadership_start_date, termination_date,
                is_monitor, is_leadership, active, deactivated_at
            FROM employees
            ORDER BY active DESC, sector, role, name
        """)

    return list_active_employees()

def list_active_employees():
    return fetch_df("""
        SELECT
            id, name, sector, role, hire_date, monitor_start_date, leadership_start_date, termination_date,
            is_monitor, is_leadership, active, deactivated_at
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
        current = pd.read_sql_query(
            f"""
            SELECT w.*, 'current' AS basis_source
            FROM weekly_evaluations w
            WHERE w.week_start = ?
              AND w.employee_id IN ({placeholders})
            """,
            con,
            params=(week_start_iso, *ids),
        )

        previous = pd.read_sql_query(
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
            con,
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
def add_weekly_error(employee_id: int, week_start_iso: str, role_snapshot: str, error_type: str, severity: str, qty: int, notes: str):
    now = datetime.now().isoformat(timespec="seconds")
    week_start_iso = normalize_week_start_iso(week_start_iso)
    exec_sql("""
        INSERT INTO weekly_errors (
            employee_id, week_start, role_snapshot, error_type, severity, qty, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (employee_id, week_start_iso, role_snapshot, error_type, severity, int(qty), notes.strip(), now))

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
            is_monitor = ?,
            is_leadership = ?,
            active = ?,
            deactivated_at = ?
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
            is_monitor_value,
            is_leadership_value,
            active_value,
            deactivated_at,
            int(employee_id),
        ),
    )
