"""Auto-balance push honours the athlete's configured weekly cadence."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import get_balance_rotation as gbr  # noqa: E402
import push_workouts as pw  # noqa: E402

_STATUS_3_PER_WEEK = "- **balance_sessions_per_week:** 3\n"


class _StubClient:
    def __init__(self, events=None):
        self._events = events or []

    async def get_events(self, start, end):  # noqa: D401
        return self._events


async def _fake_push(athlete_id, events, dry_run=False, date_str=None):
    return events


def _balance_event(date_str: str, name: str = "Balance A"):
    return {
        "start_date_local": f"{date_str}T06:00:00",
        "tags": ["balance"],
        "name": name,
    }


def _wire(monkeypatch, events, status: str, captured: dict):
    def fake_build(target_date, travel=False, leg_conflict=False, rotation=None):
        captured["called"] = True
        captured["rotation"] = rotation
        return rotation or "A", {
            "type": "Workout", "name": "stub", "tags": ["balance"], "description": "x",
        }

    monkeypatch.setattr(gbr, "build_rotation_workout", fake_build)
    monkeypatch.setattr(pw, "CachedIntervalsClient", lambda athlete_id=None: _StubClient(events))
    monkeypatch.setattr(pw, "_push", _fake_push)
    monkeypatch.setattr(pw, "prepare_workout_events", lambda workouts, date_str: [dict(w) for w in workouts])
    monkeypatch.setattr(pw, "_read_config", lambda path: status)


def test_no_config_keeps_pushing_daily(monkeypatch):
    """An athlete without the key sees the pre-existing behaviour."""
    captured: dict = {}
    _wire(monkeypatch, [_balance_event("2026-09-09")], "", captured)
    pw._auto_push_balance("2026-09-10", [], "athlete1")
    assert captured.get("called") is True


def test_budget_reached_skips_the_push(monkeypatch):
    captured: dict = {}
    events = [
        _balance_event("2026-09-04"),
        _balance_event("2026-09-06"),
        _balance_event("2026-09-08"),
    ]
    _wire(monkeypatch, events, _STATUS_3_PER_WEEK, captured)
    pw._auto_push_balance("2026-09-10", [], "athlete1")
    assert captured.get("called") is None


def test_within_budget_still_pushes(monkeypatch):
    captured: dict = {}
    _wire(monkeypatch, [_balance_event("2026-09-06")], _STATUS_3_PER_WEEK, captured)
    pw._auto_push_balance("2026-09-10", [], "athlete1")
    assert captured.get("called") is True


def test_same_day_event_still_wins_over_the_budget(monkeypatch):
    """Idempotency comes first: a re-push of the same day must fail on
    "already exists", never on the cadence budget."""
    captured: dict = {}
    _wire(monkeypatch, [_balance_event("2026-09-10")], _STATUS_3_PER_WEEK, captured)
    pw._auto_push_balance("2026-09-10", [], "athlete1")
    assert captured.get("called") is None


def test_rotation_steps_on_from_the_last_session(monkeypatch):
    """With a reduced cadence the date-based pick repeats keys; the push
    passes an explicitly stepped rotation instead."""
    captured: dict = {}
    pool_name = None
    import json
    with open(gbr._pool_path(), encoding="utf-8") as f:
        pool = json.load(f)
    pool_name = pool["sessions"]["B"]["name"]

    _wire(monkeypatch, [_balance_event("2026-09-06", name=pool_name)],
          _STATUS_3_PER_WEEK, captured)
    pw._auto_push_balance("2026-09-10", [], "athlete1")
    assert captured.get("rotation") == "C"


def test_balance_is_placed_before_the_earliest_session(monkeypatch):
    """Balance belongs on fresh legs. Both pushes start their own numbering
    at 06:00, so without the shift the two events collide on one minute."""
    captured: dict = {}
    day = [{"start_date_local": "2026-09-10T07:00:00", "tags": ["run"], "name": "Easy"}]
    _wire(monkeypatch, day, _STATUS_3_PER_WEEK, captured)

    pushed: dict = {}

    async def capture_push(athlete_id, events, dry_run=False, date_str=None):
        pushed["events"] = events
        return events

    monkeypatch.setattr(pw, "_push", capture_push)
    monkeypatch.setattr(
        pw, "prepare_workout_events",
        lambda workouts, date_str: [
            {**w, "start_date_local": f"{date_str}T06:00:00", "moving_time": 12 * 60}
            for w in workouts
        ],
    )
    pw._auto_push_balance("2026-09-10", [], "athlete1")
    assert pushed["events"][0]["start_date_local"] == "2026-09-10T06:33:00"
