"""Tests for the Strava→intervals.icu shoe migration + the intervals backend.

All fixtures are synthetic (made-up gear ids / km), never real athlete data.
"""

from __future__ import annotations

import importlib

from scripts.migrate_shoes_strava_to_intervals import (
    plan_migration,
    shoe_to_gear_payload,
)
from app.graphs.shoe_advisor import (
    _compute_last_used,
    build_shoe_context,
    gear_to_shoes,
    profile_gear_key,
)


# ── shoe_to_gear_payload ────────────────────────────────────────────────────

def test_payload_converts_km_to_metres() -> None:
    payload = shoe_to_gear_payload({"name": "Demo Trainer", "distance_km": 123.4, "retired": False})
    assert payload["type"] == "Shoes"
    assert payload["name"] == "Demo Trainer"
    assert payload["distance"] == 123400  # km → m
    assert payload["retired"] is False


def test_payload_retired_flag() -> None:
    payload = shoe_to_gear_payload({"name": "Old Shoe", "distance_km": 0, "retired": True})
    assert payload["retired"] is True
    assert payload["distance"] == 0


# ── plan_migration ──────────────────────────────────────────────────────────

def _strava(name: str, km: float, retired: bool = False, sid: str = "g1") -> dict:
    return {"strava_id": sid, "name": name, "distance_km": km, "retired": retired}


def test_plan_creates_when_no_match() -> None:
    actions = plan_migration([_strava("Shoe A", 100)], existing_gear=[])
    assert len(actions) == 1
    assert actions[0]["action"] == "create"
    assert actions[0]["existing_id"] is None


def test_plan_matches_existing_by_name_case_insensitive() -> None:
    existing = [{"id": "b99", "type": "Shoes", "name": "shoe a"}]
    actions = plan_migration([_strava("Shoe A", 100)], existing)
    assert actions[0]["action"] == "update"
    assert actions[0]["existing_id"] == "b99"


def test_plan_ignores_non_shoe_gear() -> None:
    existing = [{"id": "bike1", "type": "Bike", "name": "Shoe A"}]
    actions = plan_migration([_strava("Shoe A", 100)], existing)
    # A bike named like the shoe must NOT be treated as a match.
    assert actions[0]["action"] == "create"


# ── gear_to_shoes ───────────────────────────────────────────────────────────

def test_gear_to_shoes_filters_and_converts() -> None:
    gear = [
        {"id": "b1", "type": "Shoes", "name": "Runner", "distance": 250000, "retired": False},
        {"id": "k9", "type": "Bike", "name": "Roadie", "distance": 9000000},
    ]
    shoes = gear_to_shoes(gear)
    assert len(shoes) == 1
    s = shoes[0]
    assert s["gear_key"] == "b1"
    assert s["strava_id"] == "b1"  # generic id alias
    assert s["distance_km"] == 250.0
    assert s["retired"] is False


# ── profile_gear_key ────────────────────────────────────────────────────────

def test_profile_gear_key_backend_selection() -> None:
    p = {"strava_id": "g5", "icu_gear_id": "b5"}
    assert profile_gear_key(p, "intervals") == "b5"
    assert profile_gear_key(p, "strava") == "g5"


def test_profile_gear_key_neutral_fallback() -> None:
    p = {"gear_id": "x7"}
    assert profile_gear_key(p, "intervals") == "x7"
    assert profile_gear_key(p, "strava") == "x7"


# ── build_shoe_context with intervals backend ───────────────────────────────

def test_build_context_joins_on_icu_gear_id() -> None:
    shoes = gear_to_shoes([
        {"id": "b100", "type": "Shoes", "name": "Tempo Demo", "distance": 100000, "retired": False},
    ])
    profiles = [{
        "icu_gear_id": "b100",
        "strava_id": "g100",
        "name": "Tempo Demo",
        "type": "tempo",
        "role": "daily",
        "terrain": "asphalt",
        "pace_range_min_km": [3.0, 4.5],
        "threshold_km": 600.0,
    }]
    planned = [{"type": "Run", "surface": "asphalt", "intensity": "z4", "workout_type": "WORKOUT"}]
    ctx = build_shoe_context(
        shoes=shoes,
        profiles=profiles,
        activities=[],
        planned_workouts=planned,
        weather_info="",
        race_in_days=None,
        today_str="2025-03-01",
        backend="intervals",
    )
    primary = ctx["shoeRecommendation"]["primary"]
    assert primary["gear_id"] == "b100"
    assert primary["name"] == "Tempo Demo"
    # enriched active shoe is keyed/joined correctly → type came from the profile
    assert ctx["shoes"][0]["type"] == "tempo"


# ── last-used reads the nested `gear` object (regression) ───────────────────

def test_compute_last_used_reads_nested_gear_object() -> None:
    """intervals.icu returns an assigned shoe as a nested `gear` object
    ({"id": ...}), NOT a flat `gear_id`. The rotation lookup must read the
    nested id, else every assigned activity is invisible to rotation."""
    activities = [
        {"start_date_local": "2025-03-01T09:00:00", "gear": {"id": "b100"}},
        {"start_date_local": "2025-03-03T09:00:00", "gear": {"id": "b200"}},
    ]
    last = _compute_last_used(activities)
    assert last["b100"] == "2025-03-01"
    assert last["b200"] == "2025-03-03"


def test_compute_last_used_flat_field_fallback() -> None:
    """Legacy / Strava-synced rows may still carry a flat gear_id."""
    activities = [
        {"start_date_local": "2025-03-01T09:00:00", "gear_id": "g100"},
        {"start_date_local": "2025-03-02T09:00:00", "icu_gear_id": "g200"},
        {"start_date_local": "2025-03-04T09:00:00", "gear": None},  # no gear → skipped
    ]
    last = _compute_last_used(activities)
    assert last["g100"] == "2025-03-01"
    assert last["g200"] == "2025-03-02"
    assert "None" not in last


# ── parser accepts icu_gear_id entry marker ─────────────────────────────────

def test_parser_accepts_icu_gear_id_marker(tmp_path, monkeypatch) -> None:
    import app.graphs.shoe_advisor as sa

    md = tmp_path / "equipment.md"
    md.write_text(
        "## Laufschuhe\n"
        "- icu_gear_id: b321\n"
        '  name: "Demo Long"\n'
        "  type: long\n"
        "  threshold_km: 900\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sa, "_equipment_md_path", lambda: md)
    profiles = sa.load_shoe_profiles()
    assert len(profiles) == 1
    assert profiles[0]["icu_gear_id"] == "b321"
    assert profiles[0]["name"] == "Demo Long"
    assert profile_gear_key(profiles[0], "intervals") == "b321"
