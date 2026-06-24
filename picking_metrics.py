from __future__ import annotations

import os
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from urllib import error as url_error
from urllib import request as url_request
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd

from db import is_sqlite_test_backend, normalize_week_start_iso


PICKING_DATABASE_URL_ENV_KEYS = (
    "PICKING_DATABASE_URL",
    "PICKING_SUPABASE_DB_URL",
    "PICKING_POSTGRES_URL",
)

PICKING_SUPABASE_URL_ENV_KEYS = (
    "PICKING_SUPABASE_URL",
    "PICKING_SUPABASE_PROJECT_URL",
)

PICKING_SUPABASE_KEY_ENV_KEYS = (
    "PICKING_SUPABASE_KEY",
    "PICKING_SUPABASE_ANON_KEY",
    "PICKING_SUPABASE_SERVICE_ROLE_KEY",
)


@dataclass(frozen=True)
class ProcessMetric:
    pieces: float = 0.0
    productivity_pct: float | None = None


def _database_url_with_ssl(url: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("sslmode", "require")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _normalize_supabase_url(url: str) -> str:
    value = str(url or "").strip().rstrip("/")
    if value and not value.lower().startswith(("http://", "https://")):
        raise RuntimeError("PICKING_SUPABASE_URL deve comecar com https://.")
    return value


def _secret_value(path: tuple[str, ...]) -> str:
    try:
        import streamlit as st

        current = st.secrets
        for key in path:
            current = current[key]
        return str(current or "").strip()
    except Exception:
        return ""


def get_picking_database_url() -> str:
    if is_sqlite_test_backend():
        return ""

    for key in PICKING_DATABASE_URL_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            return str(value).strip()

    secret_paths = (
        ("PICKING_DATABASE_URL",),
        ("PICKING_SUPABASE_DB_URL",),
        ("PICKING_POSTGRES_URL",),
        ("picking", "url"),
        ("connections", "picking", "url"),
        ("connections", "picking_supabase", "url"),
    )
    for path in secret_paths:
        value = _secret_value(path)
        if value:
            return value

    return ""


def get_picking_supabase_api_config() -> tuple[str, str]:
    if is_sqlite_test_backend():
        return "", ""

    api_url = ""
    api_key = ""
    for key in PICKING_SUPABASE_URL_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            api_url = str(value).strip()
            break
    for key in PICKING_SUPABASE_KEY_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            api_key = str(value).strip()
            break

    url_secret_paths = (
        ("PICKING_SUPABASE_URL",),
        ("PICKING_SUPABASE_PROJECT_URL",),
        ("picking", "supabase_url"),
        ("picking", "project_url"),
        ("connections", "picking", "supabase_url"),
        ("connections", "picking_supabase", "supabase_url"),
    )
    key_secret_paths = (
        ("PICKING_SUPABASE_KEY",),
        ("PICKING_SUPABASE_ANON_KEY",),
        ("PICKING_SUPABASE_SERVICE_ROLE_KEY",),
        ("picking", "supabase_key"),
        ("picking", "anon_key"),
        ("picking", "service_role_key"),
        ("connections", "picking", "supabase_key"),
        ("connections", "picking_supabase", "supabase_key"),
    )
    if not api_url:
        for path in url_secret_paths:
            value = _secret_value(path)
            if value:
                api_url = value
                break
    if not api_key:
        for path in key_secret_paths:
            value = _secret_value(path)
            if value:
                api_key = value
                break

    return _normalize_supabase_url(api_url), api_key


def _picking_source_not_configured_error() -> RuntimeError:
    return RuntimeError(
        "Fonte de picking nao configurada. Como as RPCs ficam em outro banco, configure "
        "PICKING_DATABASE_URL ou PICKING_SUPABASE_URL + PICKING_SUPABASE_KEY apontando "
        "para o projeto picking-kaisan."
    )


def _connect_picking_postgres():
    url = get_picking_database_url()
    if not url:
        raise RuntimeError("Banco de picking nao configurado.")
    if not url.lower().startswith(("postgres://", "postgresql://")):
        raise RuntimeError("PICKING_DATABASE_URL deve ser uma connection string PostgreSQL/Supabase.")

    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Instale psycopg para ler metricas de picking.") from exc

    return psycopg.connect(
        _database_url_with_ssl(url),
        connect_timeout=15,
        prepare_threshold=None,
    )


def _read_picking_sql(query: str, params: tuple = ()) -> pd.DataFrame:
    with _connect_picking_postgres() as con:
        cur = con.execute(query, params)
        if not cur.description:
            return pd.DataFrame()
        columns = [str(getattr(desc, "name", None) or desc[0]) for desc in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columns)


def _read_picking_rpc(function_name: str, payload: dict, select: str | None = None) -> pd.DataFrame:
    api_url, api_key = get_picking_supabase_api_config()
    if not api_url or not api_key:
        raise _picking_source_not_configured_error()

    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    query = urlencode({"select": select}) if select else ""
    endpoint = f"{api_url}/rest/v1/rpc/{function_name}"
    if query:
        endpoint = f"{endpoint}?{query}"
    req = url_request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with url_request.urlopen(req, timeout=30) as res:
            raw = res.read().decode("utf-8")
    except url_error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"RPC {function_name} falhou via Supabase API ({exc.code}): {details or exc.reason}"
        ) from exc
    except url_error.URLError as exc:
        raise RuntimeError(f"Nao foi possivel conectar ao Supabase de picking: {exc.reason}") from exc

    if not raw.strip():
        return pd.DataFrame()
    data = json.loads(raw)
    if isinstance(data, list):
        return pd.DataFrame(data)
    if isinstance(data, dict):
        return pd.DataFrame([data])
    return pd.DataFrame()


