import argparse
import getpass
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from security import redact_sensitive

SECRETS_PATH = ROOT_DIR / ".streamlit" / "secrets.toml"
DATABASE_URL_ENV_KEYS = ("APP_DATABASE_URL", "DATABASE_URL", "SUPABASE_DB_URL")


def get_existing_database_url() -> str:
    for key in DATABASE_URL_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            return str(value).strip()
    return ""


def read_clipboard() -> str:
    if os.name == "nt" and shutil.which("powershell"):
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    if shutil.which("pbpaste"):
        completed = subprocess.run(["pbpaste"], check=True, capture_output=True, text=True)
        return completed.stdout.strip()

    if shutil.which("wl-paste"):
        completed = subprocess.run(["wl-paste", "--no-newline"], check=True, capture_output=True, text=True)
        return completed.stdout.strip()

    if shutil.which("xclip"):
        completed = subprocess.run(
            ["xclip", "-selection", "clipboard", "-out"],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    raise RuntimeError("Nao consegui ler a area de transferencia neste sistema.")


def normalize_database_url(value: str) -> str:
    url = str(value or "").strip()
    if not url:
        raise ValueError("Informe a connection string PostgreSQL/Supabase.")

    parts = urlsplit(url)
    if parts.scheme.lower() not in {"postgres", "postgresql"}:
        raise ValueError("A connection string deve comecar com postgres:// ou postgresql://.")

    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("sslmode", "require")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def toml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def confirm_overwrite(path: Path, force: bool) -> bool:
    if force or not path.exists():
        return True
    if not sys.stdin.isatty():
        raise RuntimeError(f"{path} ja existe. Use --force para sobrescrever.")

    answer = input(f"{path} ja existe. Sobrescrever? [s/N] ").strip().lower()
    return answer in {"s", "sim", "y", "yes"}


def write_streamlit_secret(database_url: str, force: bool) -> None:
    if not confirm_overwrite(SECRETS_PATH, force):
        print("Arquivo de secrets mantido sem alteracoes.")
        return

    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SECRETS_PATH.write_text(
        "\n".join(
            [
                "# Gerado por scripts/configure_supabase.py.",
                "# Nao commite este arquivo.",
                f"APP_DATABASE_URL = {toml_quote(database_url)}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Secrets gravado em {SECRETS_PATH}")


def validate_database(database_url: str) -> None:
    os.environ["APP_DATABASE_URL"] = database_url

    import db

    db.init_db()
    with db.db() as con:
        con.execute("SELECT COUNT(*) FROM login_users").fetchone()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Configura o Supabase/PostgreSQL do app e valida o schema remoto."
    )
    parser.add_argument(
        "--database-url",
        default="",
        help="Connection string PostgreSQL/Supabase. O modo interativo e mais seguro para colar senhas.",
    )
    parser.add_argument(
        "--from-clipboard",
        action="store_true",
        help="Le a connection string da area de transferencia.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescreve .streamlit/secrets.toml se ele ja existir.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Grava o secret sem conectar no banco. Use apenas para preparar ambiente.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_url = ""
    if args.from_clipboard:
        raw_url = read_clipboard()
    raw_url = raw_url or args.database_url or get_existing_database_url()
    if not raw_url and sys.stdin.isatty():
        raw_url = getpass.getpass("Cole a connection string PostgreSQL/Supabase: ")

    try:
        database_url = normalize_database_url(raw_url)
        if not args.skip_validation:
            validate_database(database_url)
            print("Conexao validada e schema garantido no Supabase/PostgreSQL.")
        write_streamlit_secret(database_url, force=args.force)
    except Exception as exc:
        print(f"Falha ao configurar Supabase: {redact_sensitive(exc)}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
