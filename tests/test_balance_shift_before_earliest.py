"""Balance placement ahead of the day's earliest session (push_workouts)."""

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "push_workouts", Path(__file__).resolve().parents[1] / "scripts" / "push_workouts.py"
)
push_workouts = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(push_workouts)


def _balance():
    return [{"start_date_local": "2026-10-13T06:00:00", "moving_time": 720}]


def test_shifts_before_earliest_workout():
    events = _balance()
    today = [{"category": "WORKOUT", "start_date_local": "2026-10-13T09:30:00"}]
    push_workouts._shift_before_earliest(events, today)
    assert events[0]["start_date_local"] == "2026-10-13T09:03:00"


def test_day_note_at_midnight_is_ignored():
    events = _balance()
    today = [
        {"category": "NOTE", "start_date_local": "2026-10-13T00:00:00"},
        {"category": "WORKOUT", "start_date_local": "2026-10-13T09:30:00"},
    ]
    push_workouts._shift_before_earliest(events, today)
    assert events[0]["start_date_local"] == "2026-10-13T09:03:00"


def test_only_note_leaves_slot_untouched():
    events = _balance()
    today = [{"category": "NOTE", "start_date_local": "2026-10-13T00:00:00"}]
    push_workouts._shift_before_earliest(events, today)
    assert events[0]["start_date_local"] == "2026-10-13T06:00:00"


def test_never_crosses_into_previous_day():
    events = _balance()
    today = [{"category": "WORKOUT", "start_date_local": "2026-10-13T00:10:00"}]
    push_workouts._shift_before_earliest(events, today)
    assert events[0]["start_date_local"] == "2026-10-13T06:00:00"