def _is_undefined_function_error(exc: Exception) -> bool:
    sqlstate = str(getattr(exc, "sqlstate", "") or "")
    if sqlstate == "42883":
        return True
    return "function " in str(exc).lower() and " does not exist" in str(exc).lower()


def _read_metric_sql(source_name: str, function_name: str, query: str, params: tuple = ()) -> pd.DataFrame:
    try:
        return _read_picking_sql(query, params)
    except Exception as exc:
        if _is_undefined_function_error(exc):
            raise RuntimeError(
                f"RPC {function_name} nao encontrada com a assinatura esperada no banco configurado "
                f"para {source_name}. Verifique PICKING_DATABASE_URL ou aplique a funcao no Supabase "
                "de picking."
            ) from exc
        raise


def _read_metric_rows(
    source_name: str,
    function_signature: str,
    sql_query: str,
    sql_params: tuple,
    rpc_name: str,
    rpc_payload: dict,
    rpc_select: str | None = None,
) -> pd.DataFrame:
    if get_picking_database_url():
        return _read_metric_sql(source_name, function_signature, sql_query, sql_params)
    return _read_picking_rpc(rpc_name, rpc_payload, select=rpc_select)


def _to_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        if isinstance(value, Decimal):
            number = float(value)
        else:
            number = float(value)
        if not math.isfinite(number):
            return float(default)
        return number
    except Exception:
        return float(default)


def _operator_key(value: str) -> str:
    return str(value or "").replace("\r", "").replace("\n", "").strip().casefold()


