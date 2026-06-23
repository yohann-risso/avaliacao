from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

from constants import DEFAULT_ERROR_TYPES, SEVERITIES
from db import normalize_week_start_iso


CANONICAL_COLUMNS = {
    "employee_id": {
        "employee_id",
        "employee id",
        "id",
        "id funcionario",
        "id_funcionario",
        "funcionario_id",
        "colaborador_id",
    },
    "employee_name": {
        "employee_name",
        "funcionario_nome_conferencia",
        "nome_funcionario",
        "funcionario",
        "funcionário",
        "colaborador",
        "nome",
        "name",
    },
    "week_start": {
        "week_start",
        "semana",
        "semana_inicio",
        "inicio_semana",
        "data_semana",
        "data",
    },
    "role_snapshot": {
        "role_snapshot",
        "funcao",
        "função",
        "cargo",
        "role",
    },
    "error_type": {
        "error_type",
        "tipo",
        "tipo_erro",
        "tipo de erro",
        "erro",
    },
    "severity": {
        "severity",
        "gravidade",
    },
    "qty": {
        "qty",
        "qtd",
        "quantidade",
    },
    "notes": {
        "notes",
        "obs",
        "observacao",
        "observação",
        "nota",
        "notas",
    },
    "created_at": {
        "created_at",
        "criado_em",
        "data_criacao",
    },
}

ALIASES_TO_CANONICAL = {
    _alias: canonical
    for canonical, aliases in CANONICAL_COLUMNS.items()
    for _alias in aliases
}

DATA_COLUMNS = [
    "employee_id",
    "employee_name",
    "week_start",
    "role_snapshot",
    "error_type",
    "severity",
    "qty",
    "notes",
    "created_at",
]
PREVIEW_SOURCE_COLUMN = "source_row"


@dataclass(frozen=True)
class EmployeeMatch:
    employee_id: int | None
    name: str
    role: str
    sector: str
    method: str
    score: float
    message: str = ""


def normalize_lookup_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_column_name(value: Any) -> str:
    text = normalize_lookup_text(value)
    return text.replace(" ", "_")


