"""lastSessionEnd — inter-session recovery window field.

Recovery between sessions is a function of elapsed clock-time, not
calendar-day gap: a 22:00-ending session before an 08:00 briefing leaves
~10 h, not "one day". The field surfaces end time + hours since so the
planner reads the real window. Synthetic 2025 dates (athlete-agnostic).
"""
from __future__ import annotations

from datetime import datetime

from app.graphs.sub_athlete_context.context_builder import _compute_last_session_end

NOW = datetime(2025, 6, 2, 8, 0)


def _act(act_id: str, start: str, moving_min: int, name: str = "s") -> dict:
    return {
        "id": act_id,
        "start_date_local": start,
        "moving_time": moving_min * 60,
        "name": name,
    }


def test_late_evening_session_compresses_overnight_window():
    acts = [
        _act("i1", "2025-06-01T21:00:00", 60),   # ends 22:00 the evening before
        _act("i0", "2025-05-30T07:00:00", 45),
    ]
    r = _compute_last_session_end(acts, now=NOW)
    assert r is not None
    assert r["activityId"] == "i1"
    assert r["endLocal"] == "2025-06-01T22:00"
    assert r["hoursSinceEnd"] == 10.0  # NOT a full "1 day" of recovery


def test_early_session_leaves_full_window():
    acts = [_act("i1", "2025-06-01T07:00:00", 60)]
    r = _compute_last_session_end(acts, now=NOW)
    assert r["hoursSinceEnd"] == 24.0


def test_latest_END_wins_not_latest_start():
    # a long session starting earlier can still end later
    acts = [
        _act("long", "2025-06-01T16:00:00", 180),  # ends 19:00
        _act("short", "2025-06-01T18:00:00", 30),  # ends 18:30
    ]
    r = _compute_last_session_end(acts, now=NOW)
    assert r["activityId"] == "long"


def test_future_and_unparseable_entries_ignored():
    acts = [
        {"id": "bad", "start_date_local": "not-a-date", "moving_time": 60},
        _act("future", "2025-06-02T09:00:00", 60),  # after `now`
    ]
    assert _compute_last_session_end(acts, now=NOW) is None
    assert _compute_last_session_end([], now=NOW) is None


def test_missing_moving_time_treated_as_zero_duration():
    acts = [{"id": "i1", "start_date_local": "2025-06-01T20:00:00", "name": "x"}]
    r = _compute_last_session_end(acts, now=NOW)
    assert r["endLocal"] == "2025-06-01T20:00"
    assert r["hoursSinceEnd"] == 12.0
