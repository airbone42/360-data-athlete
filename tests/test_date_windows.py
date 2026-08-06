"""Tests for the shared date-cutoff helper (`app.utils.date_windows`)."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.date_windows import cutoff_iso


def test_matches_manual_timedelta_computation() -> None:
    today = date(2026, 8, 6)
    for n in (0, 1, 7, 60, 90):
        assert cutoff_iso(today, n) == (today - timedelta(days=n)).isoformat()


def test_zero_days_returns_same_date() -> None:
    today = date(2026, 8, 6)
    assert cutoff_iso(today, 0) == "2026-08-06"


def test_crosses_month_boundary() -> None:
    today = date(2026, 8, 6)
    assert cutoff_iso(today, 7) == "2026-07-30"


def test_crosses_year_boundary() -> None:
    today = date(2026, 1, 3)
    assert cutoff_iso(today, 5) == "2025-12-29"


def test_works_with_arbitrary_base_date_not_just_today() -> None:
    base = date(2025, 12, 25)
    assert cutoff_iso(base, 90) == (base - timedelta(days=90)).isoformat()
