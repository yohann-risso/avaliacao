import argparse
import os
import sqlite3
import sys
from pathlib import Path


TABLES = [
    "login_users",
    "employees",
    "weekly_evaluations",
    "weekly_errors",
    "monitor_monthly_evaluations",
]

DELETE_ORDER = [
    "weekly_errors",
    "monitor_monthly_evaluations",
    "weekly_evaluations",
    "employees",
    "login_users",
]


def quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def rows_from_sqlite(sqlite_path: Path, table: str) -> list[dict]:
    with sqlite3.connect(sqlite_path) as con:
        con.row_factory = sqlite3.Row
        return [dict(row) for row in con.execute(f"SELECT * FROM {quote_ident(table)} ORDER BY id")]


def upsert_rows(dst_con, table: str, rows: list[dict]) -> int:
    if not rows:
        return 0

    columns = list(rows[0].keys())
    column_sql = ", ".join(quote_ident(col) for col in columns)
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(
        f"{quote_ident(col)} = EXCLUDED.{quote_ident(col)}"
        for col in columns
        if col != "id"
    )
    conflict_sql = f"DO UPDATE SET {updates}" if updates else "DO NOTHING"
    sql = (
        f"INSERT INTO {quote_ident(table)} ({column_sql}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT (id) {conflict_sql}"
    )
    params = [tuple(row.get(col) for col in columns) for row in rows]
    dst_con.executemany(sql, params)
    return len(rows)


def reset_identity(dst_con, table: str) -> None:
    table_sql = quote_ident(table)
    dst_con.execute(
        f"""
        SELECT setval(
            pg_get_serial_sequence('public.{table}', 'id'),
            COALESCE((SELECT MAX(id) FROM {table_sql}), 1),
            (SELECT MAX(id) IS NOT NULL FROM {table_sql})
        )
        """
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migra o avaliacoes.db local para o PostgreSQL/Supabase configurado em APP_DATABASE_URL."
    )
    parser.add_argument(
        "--sqlite-path",
        default=str(Path(__file__).resolve().parents[1] / "avaliacoes.db"),
        help="Caminho do banco SQLite de origem.",
    )
    parser.add_argument(
        "--database-url",
        default="",
        help="Connection string PostgreSQL/Supabase. Se omitida, usa APP_DATABASE_URL/DATABASE_URL/SUPABASE_DB_URL.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Apaga os dados atuais das tabelas antes de importar. Use somente em projeto novo ou backup confirmado.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sqlite_path = Path(args.sqlite_path).resolve()
    if not sqlite_path.exists():
        print(f"SQLite de origem não encontrado: {sqlite_path}", file=sys.stderr)
        return 1

    if args.database_url:
        os.environ["APP_DATABASE_URL"] = args.database_url

    import db

    if not db.is_postgres_backend():
        print(
            "Configure APP_DATABASE_URL, DATABASE_URL ou SUPABASE_DB_URL com uma connection string PostgreSQL.",
            file=sys.stderr,
        )
        return 1

    db.init_db()

    copied: dict[str, int] = {}
    with db.db() as dst_con:
        if args.replace:
            for table in DELETE_ORDER:
                dst_con.execute(f"DELETE FROM {quote_ident(table)}")

        for table in TABLES:
            rows = rows_from_sqlite(sqlite_path, table)
            copied[table] = upsert_rows(dst_con, table, rows)
            reset_identity(dst_con, table)

    for table, count in copied.items():
        print(f"{table}: {count} linha(s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
