"""Tests for scripts/set_activity_gear.py.

Covers the two behaviours added after the shoe-tracking migration:

1. Idempotency must ignore a *phantom* gear — a retired / non-shoe / unknown
   gear id (e.g. a stale auto-default an importer stamps onto every activity).
   Only an active Shoes-type gear blocks auto-correction.
2. The advisor recommendation for a finished activity must read terrain from
   the *paired planned event* (the completed activity carries no surface and
   an empty description), so the analysis pick matches the push-time pick.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import set_activity_gear as sag  # noqa: E402


class _FakeIcu:
    """Minimal async stub of IntervalsClient for the gear-setter."""

    def __init__(self, *, activity: dict, gear: list[dict], event: dict | None = None):
        self._activity = activity
        self._gear = gear
        self._event = event or {}
        self.set_calls: list[tuple[str, str | None]] = []

    async def get_activity(self, activity_id: str) -> dict:
        return self._activity

    async def list_gear(self) -> list[dict]:
        return self._gear

    async def get_event(self, event_id: str) -> dict:
        return self._event

    async def get_activities(self, oldest: str, newest: str) -> list[dict]:
        return []

    async def set_activity_gear(self, activity_id: str, gear_id: str | None) -> dict:
        self.set_calls.append((activity_id, gear_id))
        return {"gear": {"id": gear_id}}


def _run_with(monkeyclient: _FakeIcu, **kwargs) -> None:
    orig = sag.IntervalsClient
    sag.IntervalsClient = lambda: monkeyclient  # type: ignore[assignment]
    try:
        asyncio.run(sag._run(**kwargs))
    finally:
        sag.IntervalsClient = orig  # type: ignore[assignment]


def test_active_shoe_blocks_overwrite():
    """An already-assigned active shoe is left untouched (idempotent)."""
    icu = _FakeIcu(
        activity={"type": "Run", "gear": {"id": "g_active"}},
        gear=[{"id": "g_active", "type": "Shoes", "retired": None}],
    )
    _run_with(icu, activity_id="i1", gear_id="g_new", auto=False, dry_run=False, force=False)
    assert icu.set_calls == [], "active shoe must not be overwritten without --force"


def test_retired_phantom_is_overwritten():
    """A retired gear id (phantom auto-default) does not block assignment."""
    icu = _FakeIcu(
        activity={"type": "Run", "gear": {"id": "g_phantom"}},
        gear=[{"id": "g_phantom", "type": "Shoes", "retired": "2026-06-02"}],
    )
    _run_with(icu, activity_id="i1", gear_id="g_new", auto=False, dry_run=False, force=False)
    assert icu.set_calls == [("i1", "g_new")], "retired phantom must be replaced"


def test_unknown_gear_id_is_overwritten():
    """A gear id not present in the gear list (unknown phantom) is replaced."""
    icu = _FakeIcu(
        activity={"type": "Run", "gear": {"id": "g_ghost"}},
        gear=[{"id": "g_active", "type": "Shoes", "retired": None}],
    )
    _run_with(icu, activity_id="i1", gear_id="g_new", auto=False, dry_run=False, force=False)
    assert icu.set_calls == [("i1", "g_new")], "unknown gear id must be replaced"


def test_gear_from_planned_marker():
    """The machine [coach-gear:<id>] marker is read directly."""
    plan = {"description": "Main\n- Trail 30m\n\nShoe recommendation: On Cloudeclipse (323 km)\n[coach-gear:g_on]"}
    gear = [{"id": "g_on", "type": "Shoes", "name": "On Cloudeclipse", "retired": None}]
    gid, _ = sag._gear_from_planned_event(plan, gear)
    assert gid == "g_on"


def test_gear_from_planned_marker_retired_falls_through():
    """A marker pointing at a retired shoe is ignored (→ re-derive)."""
    plan = {"description": "Shoe recommendation: Old Shoe (900 km)\n[coach-gear:g_old]"}
    gear = [{"id": "g_old", "type": "Shoes", "name": "Old Shoe", "retired": "2026-06-02"}]
    gid, _ = sag._gear_from_planned_event(plan, gear)
    assert gid is None


def test_gear_from_planned_name_fallback():
    """Legacy footer without a marker → resolve via the shoe name."""
    plan = {"description": "Shoe recommendation: On Cloudeclipse (323 km) — 11 days unused"}
    gear = [{"id": "g_on", "type": "Shoes", "name": "On Cloudeclipse", "retired": None}]
    gid, _ = sag._gear_from_planned_event(plan, gear)
    assert gid == "g_on"


def test_gear_from_planned_none():
    """No recommendation in the description → None (caller re-derives)."""
    plan = {"description": "Warmup\n- Easy 6m press lap\n\nMain\n- Trail 30m Z2 HR"}
    gear = [{"id": "g_on", "type": "Shoes", "name": "On Cloudeclipse", "retired": None}]
    gid, _ = sag._gear_from_planned_event(plan, gear)
    assert gid is None


def test_auto_uses_persisted_marker_not_rederive(monkeypatch):
    """--auto must use the persisted push-time pick and skip re-derivation."""
    called = {"rederive": False}

    async def _no_rederive(*a, **k):
        called["rederive"] = True
        return {"gear_id": "g_wrong", "name": "Wrong"}

    monkeypatch.setattr(sag, "_recommend_gear_for_activity", _no_rederive)
    icu = _FakeIcu(
        activity={"type": "Run", "gear": None, "paired_event_id": 1},
        gear=[{"id": "g_on", "type": "Shoes", "name": "On Cloudeclipse", "retired": None}],
        event={"description": "Shoe recommendation: On Cloudeclipse (323 km)\n[coach-gear:g_on]"},
    )
    _run_with(icu, activity_id="i1", gear_id=None, auto=True, dry_run=False, force=False)
    assert icu.set_calls == [("i1", "g_on")]
    assert called["rederive"] is False, "must not re-derive when a persisted pick exists"


def test_recommendation_reads_paired_event_terrain(monkeypatch):
    """_recommend_gear_for_activity must feed the advisor the planned event's
    description (terrain keywords), not the empty completed-activity fields."""
    captured: dict = {}

    def _fake_build_shoe_context(**kwargs):
        captured["planned"] = kwargs.get("planned_workouts")
        return {"shoeRecommendation": {"primary": {"gear_id": "g_trail", "name": "Trail Shoe"}}}

    monkeypatch.setattr(sag, "build_shoe_context", _fake_build_shoe_context)
    monkeypatch.setattr(sag, "gear_to_shoes", lambda gear: [])
    monkeypatch.setattr(sag, "load_shoe_profiles", lambda: {})

    icu = _FakeIcu(
        activity={
            "type": "Run",
            "surface": None,
            "description": "",          # completed activity: empty
            "tags": ["run", "legs"],
            "paired_event_id": 999,
            "start_date_local": "2026-06-03T08:00:00",
        },
        gear=[],
        event={                         # planned event carries the terrain wording
            "type": "Run",
            "description": "Warmup\n- Easy 6m press lap\n\nMain\n- Trail 30m Z2 HR",
            "tags": ["run", "legs"],
            "workout_type": "EASY",
            "intensity": "low",
        },
    )
    primary = asyncio.run(sag._recommend_gear_for_activity(icu, icu._activity))
    assert primary and primary["gear_id"] == "g_trail"
    planned = captured["planned"][0]
    assert "Trail" in planned["coaching_notes"], "must use paired-event description"
