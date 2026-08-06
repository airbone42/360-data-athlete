"""Parity tests — context-time shoe recommendation vs. push-time pick.

The intervals.icu event dict returned by ``get_events`` does NOT carry the
coach's ``surface`` / ``workout_type`` / ``intensity`` / ``coaching_notes``
fields — even though ``push_workouts`` sent them at push time. Without a
reconstruction step, the context path fed the advisor a bare event dict and
the terrain filter defaulted to "asphalt" while the pace bucket returned
None, so a LONG run silently kept tempo-only shoes in the running and could
pick a different shoe than the push path did.

These tests pin the two mechanisms that close the divergence:

  1. ``[coach-plan:surface=…,workout_type=…,intensity=…]`` marker parsing —
     re-hydrates the same inputs the push received, so the advisor's own
     scoring converges.

  2. ``[coach-gear:<id>]`` marker SSOT — for legacy events (marker (1)
     absent), the pinned shoe is promoted to primary directly, so context
     agrees with push even without input recovery.

All fixtures are synthetic (invented gear ids, no real athlete equipment).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.graphs import shoe_advisor
from app.graphs.shoe_advisor import (
    _compute_last_used,
    build_shoe_context,
    gear_to_shoes,
    load_shoe_profiles,
    profile_gear_key,
)
from app.graphs.sub_athlete_context.context_builder import (
    _apply_coach_gear_ssot,
    _build_shoe_planned_workouts,
    _parse_coach_gear_marker,
    _parse_coach_plan_marker,
)


# Two-shoe fleet: one tempo-only shoe with a narrow fast pace range, one
# long-range daily. Same terrain (asphalt). The LONG-run pace bucket
# (4.8-7.0 min/km) has 0.2 overlap with the tempo range (3.5-5.0 min/km) —
# below the 50 % overlap threshold — so a correctly-filtered advisor
# disqualifies the tempo shoe.
_EQUIP_MD = """# Equipment

## Laufschuhe

- icu_gear_id: gLONG
  name: "Long Daily"
  type: easy
  role: daily
  terrain: asphalt
  pace_range_min_km: [4.5, 6.5]
  recommended_tags: [easy, long]
  threshold_km: 800

- icu_gear_id: gTEMPO
  name: "Tempo Only"
  type: tempo
  role: daily
  terrain: asphalt
  pace_range_min_km: [3.5, 5.0]
  recommended_tags: [tempo, intervals]
  threshold_km: 700
