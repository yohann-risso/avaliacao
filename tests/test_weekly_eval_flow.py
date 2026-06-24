from datetime import date

import pandas as pd

from ui_weekly import next_week_friday, weekly_eval_context_key, weekly_metric_cache_key


def test_next_week_friday_uses_following_week():
    assert next_week_friday(date(2026, 6, 24)) == date(2026, 7, 3)


def test_weekly_eval_context_key_uses_employee_and_week():
    assert weekly_eval_context_key(12, "2026-06-22") == "12|2026-06-22"


def test_weekly_metric_cache_key_includes_operator_mappings():
    row = pd.Series(
        {
            "id": 12,
            "name": "Andreza Bonan Rosa",
            "picking_operator_name": "Andreza Bonan",
            "bybox_operator_name": "",
        }
    )

    assert weekly_metric_cache_key(row, "2026-06-22") == (
        "12|2026-06-22|Andreza Bonan Rosa|Andreza Bonan|"
    )
