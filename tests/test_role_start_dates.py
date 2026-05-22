from ui_report import is_employee_leadership_for_month, is_employee_monitor_for_month
from utils import eligible_weeks_after_start_date, has_eligible_week_after_start_date


def test_role_start_date_uses_second_week_rule():
    weeks = ["2026-05-04", "2026-05-11", "2026-05-18"]

    assert eligible_weeks_after_start_date(
        "2026-05-05",
        weeks,
        missing_is_eligible=False,
    ) == ["2026-05-11", "2026-05-18"]
    assert has_eligible_week_after_start_date("", weeks, missing_is_eligible=False) is False


def test_monitor_and_leadership_need_their_own_start_dates():
    weeks = ["2026-05-04", "2026-05-11"]

    assert is_employee_monitor_for_month(
        {
            "is_monitor": 1,
            "is_leadership": 0,
            "monitor_start_date": "2026-05-06",
        },
        weeks,
    )
    assert not is_employee_monitor_for_month(
        {
            "is_monitor": 1,
            "is_leadership": 0,
            "monitor_start_date": "",
        },
        weeks,
    )
    assert is_employee_leadership_for_month(
        {
            "is_leadership": 1,
            "leadership_start_date": "2026-05-06",
        },
        weeks,
    )
