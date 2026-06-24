import pandas as pd

import picking_metrics
from picking_metrics import ProcessMetric, combine_process_metrics, employee_operator_name


def test_combine_process_metrics_weights_productivity_by_pieces():
    metric = combine_process_metrics(
        picking=ProcessMetric(pieces=800, productivity_pct=90),
        bybox=ProcessMetric(pieces=200, productivity_pct=70),
    )

    assert metric["items_count"] == 1000
    assert metric["produtividade_pct"] == 86.0
    assert metric["source_label"] == "Picking + By-Box"


def test_combine_process_metrics_uses_single_available_process():
    metric = combine_process_metrics(
        picking=ProcessMetric(pieces=120, productivity_pct=88),
    )

    assert metric["items_count"] == 120
    assert metric["produtividade_pct"] == 88.0
    assert metric["source_label"] == "Picking"


def test_combine_process_metrics_keeps_productivity_empty_without_execution():
    metric = combine_process_metrics()

    assert metric["items_count"] == 0
    assert metric["produtividade_pct"] is None
    assert metric["source_label"] == "Sem picking"


def test_combine_process_metrics_clamps_to_weekly_ui_range():
    metric = combine_process_metrics(
        picking=ProcessMetric(pieces=10, productivity_pct=130),
        bybox=ProcessMetric(pieces=10, productivity_pct=-10),
    )

    assert metric["produtividade_pct"] == 50.0
    assert metric["picking_produtividade_pct"] == 100.0
    assert metric["bybox_produtividade_pct"] == 0.0


def test_employee_operator_name_uses_mapping_or_employee_name():
    row = {
        "name": "Ana Silva",
        "picking_operator_name": "",
        "bybox_operator_name": "Ana S.",
    }

    assert employee_operator_name(row, "picking_operator_name") == "Ana Silva"
    assert employee_operator_name(row, "bybox_operator_name") == "Ana S."


def test_fetch_picking_process_metrics_uses_explicit_rpc_casts(monkeypatch):
    calls = []

    def fake_read_metric_sql(source_name, function_name, query, params):
        calls.append((source_name, function_name, query, params))
        return pd.DataFrame([{"operador": "Ana", "itens": 50, "eficiencia": 0.8}])

    monkeypatch.setattr(picking_metrics, "_read_metric_sql", fake_read_metric_sql)

    metrics = picking_metrics.fetch_picking_process_metrics("2026-06-22")

    assert metrics["ana"].pieces == 50
    assert metrics["ana"].productivity_pct == 80
    assert "p_data_ini => %s::date" in calls[0][2]
    assert "p_min_itens => %s::integer" in calls[0][2]


def test_fetch_bybox_process_metrics_uses_explicit_rpc_casts(monkeypatch):
    calls = []

    def fake_read_metric_sql(source_name, function_name, query, params):
        calls.append((source_name, function_name, query, params))
        return pd.DataFrame(
            [{"operador": "Ana", "pecas": 40, "eficiencia": 0.75}]
        )

    monkeypatch.setattr(picking_metrics, "_read_metric_sql", fake_read_metric_sql)

    metrics = picking_metrics.fetch_bybox_process_metrics("2026-06-22")

    assert metrics["ana"].pieces == 40
    assert metrics["ana"].productivity_pct == 75
    assert "p_inicio => %s::timestamptz" in calls[0][2]
    assert "p_fim => %s::timestamptz" in calls[0][2]


def test_weekly_metrics_do_not_write_zero_when_a_source_failed(monkeypatch):
    employees = pd.DataFrame(
        [{"id": 1, "name": "Ana", "picking_operator_name": "", "bybox_operator_name": ""}]
    )

    monkeypatch.setattr(picking_metrics, "is_sqlite_test_backend", lambda: False)
    monkeypatch.setattr(
        picking_metrics,
        "fetch_picking_process_metrics",
        lambda _week: (_ for _ in ()).throw(RuntimeError("falha externa")),
    )
    monkeypatch.setattr(picking_metrics, "fetch_bybox_process_metrics", lambda _week: {})

    metrics, warnings = picking_metrics.fetch_weekly_picking_metrics_for_employees(
        employees,
        "2026-06-22",
    )

    assert metrics == {}
    assert warnings == ["Picking: falha externa"]


def test_weekly_metrics_write_zero_when_all_sources_succeeded(monkeypatch):
    employees = pd.DataFrame(
        [{"id": 1, "name": "Ana", "picking_operator_name": "", "bybox_operator_name": ""}]
    )

    monkeypatch.setattr(picking_metrics, "is_sqlite_test_backend", lambda: False)
    monkeypatch.setattr(picking_metrics, "fetch_picking_process_metrics", lambda _week: {})
    monkeypatch.setattr(picking_metrics, "fetch_bybox_process_metrics", lambda _week: {})

    metrics, warnings = picking_metrics.fetch_weekly_picking_metrics_for_employees(
        employees,
        "2026-06-22",
    )

    assert warnings == []
    assert metrics[1]["items_count"] == 0
    assert metrics[1]["produtividade_pct"] is None
    assert metrics[1]["source_label"] == "Sem picking"
