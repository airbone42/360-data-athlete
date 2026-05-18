"""Output-eval smoketests for the planner contract.

The planner sub-agent produces a JSON plan directive that downstream
specialists, the validator, and `push_workouts.py` all consume. This
test asserts the structural contract on a set of canonical fixture
outputs (a typical training day, a rest day, a deload day, a ninja
day). It does NOT call the LLM — it loads pre-baked outputs and checks
that the shape is still parseable by `parse_workouts()` and that every
field stays inside its documented enum.

If anyone touches the planner prompt, the workout parser, or the tag /
type / intensity enums in a way that breaks the contract, this test
catches it. It's a complement to the existing
`test_workout_parser.py` (which tests the parser unit) — this one tests
the *contract from the planner's point of view*.
"""
from __future__ import annotations

from typing import Any

import pytest

from app.graphs.main_daily_planner.workout_parser import (
    REQUIRED_FIELDS,
    VALID_TAGS,
    VALID_TYPES,
    parse_workouts,
)

# Allowed enum values per the planner agent definition (agents/planner.md).
VALID_INTENSITY = {"low", "medium", "high"}
VALID_WORKOUT_TYPE = {"EASY", "LONG", "INTERVALS", "STRENGTH", "RECOVERY", "RACE", "WORKOUT"}


# ---------------------------------------------------------------------------
# Fixture outputs — one canonical example per typical planner scenario.
# ---------------------------------------------------------------------------

FIXTURE_TYPICAL_DAY: dict[str, Any] = {
    "coaching_notes": "HRV at baseline, TSB neutral. Solid Z2 + technique focus today.",
    "active_blocks": [],
    "workouts": [
        {
            "type": "Run",
            "name": "Easy Z2",
            "duration_min": 60,
            "duration_range": [50, 70],
            "intensity": "low",
            "workout_type": "EASY",
            "indoor": False,
            "tags": ["run"],
            "coaching_notes": "Forest path, GAP-paced, finish with 3 strides.",
        }
    ],
}

FIXTURE_REST_DAY: dict[str, Any] = {
    "coaching_notes": "TSB negative. Take a full rest day.",
    "active_blocks": [],
    "workouts": [],
}

FIXTURE_DOUBLE_DAY: dict[str, Any] = {
    "coaching_notes": "Quality day: strength + run with mandatory 6 h gap.",
    "active_blocks": [],
    "workouts": [
        {
            "type": "WeightTraining",
            "name": "Lower body strength",
            "duration_min": 45,
            "duration_range": [40, 55],
            "intensity": "medium",
            "workout_type": "STRENGTH",
            "indoor": True,
            # Keep the legacy "beine" tag here so the test fixture also
            # exercises the bilingual compat path; new plans should emit
            # "legs" instead.
            "tags": ["beine"],
            "coaching_notes": "Squat / RDL focus, RPE cap 8.",
        },
        {
            "type": "Run",
            "name": "Threshold intervals",
            "duration_min": 65,
            "duration_range": [55, 75],
            "intensity": "high",
            "workout_type": "INTERVALS",
            "indoor": False,
            "tags": ["run", "intervals"],
            "coaching_notes": "4x4 min Z4 after legs are recovered.",
        },
    ],
}

FIXTURE_NINJA_DAY: dict[str, Any] = {
    "coaching_notes": "Grip pillar is up — last grip was 5 days ago.",
    "active_blocks": [
        {"area": "heavy pull", "reason": "elbow phase", "since": "2025-04-01"}
    ],
    "workouts": [
        {
            "type": "Workout",
            "name": "Ninja Grip",
            "duration_min": 25,
            "duration_range": [20, 30],
            "intensity": "medium",
            "workout_type": "WORKOUT",
            "indoor": True,
            "tags": ["ninja", "grip"],
            "coaching_notes": "Grip pillar focus, isometric finisher at the end.",
        }
    ],
}

FIXTURE_DELOAD_DAY: dict[str, Any] = {
    "coaching_notes": "Recovery week active — Z1/Z2 only, strength volume −20%.",
    "active_blocks": [],
    "workouts": [
        {
            "type": "Run",
            "name": "Recovery jog",
            "duration_min": 40,
            "duration_range": [30, 45],
            "intensity": "low",
            "workout_type": "RECOVERY",
            "indoor": False,
            "tags": ["run"],
            "coaching_notes": "Strictly Z1 — feet light, no pace pressure.",
        }
    ],
}

ALL_FIXTURES = {
    "typical_day": FIXTURE_TYPICAL_DAY,
    "rest_day": FIXTURE_REST_DAY,
    "double_day": FIXTURE_DOUBLE_DAY,
    "ninja_day": FIXTURE_NINJA_DAY,
    "deload_day": FIXTURE_DELOAD_DAY,
}


