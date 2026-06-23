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