def canonical_column_name(value: Any) -> str:
    normalized = normalize_lookup_text(value)
    underscored = normalized.replace(" ", "_")
    return ALIASES_TO_CANONICAL.get(normalized) or ALIASES_TO_CANONICAL.get(underscored) or underscored


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def clean_text(value: Any) -> str:
    if is_blank(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def parse_positive_int(value: Any) -> int | None:
    if is_blank(value):
        return None
    if isinstance(value, bool):
        return None
    try:
        numeric = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    if not numeric.is_integer():
        return None
    parsed = int(numeric)
    return parsed if parsed > 0 else None


def parse_excel_date(value: Any) -> date | None:
    if is_blank(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value > 0:
            return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
        return None
    try:
        return datetime.fromisoformat(str(value).strip()).date()
    except ValueError:
        pass
    try:
        return datetime.strptime(str(value).strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def parse_week_start(value: Any, default_week_start_iso: str = "") -> tuple[str, str]:
    used_default = False
    parsed_date = parse_excel_date(value)
    if parsed_date is None and default_week_start_iso:
        parsed_date = datetime.strptime(normalize_week_start_iso(default_week_start_iso), "%Y-%m-%d").date()
        used_default = True
    if parsed_date is None:
        raise ValueError("week_start vazio ou invalido")
    if parsed_date.weekday() != 0:
        raise ValueError("week_start deve ser uma segunda-feira")
    message = "week_start vazio; usada a semana selecionada" if used_default else ""
    return parsed_date.isoformat(), message


def parse_created_at(value: Any) -> tuple[str, str]:
    if is_blank(value):
        return "", ""
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime().isoformat(timespec="seconds"), ""
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds"), ""
    if isinstance(value, date):
        return datetime.combine(value, time.min).isoformat(timespec="seconds"), ""
    text = clean_text(value)
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.isoformat(timespec="seconds"), ""
    except ValueError:
        return "", "created_at invalido; sera preenchido ao importar"


def canonical_error_type(value: Any) -> str | None:
    lookup = normalize_lookup_text(value)
    if not lookup:
        return None
    for option in DEFAULT_ERROR_TYPES:
        if normalize_lookup_text(option) == lookup:
            return option
    return None


def canonical_severity(value: Any) -> str | None:
    lookup = normalize_lookup_text(value)
    if not lookup:
        return None
    aliases = {
        "baixo": "BAIXO",
        "baixa": "BAIXO",
        "medio": "MEDIO",
        "media": "MEDIO",
        "alto": "ALTO",
        "alta": "ALTO",
        "critico": "CRITICO",
        "critica": "CRITICO",
    }
    canonical = aliases.get(lookup)
    if canonical in SEVERITIES:
        return canonical
    upper = clean_text(value).upper()
    return upper if upper in SEVERITIES else None


def normalized_import_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=DATA_COLUMNS)

    out = raw_df.copy()
    rename_map = {col: canonical_column_name(col) for col in out.columns}
    out = out.rename(columns=rename_map)

    # If aliases collide, keep the first non-blank value from left to right.
    collapsed = pd.DataFrame(index=out.index)
    source_rows = []
    for pos, idx in enumerate(out.index):
        source_value = out[PREVIEW_SOURCE_COLUMN].iloc[pos] if PREVIEW_SOURCE_COLUMN in out.columns else None
        parsed_source = parse_positive_int(source_value)
        if parsed_source is None:
            try:
                parsed_source = int(idx) + 1
            except (TypeError, ValueError):
                parsed_source = pos + 1
        source_rows.append(parsed_source)
    collapsed[PREVIEW_SOURCE_COLUMN] = source_rows
    for col in DATA_COLUMNS:
        matching = [c for c in out.columns if c == col]
        if not matching:
            collapsed[col] = None
            continue
        values = out[matching[0]].copy()
        for extra in matching[1:]:
            values = values.where(~values.map(is_blank), out[extra])
        collapsed[col] = values

    active_mask = ~collapsed[DATA_COLUMNS].apply(lambda row: all(is_blank(v) for v in row), axis=1)
    return collapsed[active_mask].reset_index(drop=True)


def find_header_row(raw_df: pd.DataFrame) -> int | None:
    if raw_df is None or raw_df.empty:
        return None
    for idx, row in raw_df.head(25).iterrows():
        canonical = {canonical_column_name(cell) for cell in row.tolist() if not is_blank(cell)}
        has_core = {"error_type", "severity"}.issubset(canonical)
        has_person = bool({"employee_id", "employee_name"} & canonical)
        has_week = "week_start" in canonical
        if has_core and has_person and has_week:
            return int(idx)
    return None


def load_weekly_error_import_file(uploaded_file) -> pd.DataFrame:
    try:
        raw = pd.read_excel(uploaded_file, sheet_name="Importacao_Erros", header=None, dtype=object)
    except ValueError:
        raw = pd.read_excel(uploaded_file, sheet_name=0, header=None, dtype=object)

    header_idx = find_header_row(raw)
    if header_idx is None:
        raise ValueError("Nao encontrei a linha de cabecalho da importacao no XLSX.")

    headers = raw.iloc[header_idx].tolist()
    data = raw.iloc[header_idx + 1 :].copy()
    data.columns = headers
    return normalized_import_dataframe(data)


def _employee_lookup(employees_df: pd.DataFrame) -> tuple[dict[int, dict], list[dict]]:
    id_map: dict[int, dict] = {}
    rows: list[dict] = []
    if employees_df is None or employees_df.empty:
        return id_map, rows

    for _, row in employees_df.iterrows():
        try:
            employee_id = int(row.get("id"))
        except (TypeError, ValueError):
            continue
        item = {
            "id": employee_id,
            "name": clean_text(row.get("name")),
            "role": clean_text(row.get("role")),
            "sector": clean_text(row.get("sector")),
            "norm_name": normalize_lookup_text(row.get("name")),
        }
        id_map[employee_id] = item
        rows.append(item)
    return id_map, rows


def match_employee(employee_id_value: Any, name_value: Any, employees_df: pd.DataFrame) -> EmployeeMatch:
    id_map, employees = _employee_lookup(employees_df)
    messages: list[str] = []

    parsed_id = parse_positive_int(employee_id_value)
    query_name = clean_text(name_value)
    normalized_query = normalize_lookup_text(query_name)

    if parsed_id is not None:
        matched = id_map.get(parsed_id)
        if matched:
            if normalized_query and normalized_query != matched["norm_name"]:
                messages.append("nome de conferencia difere do employee_id")
            return EmployeeMatch(
                employee_id=matched["id"],
                name=matched["name"],
                role=matched["role"],
                sector=matched["sector"],
                method="employee_id",
                score=1.0,
                message="; ".join(messages),
            )
        messages.append("employee_id nao encontrado; tentando pelo nome")
    elif not is_blank(employee_id_value):
        messages.append("employee_id invalido; tentando pelo nome")

    if not normalized_query:
        return EmployeeMatch(None, "", "", "", "sem_identificacao", 0.0, "; ".join(messages))

    exact = [emp for emp in employees if emp["norm_name"] == normalized_query]
    if len(exact) == 1:
        emp = exact[0]
        return EmployeeMatch(emp["id"], emp["name"], emp["role"], emp["sector"], "nome_exato", 1.0, "; ".join(messages))
    if len(exact) > 1:
        messages.append("nome exato ambiguo; informe employee_id")
        return EmployeeMatch(None, query_name, "", "", "nome_ambiguo", 1.0, "; ".join(messages))

    scored: list[tuple[float, str, dict]] = []
    for emp in employees:
        norm_name = emp["norm_name"]
        if not norm_name:
            continue
        if normalized_query in norm_name or norm_name in normalized_query:
            short = min(len(normalized_query), len(norm_name))
            long = max(len(normalized_query), len(norm_name))
            score = 0.86 + min(0.1, short / max(long, 1) * 0.1)
            method = "nome_parcial"
        else:
            score = SequenceMatcher(None, normalized_query, norm_name).ratio()
            method = "nome_aproximado"
        scored.append((score, method, emp))

    if not scored:
        return EmployeeMatch(None, query_name, "", "", "nao_encontrado", 0.0, "; ".join(messages))

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_method, best = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    threshold = 0.86 if best_method == "nome_parcial" else 0.78
    required_margin = 0.04 if best_method == "nome_parcial" else 0.08

    if best_score >= threshold and best_score - second_score >= required_margin:
        messages.append(f"identificado por {best_method}")
        return EmployeeMatch(
            best["id"],
            best["name"],
            best["role"],
            best["sector"],
            best_method,
            round(float(best_score), 3),
            "; ".join(messages),
        )

    messages.append("nome nao identificado com seguranca; informe employee_id")
    return EmployeeMatch(None, query_name, "", "", "nao_identificado", round(float(best_score), 3), "; ".join(messages))


def prepare_weekly_error_import(
    raw_df: pd.DataFrame,
    employees_df: pd.DataFrame,
    default_week_start_iso: str = "",
) -> dict:
    data = normalized_import_dataframe(raw_df)
    preview_rows: list[dict] = []
    valid_rows: list[dict] = []

    for idx, row in data.iterrows():
        source_row = parse_positive_int(row.get(PREVIEW_SOURCE_COLUMN)) or (int(idx) + 2)
        row_messages: list[str] = []
        row_errors: list[str] = []

        match = match_employee(row.get("employee_id"), row.get("employee_name"), employees_df)
        if match.employee_id is None:
            row_errors.append(match.message or "funcionario nao identificado")
        elif match.message:
            row_messages.append(match.message)

        try:
            week_start_iso, week_msg = parse_week_start(row.get("week_start"), default_week_start_iso)
            if week_msg:
                row_messages.append(week_msg)
        except ValueError as exc:
            week_start_iso = ""
            row_errors.append(str(exc))

        role_snapshot = clean_text(row.get("role_snapshot")) or match.role
        if not role_snapshot:
            row_errors.append("role_snapshot vazio")

        error_type = canonical_error_type(row.get("error_type"))
        if not error_type:
            row_errors.append("error_type invalido")

        severity = canonical_severity(row.get("severity"))
        if not severity:
            row_errors.append("severity invalida")

        qty = parse_positive_int(row.get("qty"))
        if qty is None:
            if is_blank(row.get("qty")):
                qty = 1
                row_messages.append("qty vazio; assumido 1")
            else:
                row_errors.append("qty deve ser inteiro maior que zero")
                qty = 0

        created_at, created_msg = parse_created_at(row.get("created_at"))
        if created_msg:
            row_messages.append(created_msg)

        status = "OK" if not row_errors else "REVISAR"
        message = "; ".join(row_errors or row_messages)
        treated = {
            "source_row": source_row,
            "status": status,
            "employee_id": match.employee_id,
            "funcionario": match.name or clean_text(row.get("employee_name")),
            "setor": match.sector,
            "match": match.method,
            "score": match.score,
            "week_start": week_start_iso,
            "role_snapshot": role_snapshot,
            "error_type": error_type or clean_text(row.get("error_type")),
            "severity": severity or clean_text(row.get("severity")),
            "qty": qty,
            "notes": clean_text(row.get("notes")),
            "created_at": created_at or "preencher ao importar",
            "mensagem": message,
        }
        preview_rows.append(treated)

        if status == "OK":
            valid_rows.append(
                {
                    "employee_id": int(match.employee_id),
                    "week_start_iso": week_start_iso,
                    "role_snapshot": role_snapshot,
                    "error_type": str(error_type),
                    "severity": str(severity),
                    "qty": int(qty),
                    "notes": clean_text(row.get("notes")),
                    "created_at": created_at,
                }
            )

    preview_df = pd.DataFrame(preview_rows)
    total = len(preview_df)
    invalid = int((preview_df["status"] != "OK").sum()) if not preview_df.empty else 0
    return {
        "preview_df": preview_df,
        "valid_rows": valid_rows,
        "summary": {
            "total": total,
            "valid": len(valid_rows),
            "invalid": invalid,
        },
    }