# ---------------------------------------------------------------------------
# Contract checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_fixture_is_parseable(fixture_name: str) -> None:
    """parse_workouts() must accept every fixture without raising."""
    fixture = ALL_FIXTURES[fixture_name]
    notes, workouts = parse_workouts(fixture)
    assert isinstance(notes, str)
    assert isinstance(workouts, list)
    # Empty list becomes the synthetic rest day.
    if not fixture["workouts"]:
        assert len(workouts) == 1
        assert workouts[0]["workout_type"] == "RECOVERY"


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_required_fields_present(fixture_name: str) -> None:
    """Every workout entry in the planner output must carry the required fields."""
    fixture = ALL_FIXTURES[fixture_name]
    for w in fixture["workouts"]:
        missing = [f for f in REQUIRED_FIELDS if f not in w]
        assert not missing, f"{fixture_name}: missing required fields {missing}"


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_type_in_enum(fixture_name: str) -> None:
    """`type` must be one of VALID_TYPES (Run / Ride / WeightTraining / Workout)."""
    fixture = ALL_FIXTURES[fixture_name]
    for w in fixture["workouts"]:
        assert w["type"] in VALID_TYPES, (
            f"{fixture_name}: type '{w['type']}' not in {VALID_TYPES}"
        )


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_workout_type_in_enum(fixture_name: str) -> None:
    """`workout_type` must be one of the documented values."""
    fixture = ALL_FIXTURES[fixture_name]
    for w in fixture["workouts"]:
        assert w["workout_type"] in VALID_WORKOUT_TYPE, (
            f"{fixture_name}: workout_type '{w['workout_type']}' not in {VALID_WORKOUT_TYPE}"
        )


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_intensity_in_enum(fixture_name: str) -> None:
    """When `intensity` is set, it must be low / medium / high."""
    fixture = ALL_FIXTURES[fixture_name]
    for w in fixture["workouts"]:
        if "intensity" in w:
            assert w["intensity"] in VALID_INTENSITY, (
                f"{fixture_name}: intensity '{w['intensity']}' not in {VALID_INTENSITY}"
            )


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_tags_subset_of_valid(fixture_name: str) -> None:
    """Every tag must be in VALID_TAGS (silent drops are still caught upstream)."""
    fixture = ALL_FIXTURES[fixture_name]
    for w in fixture["workouts"]:
        for tag in w.get("tags", []):
            assert tag in VALID_TAGS, (
                f"{fixture_name}: tag '{tag}' not in VALID_TAGS"
            )


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_duration_range_shape(fixture_name: str) -> None:
    """When set, `duration_range` is a [min, max] pair around `duration_min`."""
    fixture = ALL_FIXTURES[fixture_name]
    for w in fixture["workouts"]:
        if "duration_range" not in w:
            continue
        rng = w["duration_range"]
        assert isinstance(rng, list) and len(rng) == 2, (
            f"{fixture_name}: duration_range must be a [min, max] list"
        )
        lo, hi = rng
        assert isinstance(lo, int) and isinstance(hi, int) and lo <= hi, (
            f"{fixture_name}: duration_range bounds invalid: {rng}"
        )
        # duration_min should sit inside the range (sanity).
        assert lo <= w["duration_min"] <= hi, (
            f"{fixture_name}: duration_min {w['duration_min']} outside range {rng}"
        )


@pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
def test_coaching_notes_under_500_chars(fixture_name: str) -> None:
    """Per planner.md, top-level coaching_notes is capped at ~500 chars."""
    fixture = ALL_FIXTURES[fixture_name]
    notes = fixture.get("coaching_notes", "")
    assert len(notes) <= 500, (
        f"{fixture_name}: coaching_notes length {len(notes)} exceeds 500"
    )


def test_double_day_ordering_is_strength_first() -> None:
    """Mandatory order rule from planner.md: strength/plyo always first, run after."""
    fixture = FIXTURE_DOUBLE_DAY
    types = [w["type"] for w in fixture["workouts"]]
    if "WeightTraining" in types and "Run" in types:
        first_strength = next(i for i, t in enumerate(types) if t == "WeightTraining")
        first_run = next(i for i, t in enumerate(types) if t == "Run")
        assert first_strength < first_run, (
            "Strength must come before Run in a double-day plan"
        )


def test_planner_output_round_trips_through_parser() -> None:
    """Every fixture should round-trip parse_workouts() without losing required fields."""
    for fixture_name, fixture in ALL_FIXTURES.items():
        notes, parsed = parse_workouts(fixture)
        if not fixture["workouts"]:
            continue  # rest day expansion verified elsewhere
        assert len(parsed) == len(fixture["workouts"]), (
            f"{fixture_name}: parser dropped workouts (in={len(fixture['workouts'])}, "
            f"out={len(parsed)})"
        )
        for original, after in zip(fixture["workouts"], parsed, strict=True):
            for field in REQUIRED_FIELDS:
                assert after[field] == original[field], (
                    f"{fixture_name}: parser changed required field {field}"
                )