def _clamp_pct(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        pct = float(value)
    except Exception:
        return None
    if not math.isfinite(pct):
        return None
    return max(0.0, min(100.0, pct))


def _week_dates(week_start_iso: str) -> tuple[str, str, str]:
    start_iso = normalize_week_start_iso(week_start_iso)
    start = datetime.strptime(start_iso, "%Y-%m-%d").date()
    end_inclusive = start + timedelta(days=6)
    end_exclusive = start + timedelta(days=7)
    return start.isoformat(), end_inclusive.isoformat(), end_exclusive.isoformat()


def combine_process_metrics(
    picking: ProcessMetric | None = None,
    bybox: ProcessMetric | None = None,
) -> dict:
    picking = picking or ProcessMetric()
    bybox = bybox or ProcessMetric()

    picking_pieces = max(0.0, _to_float(picking.pieces))
    bybox_pieces = max(0.0, _to_float(bybox.pieces))
    total_pieces = picking_pieces + bybox_pieces

    weighted_parts = []
    picking_pct = _clamp_pct(picking.productivity_pct)
    bybox_pct = _clamp_pct(bybox.productivity_pct)
    if picking_pieces > 0 and picking_pct is not None:
        weighted_parts.append((picking_pieces, picking_pct))
    if bybox_pieces > 0 and bybox_pct is not None:
        weighted_parts.append((bybox_pieces, bybox_pct))

    productivity_pct = None
    if weighted_parts:
        weight_total = sum(weight for weight, _pct in weighted_parts)
        productivity_pct = sum(weight * pct for weight, pct in weighted_parts) / weight_total
        productivity_pct = _clamp_pct(round(productivity_pct, 1))

    sources = []
    if picking_pieces > 0:
        sources.append("Picking")
    if bybox_pieces > 0:
        sources.append("By-Box")

    return {
        "items_count": int(round(total_pieces)),
        "produtividade_pct": productivity_pct,
        "picking_items": int(round(picking_pieces)),
        "picking_produtividade_pct": picking_pct,
        "bybox_items": int(round(bybox_pieces)),
        "bybox_produtividade_pct": bybox_pct,
        "source_label": " + ".join(sources) if sources else "Sem picking",
    }


def fetch_picking_process_metrics(week_start_iso: str) -> dict[str, ProcessMetric]:
    dt_ini, dt_fim, _dt_exclusive = _week_dates(week_start_iso)
    df = _read_metric_rows(
        "Picking",
        "public.fn_eficiencia_por_operador_periodo(date, date, integer, integer)",
        """
        SELECT operador, itens, eficiencia
        FROM public.fn_eficiencia_por_operador_periodo(
            p_data_ini => %s::date,
            p_data_fim => %s::date,
            p_min_itens => %s::integer,
            p_cutoff_delta_seg => %s::integer
        )
        """,
        (dt_ini, dt_fim, 1, 300),
        "fn_eficiencia_por_operador_periodo",
        {
            "p_data_ini": dt_ini,
            "p_data_fim": dt_fim,
            "p_min_itens": 1,
            "p_cutoff_delta_seg": 300,
        },
        "operador,itens,eficiencia",
    )
    metrics: dict[str, ProcessMetric] = {}
    for _, row in df.iterrows():
        key = _operator_key(row.get("operador"))
        if not key:
            continue
        pieces = max(0.0, _to_float(row.get("itens")))
        productivity = _clamp_pct(_to_float(row.get("eficiencia")) * 100.0)
        metrics[key] = ProcessMetric(pieces=pieces, productivity_pct=productivity)
    return metrics


def fetch_bybox_process_metrics(week_start_iso: str) -> dict[str, ProcessMetric]:
    dt_ini, _dt_fim, dt_exclusive = _week_dates(week_start_iso)
    df = _read_metric_rows(
        "By-Box",
        "public.rpc_bybox_eficiencia_participantes_periodo(timestamptz, timestamptz)",
        """
        SELECT
            operador,
            COALESCE(SUM(n_pecas_individual), 0)::numeric AS pecas,
            CASE
                WHEN COALESCE(SUM(tempo_real_seg), 0) > 0
                    THEN COALESCE(SUM(tempo_ideal_individual_seg), 0)::numeric
                         / NULLIF(SUM(tempo_real_seg), 0)
                ELSE NULL
            END AS eficiencia
        FROM public.rpc_bybox_eficiencia_participantes_periodo(
            p_inicio => %s::timestamptz,
            p_fim => %s::timestamptz
        )
        GROUP BY operador
        """,
        (f"{dt_ini}T00:00:00-03:00", f"{dt_exclusive}T00:00:00-03:00"),
        "rpc_bybox_eficiencia_participantes_periodo",
        {
            "p_inicio": f"{dt_ini}T00:00:00-03:00",
            "p_fim": f"{dt_exclusive}T00:00:00-03:00",
        },
        "operador,n_pecas_individual,tempo_ideal_individual_seg,tempo_real_seg",
    )
    if df.empty:
        return {}

    if "pecas" not in df.columns or "eficiencia" not in df.columns:
        grouped: dict[str, dict[str, float]] = {}
        for _, row in df.iterrows():
            key = _operator_key(row.get("operador"))
            if not key:
                continue
            current = grouped.setdefault(key, {"pecas": 0.0, "ideal": 0.0, "real": 0.0})
            current["pecas"] += max(0.0, _to_float(row.get("n_pecas_individual")))
            current["ideal"] += max(0.0, _to_float(row.get("tempo_ideal_individual_seg")))
            current["real"] += max(0.0, _to_float(row.get("tempo_real_seg")))
        metrics = {}
        for key, totals in grouped.items():
            efficiency = totals["ideal"] / totals["real"] if totals["real"] > 0 else None
            productivity = None if efficiency is None else _clamp_pct(efficiency * 100.0)
            metrics[key] = ProcessMetric(pieces=totals["pecas"], productivity_pct=productivity)
        return metrics

    metrics: dict[str, ProcessMetric] = {}
    for _, row in df.iterrows():
        key = _operator_key(row.get("operador"))
        if not key:
            continue
        pieces = max(0.0, _to_float(row.get("pecas")))
        efficiency = row.get("eficiencia")
        productivity = None if efficiency is None else _clamp_pct(_to_float(efficiency) * 100.0)
        metrics[key] = ProcessMetric(pieces=pieces, productivity_pct=productivity)
    return metrics


def employee_operator_name(row: pd.Series | dict, column: str) -> str:
    fallback = str(row.get("name", "") or "").strip()
    mapped = str(row.get(column, "") or "").strip()
    return mapped or fallback


def fetch_weekly_picking_metrics_for_employees(
    employees_df: pd.DataFrame,
    week_start_iso: str,
) -> tuple[dict[int, dict], list[str]]:
    if employees_df.empty or is_sqlite_test_backend():
        return {}, []

    warnings: list[str] = []
    picking_ok = True
    bybox_ok = True
    try:
        picking_metrics = fetch_picking_process_metrics(week_start_iso)
    except Exception as exc:
        picking_ok = False
        picking_metrics = {}
        warnings.append(f"Picking: {exc}")

    try:
        bybox_metrics = fetch_bybox_process_metrics(week_start_iso)
    except Exception as exc:
        bybox_ok = False
        bybox_metrics = {}
        warnings.append(f"By-Box: {exc}")

    if not picking_ok and not bybox_ok:
        return {}, warnings

    combined: dict[int, dict] = {}
    for _, row in employees_df.iterrows():
        employee_id = int(row.get("id"))
        picking_key = _operator_key(employee_operator_name(row, "picking_operator_name"))
        bybox_key = _operator_key(employee_operator_name(row, "bybox_operator_name"))
        picking_metric = picking_metrics.get(picking_key)
        bybox_metric = bybox_metrics.get(bybox_key)

        if (not picking_ok or not bybox_ok) and picking_metric is None and bybox_metric is None:
            continue

        metric = combine_process_metrics(
            picking=picking_metric,
            bybox=bybox_metric,
        )
        metric["employee_id"] = employee_id
        metric["picking_operator_name"] = employee_operator_name(row, "picking_operator_name")
        metric["bybox_operator_name"] = employee_operator_name(row, "bybox_operator_name")
        combined[employee_id] = metric

    return combined, warnings