"""


@pytest.fixture()
def _equipment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "equipment.md"
    p.write_text(_EQUIP_MD, encoding="utf-8")
    monkeypatch.setattr(shoe_advisor, "_equipment_md_path", lambda: p)


# ── Marker parsers ────────────────────────────────────────────────────

def test_parse_coach_plan_marker_extracts_whitelisted_keys() -> None:
    desc = (
        "some plan text\n"
        "[coach-plan:surface=trail,workout_type=LONG,intensity=low]\n"
    )
    assert _parse_coach_plan_marker(desc) == {
        "surface": "trail",
        "workout_type": "LONG",
        "intensity": "low",
    }


def test_parse_coach_plan_marker_ignores_unknown_keys() -> None:
    # Unknown keys must not leak through — the advisor should never see
    # an unexpected field on the planned-workout dict.
    desc = "[coach-plan:surface=asphalt,foo=bar,workout_type=EASY]"
    assert _parse_coach_plan_marker(desc) == {
        "surface": "asphalt",
        "workout_type": "EASY",
    }


def test_parse_coach_plan_marker_absent_returns_empty() -> None:
    assert _parse_coach_plan_marker("nothing here") == {}
    assert _parse_coach_plan_marker(None) == {}


def test_parse_coach_gear_marker_extracts_id() -> None:
    desc = "Shoe recommendation: Foo Trainer\n[coach-gear:gABC123]"
    assert _parse_coach_gear_marker(desc) == "gABC123"


def test_parse_coach_gear_marker_absent_returns_none() -> None:
    assert _parse_coach_gear_marker("plain description") is None
    assert _parse_coach_gear_marker(None) is None


# ── Planned-workout builder — field-recovery from marker ─────────────

def test_builder_recovers_marker_fields_for_today_run() -> None:
    events = [
        {
            "id": 1,
            "type": "Run",
            "start_date_local": "2025-04-10T08:00:00",
            "tags": ["run"],
            "description": (
                "Warmup … Main …\n"
                "[coach-plan:surface=asphalt,workout_type=LONG,intensity=low]"
            ),
        },
    ]
    planned = _build_shoe_planned_workouts(events, "2025-04-10")
    assert planned == [
        {
            "type": "Run",
            "tags": ["run"],
            "surface": "asphalt",
            "workout_type": "LONG",
            "intensity": "low",
            "coaching_notes": "",
        }
    ]


def test_builder_leaves_fields_empty_without_marker() -> None:
    # An event without any coach markers must not manufacture defaults —
    # empty strings encode "unknown" for the downstream advisor.
    events = [
        {
            "id": 2,
            "type": "Run",
            "start_date_local": "2025-04-10T08:00:00",
            "tags": ["run"],
            "description": "Some plain description with the word Wald in it.",
        },
    ]
    planned = _build_shoe_planned_workouts(events, "2025-04-10")
    assert len(planned) == 1
    assert planned[0]["surface"] == ""
    assert planned[0]["workout_type"] == ""
    assert planned[0]["intensity"] == ""
    assert planned[0]["coaching_notes"] == ""


def test_builder_carries_coach_gear_id_when_present() -> None:
    events = [
        {
            "id": 3,
            "type": "Run",
            "start_date_local": "2025-04-10T08:00:00",
            "tags": ["run"],
            "description": "…\n[coach-gear:gPICKED]",
        },
    ]
    planned = _build_shoe_planned_workouts(events, "2025-04-10")
    assert planned[0]["_coach_gear_id"] == "gPICKED"


def test_builder_skips_non_run_and_non_today() -> None:
    events = [
        {"id": 10, "type": "Ride", "start_date_local": "2025-04-10T08:00:00"},
        {"id": 11, "type": "Run", "start_date_local": "2025-04-09T08:00:00"},
    ]
    assert _build_shoe_planned_workouts(events, "2025-04-10") == []


# ── End-to-end: context path picks the same shoe as push path ──────────

_TODAY = "2025-04-10"


def _push_time_workout_dict(workout_type: str) -> dict:
    """Full-fidelity dict as ``shoe_recommend`` receives it from stdin."""
    return {
        "type": "Run",
        "tags": ["run"],
        "surface": "asphalt",
        "workout_type": workout_type,
        "intensity": "low",
        "coaching_notes": "",
    }


def _shoes() -> list[dict]:
    return [
        {"gear_key": "gLONG", "name": "Long Daily", "distance_km": 200},
        {"gear_key": "gTEMPO", "name": "Tempo Only", "distance_km": 100},
    ]


def test_marker_reconstruction_matches_push_on_long_run(
    _equipment: None
) -> None:
    """The context path (event → marker parse → advisor) must pick the same
    shoe as the push path (workout dict → advisor) for a LONG run."""
    # Push path: the advisor receives the full workout dict directly.
    push_ctx = build_shoe_context(
        shoes=[dict(s) for s in _shoes()],
        profiles=load_shoe_profiles(),
        activities=[],
        planned_workouts=[_push_time_workout_dict("LONG")],
        weather_info="",
        race_in_days=None,
        today_str=_TODAY,
        backend="intervals",
    )
    push_pick = push_ctx["shoeRecommendation"]["primary"]["gear_id"]
    assert push_pick == "gLONG"  # tempo shoe was disqualified on pace overlap

    # Context path: only the intervals.icu event dict (fields dropped)
    # plus the coach-plan marker on the description.
    events = [
        {
            "id": 100,
            "type": "Run",
            "start_date_local": f"{_TODAY}T08:00:00",
            "tags": ["run"],
            "description": (
                "Warmup … Main …\n"
                "[coach-plan:surface=asphalt,workout_type=LONG,intensity=low]"
            ),
        },
    ]
    planned_from_marker = _build_shoe_planned_workouts(events, _TODAY)
    ctx_ctx = build_shoe_context(
        shoes=[dict(s) for s in _shoes()],
        profiles=load_shoe_profiles(),
        activities=[],
        planned_workouts=planned_from_marker,
        weather_info="",
        race_in_days=None,
        today_str=_TODAY,
        backend="intervals",
    )
    assert ctx_ctx["shoeRecommendation"]["primary"]["gear_id"] == push_pick


def test_context_without_marker_diverges_from_push_on_long_run(
    _equipment: None
) -> None:
    """Regression pin: without any recovery, the context path leaves surface
    empty / workout_type empty / intensity empty — the terrain filter still
    accepts both shoes and pace_bucket becomes None, so both shoes qualify.
    The picked shoe is not guaranteed to equal the push pick. This test
    documents the pre-fix behaviour so future changes to the empty-input
    handling stay intentional (currently: tempo wins on the ``pct_used``
    tiebreak because it has less mileage)."""
    events = [
        {
            "id": 200,
            "type": "Run",
            "start_date_local": f"{_TODAY}T08:00:00",
            "tags": ["run"],
            "description": "no markers at all",
        },
    ]
    planned = _build_shoe_planned_workouts(events, _TODAY)
    assert planned[0]["workout_type"] == ""  # nothing to filter on
    ctx = build_shoe_context(
        shoes=[dict(s) for s in _shoes()],
        profiles=load_shoe_profiles(),
        activities=[],
        planned_workouts=planned,
        weather_info="",
        race_in_days=None,
        today_str=_TODAY,
        backend="intervals",
    )
    primary = ctx["shoeRecommendation"]["primary"]["gear_id"]
    # Without pace-filter, both are eligible; tie-break on less mileage picks
    # the tempo shoe — NOT what push would pick on a LONG run. This is why
    # the SSOT backstop below matters for legacy events.
    assert primary == "gTEMPO"


def test_coach_gear_ssot_overrides_diverging_advisor_pick(
    _equipment: None
) -> None:
    """Legacy event with only ``[coach-gear:…]`` (no coach-plan): the SSOT
    must promote the pinned shoe to primary so context converges on push."""
    events = [
        {
            "id": 300,
            "type": "Run",
            "start_date_local": f"{_TODAY}T08:00:00",
            "tags": ["run"],
            "description": "no plan marker\n[coach-gear:gLONG]",
        },
    ]
    planned = _build_shoe_planned_workouts(events, _TODAY)
    assert planned[0]["_coach_gear_id"] == "gLONG"
    ctx = build_shoe_context(
        shoes=[dict(s) for s in _shoes()],
        profiles=load_shoe_profiles(),
        activities=[],
        planned_workouts=planned,
        weather_info="",
        race_in_days=None,
        today_str=_TODAY,
        backend="intervals",
    )
    # Advisor without recovered inputs would pick the tempo shoe (see the
    # divergence pin above); SSOT flips it back to the pinned long shoe.
    assert ctx["shoeRecommendation"]["primary"]["gear_id"] == "gTEMPO"
    ctx_after = _apply_coach_gear_ssot(ctx, planned)
    assert ctx_after["shoeRecommendation"]["primary"]["gear_id"] == "gLONG"
    # Previously-picked primary demoted to alternative — read side still sees
    # a runner-up.
    assert ctx_after["shoeRecommendation"]["alternative"]["gear_id"] == "gTEMPO"


def test_coach_gear_ssot_noop_when_pinned_shoe_missing(
    _equipment: None
) -> None:
    """Pin references a shoe not in the active fleet (retired, migrated,
    travel-subset excluded): SSOT stays silent, advisor's pick stands."""
    ctx = build_shoe_context(
        shoes=[dict(s) for s in _shoes()],
        profiles=load_shoe_profiles(),
        activities=[],
        planned_workouts=[_push_time_workout_dict("LONG")],
        weather_info="",
        race_in_days=None,
        today_str=_TODAY,
        backend="intervals",
    )
    original_primary = ctx["shoeRecommendation"]["primary"]["gear_id"]
    ctx_after = _apply_coach_gear_ssot(
        ctx,
        [{"type": "Run", "_coach_gear_id": "gNOT_IN_FLEET"}],
    )
    assert ctx_after["shoeRecommendation"]["primary"]["gear_id"] == original_primary


