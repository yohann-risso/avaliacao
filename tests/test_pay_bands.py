import pytest

from rules import band_multiplier as rules_band_multiplier
from ui_monitor import band_multiplier as monitor_band_multiplier
from ui_report import band_multiplier as report_band_multiplier
from ui_weekly import band_multiplier as weekly_band_multiplier


@pytest.mark.parametrize(
    ("pct", "expected"),
    [
        (-10, 0.0),
        (0, 0.0),
        (50, 0.0),
        (50.5, 0.25),
        (70, 0.25),
        (70.5, 0.5),
        (80, 0.5),
        (80.5, 0.75),
        (90, 0.75),
        (90.5, 1.0),
        (100, 1.0),
        (110, 1.0),
    ],
)
def test_band_multiplier_handles_decimal_edges(pct, expected):
    for band_multiplier in (
        rules_band_multiplier,
        weekly_band_multiplier,
        monitor_band_multiplier,
        report_band_multiplier,
    ):
        assert band_multiplier(pct) == expected
