import logging
import re


_LOGGER = logging.getLogger("avaliacao.security")

_URL_CREDENTIALS_RE = re.compile(
    r"\b(?P<scheme>(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|rediss)://)"
    r"(?P<userinfo>[^@\s/]+)@",
    re.IGNORECASE,
)
_SECRET_QUERY_RE = re.compile(
    r"(?i)([?&](?:password|passwd|pwd|senha|secret|token|api[_-]?key|access_token|refresh_token)=)"
    r"[^&#\s]+"
)
_AUTH_HEADER_RE = re.compile(r"(?i)\b(?P<scheme>bearer|basic)\s+[A-Za-z0-9._~+/\-]+=*")
_KEY_VALUE_RE = re.compile(
    r"(?i)\b(?P<key>app_database_url|database_url|supabase_db_url|password|passwd|pwd|senha|"
    r"secret|token|api[_-]?key)\b"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<quote>['\"]?)"
    r"(?P<value>[^'\"\s,;]+)"
    r"(?P=quote)"
)


def redact_sensitive(value) -> str:
    text = str(value or "")
    if not text:
        return ""

    text = _URL_CREDENTIALS_RE.sub(r"\g<scheme>***:***@", text)
    text = _SECRET_QUERY_RE.sub(r"\1***", text)
    text = _AUTH_HEADER_RE.sub(lambda match: f"{match.group('scheme')} ***", text)
    return _KEY_VALUE_RE.sub(
        lambda match: (
            f"{match.group('key')}{match.group('sep')}"
            f"{match.group('quote')}***{match.group('quote')}"
        ),
        text,
    )


def public_error_message(exc: Exception, fallback: str) -> str:
    if isinstance(exc, ValueError):
        return redact_sensitive(str(exc))
    return fallback


def log_sanitized_exception(message: str, exc: Exception) -> None:
    _LOGGER.error("%s: %s", message, redact_sensitive(str(exc)))
