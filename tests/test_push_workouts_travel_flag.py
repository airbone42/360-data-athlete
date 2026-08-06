"""Tests for `push_workouts.py --travel` forwarding to the auto-balance push.

Covers requirement (d) from the equipment-flag task: the CLI flag must
reach `build_rotation_workout` via `_auto_push_balance`, without requiring
a real network push. All intervals.icu I/O is mocked/stubbed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import push_workouts as pw  # noqa: E402
import get_balance_rotation as gbr  # noqa: E402
from app.utils import tracing as _tracing  # noqa: E402


class _StubSpan:
    def set_attribute(self, *a, **k):
        pass

    def set_status(self, *a, **k):
        pass


class _StubTracer:
    from contextlib import contextmanager as _cm

    @_cm
    def start_as_current_span(self, *a, **k):
        yield _StubSpan()


def _patch_tracing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid the optional `opentelemetry` dependency in `main()`'s
    `script_span()` — not part of this task, just a test-environment gap."""
    monkeypatch.setattr(_tracing, "get_tracer", lambda name: _StubTracer())


class _StubClient:
    """Minimal async stub of IntervalsClient — no existing events, no writes."""

    async def get_events(self, start, end):
        return []


async def _fake_push(athlete_id, events, dry_run, date_str):
    return [{"uid": "fake"}]


def test_auto_push_balance_forwards_travel_true(monkeypatch):
    captured: dict = {}

    def fake_build_rotation_workout(target_date, travel=False):
        captured["travel"] = travel
        return "A", {"type": "Workout", "name": "stub", "tags": ["balance"], "description": "x"}

    monkeypatch.setattr(gbr, "build_rotation_workout", fake_build_rotation_workout)
    monkeypatch.setattr(pw, "IntervalsClient", lambda athlete_id=None: _StubClient())
    monkeypatch.setattr(pw, "_push", _fake_push)
    monkeypatch.setattr(pw, "prepare_workout_events", lambda workouts, date_str: workouts)

    pw._auto_push_balance("2026-08-06", [], "athlete1", travel=True)
    assert captured["travel"] is True


def test_auto_push_balance_forwards_travel_false_by_default(monkeypatch):
    captured: dict = {}

    def fake_build_rotation_workout(target_date, travel=False):
        captured["travel"] = travel
        return "A", {"type": "Workout", "name": "stub", "tags": ["balance"], "description": "x"}

    monkeypatch.setattr(gbr, "build_rotation_workout", fake_build_rotation_workout)
    monkeypatch.setattr(pw, "IntervalsClient", lambda athlete_id=None: _StubClient())
    monkeypatch.setattr(pw, "_push", _fake_push)
    monkeypatch.setattr(pw, "prepare_workout_events", lambda workouts, date_str: workouts)

    pw._auto_push_balance("2026-08-06", [], "athlete1")
    assert captured["travel"] is False


def test_cli_parses_travel_flag(monkeypatch):
    """--travel and its --no-equipment alias both set args.travel True, and
    main() forwards it into `_auto_push_balance`. Every other side effect
    (validation, shoe enrichment, push, warmup/mental-coach warnings) is
    mocked out so this stays a pure argument-plumbing test."""
    captured_calls: list[bool] = []

    def fake_auto_push_balance(target_date, workouts, athlete_id, travel=False):
        captured_calls.append(travel)

    monkeypatch.setattr(pw, "_auto_push_balance", fake_auto_push_balance)
    monkeypatch.setattr(pw, "_warn_on_warmup_overlap", lambda *a, **k: None)
    monkeypatch.setattr(pw, "_warn_on_mental_coach_triggers", lambda *a, **k: None)
    monkeypatch.setattr(pw, "prepare_workout_events", lambda workouts, date_str: [])

    async def fake_push(athlete_id, events, dry_run, date_str):
        return []

    monkeypatch.setattr(pw, "_push", fake_push)
    _patch_tracing(monkeypatch)

    workouts_json = "[]"
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(workouts_json))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "push_workouts.py",
            "--date", "2026-08-06",
            "--skip-validation",
            "--no-shoes",
            "--travel",
        ],
    )

    pw.main()
    assert captured_calls == [True]


def test_cli_no_equipment_alias_sets_travel(monkeypatch):
    captured_calls: list[bool] = []

    def fake_auto_push_balance(target_date, workouts, athlete_id, travel=False):
        captured_calls.append(travel)

    monkeypatch.setattr(pw, "_auto_push_balance", fake_auto_push_balance)
    monkeypatch.setattr(pw, "_warn_on_warmup_overlap", lambda *a, **k: None)
    monkeypatch.setattr(pw, "_warn_on_mental_coach_triggers", lambda *a, **k: None)
    monkeypatch.setattr(pw, "prepare_workout_events", lambda workouts, date_str: [])

    async def fake_push(athlete_id, events, dry_run, date_str):
        return []

    monkeypatch.setattr(pw, "_push", fake_push)
    _patch_tracing(monkeypatch)

    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("[]"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "push_workouts.py",
            "--date", "2026-08-06",
            "--skip-validation",
            "--no-shoes",
            "--no-equipment",
        ],
    )

    pw.main()
    assert captured_calls == [True]


def test_cli_travel_defaults_off(monkeypatch):
    captured_calls: list[bool] = []

    def fake_auto_push_balance(target_date, workouts, athlete_id, travel=False):
        captured_calls.append(travel)

    monkeypatch.setattr(pw, "_auto_push_balance", fake_auto_push_balance)
    monkeypatch.setattr(pw, "_warn_on_warmup_overlap", lambda *a, **k: None)
    monkeypatch.setattr(pw, "_warn_on_mental_coach_triggers", lambda *a, **k: None)
    monkeypatch.setattr(pw, "prepare_workout_events", lambda workouts, date_str: [])

    async def fake_push(athlete_id, events, dry_run, date_str):
        return []

    monkeypatch.setattr(pw, "_push", fake_push)
    _patch_tracing(monkeypatch)

    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("[]"))
    monkeypatch.setattr(
        sys,
        "argv",
        ["push_workouts.py", "--date", "2026-08-06", "--skip-validation", "--no-shoes"],
    )

    pw.main()
    assert captured_calls == [False]