def test_coach_gear_ssot_noop_when_advisor_already_agrees(
    _equipment: None
) -> None:
    """Advisor already picked the pinned shoe — SSOT does nothing, no
    duplicate demotion into alternative."""
    ctx = build_shoe_context(
        shoes=[dict(s) for s in _shoes()],
        profiles=load_shoe_profiles(),
        activities=[],
        planned_workouts=[_push_time_workout_dict("LONG")],
        weather_info="",
        race_in_days=None,
        today_str=_TODAY,
        backend="intervals",
    )
    before = ctx["shoeRecommendation"]
    ctx_after = _apply_coach_gear_ssot(
        ctx, [{"type": "Run", "_coach_gear_id": "gLONG"}]
    )
    assert ctx_after["shoeRecommendation"] == before


# ── gear_to_shoes ─────────────────────────────────────────────────────────────

def test_gear_to_shoes_filters_and_converts() -> None:
    gear = [
        {"id": "b1", "type": "Shoes", "name": "Runner", "distance": 250000, "retired": False},
        {"id": "k9", "type": "Bike", "name": "Roadie", "distance": 9000000},
    ]
    shoes = gear_to_shoes(gear)
    assert len(shoes) == 1
    s = shoes[0]
    assert s["gear_key"] == "b1"
    assert "strava_id" not in s  # strava backend removed
    assert s["distance_km"] == 250.0
    assert s["retired"] is False


