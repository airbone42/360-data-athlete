"""Smoke tests for workout_parser.parse_workouts()."""
from __future__ import annotations

import pytest

from app.graphs.main_daily_planner.workout_parser import (
    REQUIRED_FIELDS,
    VALID_TAGS,
    VALID_TYPES,
    VALID_WORKOUT_TYPES,
    parse_workouts,
    prepare_workout_events,
)

_MINIMAL = {
    "type": "Run",
    "name": "Testlauf",
    "duration_min": 45,
    "workout_type": "EASY",
}


def _full(**overrides: object) -> dict:
    return {**_MINIMAL, **overrides}


# ---------------------------------------------------------------------------
# Valid inputs
# ---------------------------------------------------------------------------


def test_dict_with_workouts_key() -> None:
    notes, ws = parse_workouts({"coaching_notes": "gut", "workouts": [_full()]})
    assert notes == "gut"
    assert len(ws) == 1
    assert ws[0]["type"] == "Run"


def test_bare_list() -> None:
    notes, ws = parse_workouts([_full(), _full(type="Ride", name="Rad")])
    assert notes == ""
    assert len(ws) == 2


def test_empty_list_returns_rest_day() -> None:
    _, ws = parse_workouts([])
    assert len(ws) == 1
    assert ws[0]["workout_type"] == "RECOVERY"


def test_all_valid_types() -> None:
    for t in VALID_TYPES:
        _, ws = parse_workouts([_full(type=t)])
        assert ws[0]["type"] == t


# ---------------------------------------------------------------------------
# Tag filtering
# ---------------------------------------------------------------------------


def test_valid_tags_kept() -> None:
    _, ws = parse_workouts([_full(tags=["core", "plyo"])])
    assert set(ws[0]["tags"]) == {"core", "plyo"}


def test_legs_and_beine_both_accepted() -> None:
    """Bilingual compat during the beine → legs migration: both forms parse."""
    _, ws_legs = parse_workouts([_full(tags=["legs"])])
    assert "legs" in ws_legs[0]["tags"]
    _, ws_beine = parse_workouts([_full(tags=["beine"])])
    assert "beine" in ws_beine[0]["tags"]


