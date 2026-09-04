"""Balance-rotation cadence: frequency parsing, due logic, rotation stepping.

The framework default is daily (7/week), which is what existed before this
module. An athlete following the ankle-prevention evidence runs 2–3 longer,
harder sessions instead, and the auto-push had no way to express that.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.analytics.balance_schedule import (  # noqa: E402
    DEFAULT_SESSIONS_PER_WEEK,
    balance_due,
    min_gap_days,
    next_rotation,
    parse_balance_frequency,
)

TODAY = date(2026, 9, 10)


def _days_ago(*offsets: int) -> list[date]:
    return [TODAY - timedelta(days=o) for o in offsets]


# ─── Frequency parsing ───────────────────────────────────────────────────

def test_missing_key_keeps_the_daily_default():
    """An athlete who configures nothing sees no behaviour change."""
    assert parse_balance_frequency(None) == DEFAULT_SESSIONS_PER_WEEK
    assert parse_balance_frequency("") == DEFAULT_SESSIONS_PER_WEEK
    assert parse_balance_frequency("## Zones\n- **LTHR:** 166 bpm\n") == 7


def test_markdown_bullet_is_parsed():
    status = (
        "## Balance cadence (machine-readable)\n"
        "- **balance_sessions_per_week:** 3\n"
    )
    assert parse_balance_frequency(status) == 3


def test_plain_and_equals_forms_are_parsed():
    assert parse_balance_frequency("balance_sessions_per_week: 2") == 2
    assert parse_balance_frequency("balance_sessions_per_week = 4") == 4


def test_out_of_range_values_are_clamped():
    """Zero would silently retire a standing prescription — that is the
    athlete's decision, not a config typo's."""
    assert parse_balance_frequency("balance_sessions_per_week: 0") == 1
    assert parse_balance_frequency("balance_sessions_per_week: 99") == 7


# ─── Minimum gap ─────────────────────────────────────────────────────────

def test_min_gap_spreads_the_sessions():
    assert min_gap_days(7) == 1
    assert min_gap_days(3) == 2
    assert min_gap_days(2) == 3
    assert min_gap_days(1) == 7


# ─── Due logic ───────────────────────────────────────────────────────────

def test_daily_cadence_is_always_due():
    due, reason = balance_due(TODAY, _days_ago(1, 2, 3), 7)
    assert due is True
    assert "daily" in reason


def test_empty_window_is_due():
    due, _ = balance_due(TODAY, [], 3)
    assert due is True


def test_budget_reached_is_not_due():
    due, reason = balance_due(TODAY, _days_ago(2, 4, 6), 3)
    assert due is False
    assert "3/3" in reason


def test_minimum_gap_blocks_a_back_to_back_day():
    """Two of three used, but yesterday was one of them — at 3/week the gap
    is two days, so today is too soon even though the budget allows it."""
    due, reason = balance_due(TODAY, _days_ago(1, 4), 3)
    assert due is False
    assert "minimum gap" in reason


def test_gap_satisfied_within_budget_is_due():
    due, _ = balance_due(TODAY, _days_ago(2, 5), 3)
    assert due is True


def test_events_outside_the_rolling_window_do_not_count():
    """The window rolls; it does not reset on Monday. Sessions eight days
    back are irrelevant, sessions six days back are not."""
    due, _ = balance_due(TODAY, _days_ago(7, 8, 9), 3)
    assert due is True


def test_window_is_rolling_not_calendar_week():
    """A Fri/Sat/Sun cluster must still block the following Monday — under
    calendar-week counting it would not."""
    due, reason = balance_due(TODAY, _days_ago(2, 3, 4), 3)
    assert due is False
    assert "3/3" in reason


# ─── Rotation stepping ───────────────────────────────────────────────────

def test_rotation_steps_on_from_the_previous_key():
    assert next_rotation("A", TODAY) == "B"
    assert next_rotation("B", TODAY) == "C"
    assert next_rotation("C", TODAY) == "D"
    assert next_rotation("D", TODAY) == "A"


def test_rotation_falls_back_to_the_date_pick_when_unknown():
    """Unknown previous key reproduces the pre-existing behaviour exactly."""
    expected = ["A", "B", "C", "D"][TODAY.toordinal() % 4]
    assert next_rotation(None, TODAY) == expected
    assert next_rotation("Z", TODAY) == expected


def test_stepping_covers_all_four_at_a_reduced_cadence():
    """The reason stepping exists: at three sessions a week with a two-day
    gap, the date-based pick keeps drawing the same keys."""
    key = "A"
    seen = {key}
    for _ in range(3):
        key = next_rotation(key, TODAY)
        seen.add(key)
    assert seen == {"A", "B", "C", "D"}