# ── profile_gear_key ──────────────────────────────────────────────────────────

def test_profile_gear_key_icu_gear_id() -> None:
    p = {"icu_gear_id": "b5", "gear_id": "x5"}
    # icu_gear_id wins over neutral gear_id; backend param is ignored
    assert profile_gear_key(p, "intervals") == "b5"
    assert profile_gear_key(p, "strava") == "b5"


def test_profile_gear_key_neutral_fallback() -> None:
    p = {"gear_id": "x7"}
    assert profile_gear_key(p, "intervals") == "x7"
    assert profile_gear_key(p, "strava") == "x7"


# ── build_shoe_context with intervals backend ─────────────────────────────────

def test_build_context_joins_on_icu_gear_id() -> None:
    shoes = gear_to_shoes([
        {"id": "b100", "type": "Shoes", "name": "Tempo Demo", "distance": 100000, "retired": False},
    ])
    profiles = [{
        "icu_gear_id": "b100",
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
    assert ctx["shoes"][0]["type"] == "tempo"


# ── _compute_last_used ────────────────────────────────────────────────────────

def test_compute_last_used_reads_nested_gear_object() -> None:
    """intervals.icu returns an assigned shoe as a nested `gear` object."""
    activities = [
        {"start_date_local": "2025-03-01T09:00:00", "gear": {"id": "b100"}},
        {"start_date_local": "2025-03-03T09:00:00", "gear": {"id": "b200"}},
    ]
    last = _compute_last_used(activities)
    assert last["b100"] == "2025-03-01"
    assert last["b200"] == "2025-03-03"


def test_compute_last_used_flat_field_fallback() -> None:
    """Legacy rows may still carry a flat gear_id."""
    activities = [
        {"start_date_local": "2025-03-01T09:00:00", "gear_id": "g100"},
        {"start_date_local": "2025-03-02T09:00:00", "icu_gear_id": "g200"},
        {"start_date_local": "2025-03-04T09:00:00", "gear": None},  # no gear → skipped
    ]
    last = _compute_last_used(activities)
    assert last["g100"] == "2025-03-01"
    assert last["g200"] == "2025-03-02"
    assert "None" not in last


# ── load_shoe_profiles: icu_gear_id marker ─────────────────────────────────────

def test_parser_accepts_icu_gear_id_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    md = tmp_path / "equipment.md"
    md.write_text(
        "## Laufschuhe\n"
        "- icu_gear_id: b321\n"
        '  name: "Demo Long"\n'
        "  type: long\n"
        "  threshold_km: 900\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(shoe_advisor, "_equipment_md_path", lambda: md)
    profiles = load_shoe_profiles()
    assert len(profiles) == 1
    assert profiles[0]["icu_gear_id"] == "b321"
    assert profiles[0]["name"] == "Demo Long"
    assert profile_gear_key(profiles[0], "intervals") == "b321"