def test_invalid_tags_dropped(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    with caplog.at_level(logging.WARNING):
        _, ws = parse_workouts([_full(tags=["core", "bogustag"])])
    assert "bogustag" not in ws[0]["tags"]
    assert "bogustag" in caplog.text


def test_valid_tags_constant_complete() -> None:
    expected = {"run", "ride", "core", "legs", "beine", "plyo", "balance",
                "mobility", "intervals", "ninja", "grip", "upperbody"}
    assert VALID_TAGS == expected


# ---------------------------------------------------------------------------
# Missing REQUIRED_FIELDS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
def test_missing_required_field_raises(missing_field: str) -> None:
    bad = {k: v for k, v in _MINIMAL.items() if k != missing_field}
    with pytest.raises(ValueError, match=missing_field):
        parse_workouts([bad])


# ---------------------------------------------------------------------------
# Invalid type
# ---------------------------------------------------------------------------


def test_invalid_type_raises() -> None:
    with pytest.raises(ValueError, match="invalid type"):
        parse_workouts([_full(type="Swim")])


# ---------------------------------------------------------------------------
# workout_type — soft validation (warn, never reject)
# ---------------------------------------------------------------------------


def test_workout_type_enum_complete() -> None:
    assert VALID_WORKOUT_TYPES == {
        "EASY", "LONG", "INTERVALS", "STRENGTH", "RECOVERY", "RACE",
    }


@pytest.mark.parametrize("wt", sorted(VALID_WORKOUT_TYPES))
def test_known_workout_types_pass_silently(
    wt: str, caplog: pytest.LogCaptureFixture
) -> None:
    import logging
    with caplog.at_level(logging.WARNING):
        _, ws = parse_workouts([_full(workout_type=wt)])
    assert ws[0]["workout_type"] == wt
    assert "unknown workout_type" not in caplog.text


def test_unknown_workout_type_warns_but_keeps(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Legacy values (e.g. "WORKOUT") must not be rejected — soft validation
    only logs a warning and the value is passed through unchanged."""
    import logging
    with caplog.at_level(logging.WARNING):
        _, ws = parse_workouts([_full(workout_type="WORKOUT")])
    assert ws[0]["workout_type"] == "WORKOUT"
    assert "unknown workout_type" in caplog.text


# ---------------------------------------------------------------------------
# prepare_workout_events — workout_doc payload shape
# ---------------------------------------------------------------------------


def test_endurance_event_has_no_workout_doc() -> None:
    """Run/Ride events must not carry workout_doc.

    intervals.icu parses the description (intervals_icu syntax) server-side
    and writes the resulting structured steps into workout_doc itself —
    Garmin sync then reads those steps. A pre-populated workout_doc
    (even just {"locales": []}) is treated as authoritative and suppresses
    the parsing, leaving Garmin with a single "Run Until Lap Press" step.
    Regression guard for the 2026-05-19 → 2026-05-22 incident.
    """
    for endurance_type in ("Run", "Ride"):
        events = prepare_workout_events(
            [
                {
                    "type": endurance_type,
                    "name": "Testlauf",
                    "duration_min": 45,
                    "workout_type": "EASY",
                    "intensity": "Z2",
                    "intervals_icu": "Warmup\n- Easy 5m press lap\n\nMain\n- 30m 76-84% LTHR\n\nCool-down\n- Cool-down 5m press lap",
                }
            ],
            date="2026-01-01",
        )
        assert len(events) == 1
        assert "workout_doc" not in events[0], (
            f"{endurance_type} event must not pre-populate workout_doc"
        )


def test_non_endurance_event_has_workout_doc_with_locales() -> None:
    """WeightTraining / Workout events keep explicit workout_doc with locales=[]
    to suppress intervals.icu's language-detection heuristic (Tss! → ja)."""
    events = prepare_workout_events(
        [
            {
                "type": "WeightTraining",
                "name": "Ninja",
                "duration_min": 45,
                "workout_type": "WORKOUT",
                "intensity": "medium",
                "structure": [],
                "description": "Some text",
            }
        ],
        date="2026-01-01",
    )
    assert len(events) == 1
    doc = events[0].get("workout_doc")
    assert doc is not None
    assert doc.get("locales") == []


def test_complementary_split_blocks_are_adjacent() -> None:
    """A per-focus complementary split (e.g. shoulder / core / grip) carries
    no interference gap — the blocks are scheduled back-to-back so they read
    as one slot the athlete can work through or partially complete."""
    events = prepare_workout_events(
        [
            {"type": "Workout", "name": "Schulter", "duration_min": 15,
             "workout_type": "WORKOUT", "tags": ["upperbody"]},
            {"type": "Workout", "name": "Core", "duration_min": 15,
             "workout_type": "WORKOUT", "tags": ["core"]},
            {"type": "Workout", "name": "Grip", "duration_min": 10,
             "workout_type": "WORKOUT", "tags": ["grip"]},
        ],
        date="2026-01-01",
    )
    starts = [e["start_date_local"] for e in events]
    # 06:00 → +15m → 06:15 → +15m → 06:30 (no 2h interference gap stacked in)
    assert starts == [
        "2026-01-01T06:00:00",
        "2026-01-01T06:15:00",
        "2026-01-01T06:30:00",
    ]


def test_strength_to_run_keeps_interference_gap() -> None:
    """Strength → Run still gets the 3h (no leg tags) interference gap —
    the adjacency rule only applies between two non-endurance blocks."""
    events = prepare_workout_events(
        [
            {"type": "Workout", "name": "Grip", "duration_min": 20,
             "workout_type": "WORKOUT", "tags": ["grip"]},
            {"type": "Run", "name": "Easy", "duration_min": 40,
             "workout_type": "EASY", "intensity": "Z2"},
        ],
        date="2026-01-01",
    )
    starts = sorted(e["start_date_local"] for e in events)
    # 06:00 strength → +20m +180m gap → 09:20 run
    assert starts == ["2026-01-01T06:00:00", "2026-01-01T09:20:00"]


# ---------------------------------------------------------------------------
# Ordering: the session that carries the adaptation goes first
# ---------------------------------------------------------------------------


def test_quality_run_goes_before_strength() -> None:
    """A quality endurance session takes the first slot, strength follows 6h later.

    Running economy is degraded after leg strength, and the effect bites
    hardest above ~85 % VO2max — exactly where an INTERVALS session lives.
    The paradigms file used to demand strength-first unconditionally, which
    contradicted the framework's own research.
    """
    events = prepare_workout_events(
        [
            {"type": "WeightTraining", "name": "Bein-Kraft", "duration_min": 45,
             "workout_type": "STRENGTH", "tags": ["legs"]},
            {"type": "Run", "name": "HM-Pace", "duration_min": 70,
             "workout_type": "INTERVALS", "tags": ["run", "intervals"]},
        ],
        date="2026-01-01",
    )
    by_name = {e["name"]: e["start_date_local"] for e in events}
    assert by_name["HM-Pace"] == "2026-01-01T06:00:00"
    # 06:00 + 70min run + 360min gap = 13:10
    assert by_name["Bein-Kraft"] == "2026-01-01T13:10:00"


def test_intervals_tag_alone_marks_a_quality_run() -> None:
    """The `intervals` tag qualifies even without workout_type INTERVALS —
    a race-pace block inside a long run carries the tag, not the type."""
    events = prepare_workout_events(
        [
            {"type": "WeightTraining", "name": "Kraft", "duration_min": 30,
             "workout_type": "STRENGTH", "tags": ["legs"]},
            {"type": "Run", "name": "Long mit HM-Pace", "duration_min": 100,
             "workout_type": "LONG", "tags": ["run", "intervals"]},
        ],
        date="2026-01-01",
    )
    assert events[0]["name"] == "Long mit HM-Pace"


def test_easy_run_keeps_strength_first() -> None:
    """Below the economy-sensitive intensity the old order stands: strength
    first, run after the leg-spacing gap. A Z2 run on pre-loaded legs is a
    deliberate stimulus, not an accident."""
    events = prepare_workout_events(
        [
            {"type": "Run", "name": "Easy Z2", "duration_min": 60,
             "workout_type": "EASY", "tags": ["run"]},
            {"type": "WeightTraining", "name": "Bein-Kraft", "duration_min": 45,
             "workout_type": "STRENGTH", "tags": ["legs"]},
        ],
        date="2026-01-01",
    )
    by_name = {e["name"]: e["start_date_local"] for e in events}
    assert by_name["Bein-Kraft"] == "2026-01-01T06:00:00"
    assert by_name["Easy Z2"] == "2026-01-01T12:45:00"
