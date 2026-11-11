"""Tests for app/analytics/slot_ledger.py — ledger rows and the feed comparison."""
from __future__ import annotations

from datetime import date

from app.analytics.slot_ledger import (
    format_ledger_feed_gaps,
    ledger_appointments,
    ledger_rows,
    unmatched_ledger_appointments,
)

TODAY = date(2026, 11, 9)
LEDGER = """## Slot ledger

| Day | Booking |
|---|---|
| Sun 08.11. | Physio 09:00 |
| Mon 09.11. | Physio 10:20 (feed), hall 16:30. Ride Z2 (before 10:00) |
| Tue 10.11. | Treadmill test cancelled (athlete 09.11. 18:49: still sore); course 19:00 |
| Wed 11.11. | Ride Z2 50 min |
- 2026-11-12: club run 18:30
- 20.11.: far away 08:00

Note: physio Tue 19:00 only with a calendar entry.
"""


def test_rows_keyed_by_leading_date_within_horizon():
    rows = ledger_rows(LEDGER, TODAY, horizon_days=3)
    assert sorted(rows) == [date(2026, 11, 9), date(2026, 11, 10), date(2026, 11, 11), date(2026, 11, 12)]
    assert "Ride Z2 50 min" in rows[date(2026, 11, 11)]


def test_appointments_skip_bounds_timestamps_and_cancelled():
    appts = ledger_appointments(LEDGER, TODAY, horizon_days=3)
    got = [(a["date"].day, a["time"]) for a in appts]
    assert got == [(9, "10:20"), (9, "16:30"), (10, "19:00"), (12, "18:30")]
    assert appts[0]["label"].startswith("Physio")


def test_unmatched_against_feed():
    feed = [
        {"start": "2026-11-09T10:20", "allDay": False, "title": "Physio"},
        {"start": "2026-11-10T19:15", "allDay": False, "title": "Course"},
        {"start": "2026-11-12", "allDay": True, "title": "Holiday"},
    ]
    gaps = unmatched_ledger_appointments(LEDGER, feed, TODAY, horizon_days=3)
    assert [(g["date"].day, g["time"]) for g in gaps] == [(9, "16:30"), (12, "18:30")]
    text = format_ledger_feed_gaps(gaps)
    assert text and "2026-11-09 16:30" in text and "calendar feed wins" in text


def test_no_gaps_no_warning():
    assert format_ledger_feed_gaps([]) is None
