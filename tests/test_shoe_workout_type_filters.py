"""Tests for the workout-type levers in the shoe advisor's scoring.

Covers `excluded_workout_types` (hard filter) and `recommended_tags`
(soft bonus), plus the shared descriptor vocabulary both read from.
All fixture data is synthetic.
"""
from __future__ import annotations

from app.graphs.shoe_advisor import _score_shoe, _workout_keys

_TODAY = "2025-03-15"


def _profile(**over) -> dict:
    base = {
        "gear_key": "iAAA111",
        "name": "Synthetic Trainer",
        "role": "daily",
        "terrain": "asphalt",
        "threshold_km": 800,
    }
    base.update(over)
    return base


def _shoe(**over) -> dict:
    base = {"gear_key": "iAAA111", "name": "Synthetic Trainer", "distance_km": 100.0}
    base.update(over)
    return base


def _score(profile, *, workout, last_used=None):
    return _score_shoe(
        profile,
        _shoe(gear_key=profile["gear_key"]),
        "asphalt",
        False,
        None,
        None,
        _TODAY,
        last_used or {},
        workout_type=workout.get("workout_type", ""),
        workout_keys=_workout_keys(workout),
    )


def test_workout_keys_collects_tags_intensity_and_type():
    keys = _workout_keys(
        {"tags": ["Run", "Intervals"], "intensity": "Z4", "workout_type": "LONG"}
    )
    assert keys == ["run", "intervals", "z4", "long"]
    # Empty descriptors are dropped rather than yielding blank keys that would
    # accidentally match an empty profile entry.
    assert _workout_keys({"tags": [], "intensity": "", "workout_type": ""}) == []


def test_excluded_workout_type_disqualifies_via_workout_type():
    profile = _profile(excluded_workout_types=["long"])
    assert _score(profile, workout={"workout_type": "LONG", "tags": ["run"]}) is None


def test_excluded_workout_type_disqualifies_via_tag():
    """The term may arrive as a tag rather than as workout_type."""
    profile = _profile(excluded_workout_types=["long"])
    assert _score(profile, workout={"tags": ["run", "long"]}) is None


def test_excluded_workout_type_accepts_string_form():
    """Profiles are parsed from markdown, so a bare string must work too."""
    profile = _profile(excluded_workout_types="long, race")
    assert _score(profile, workout={"workout_type": "RACE"}) is None


def test_excluded_workout_type_leaves_other_sessions_untouched():
    profile = _profile(excluded_workout_types=["long"])
    score = _score(profile, workout={"workout_type": "EASY", "tags": ["run"]})
    assert score is not None


def test_recommended_tags_add_a_bonus_when_they_match():
    matching = _profile(recommended_tags=["easy"])
    neutral = _profile(recommended_tags=["intervals"])
    workout = {"workout_type": "EASY", "tags": ["run"]}
    assert _score(matching, workout=workout) > _score(neutral, workout=workout)


def test_recommended_tags_do_not_override_the_rotation_intent():
    """A tag match is a tie-breaker, never a reason to re-wear a fresh shoe.

    The rested shoe carries no matching tag; the recently-worn one does. The
    rested shoe must still win, or the advisor stops being a rotation advisor.
    """
    rested = _profile(gear_key="iRESTED", recommended_tags=["intervals"])
    just_worn = _profile(gear_key="iWORN", recommended_tags=["easy"])
    workout = {"workout_type": "EASY", "tags": ["run"]}
    last_used = {"iWORN": _TODAY}  # worn today -> zero rotation bonus
    rested_score = _score(rested, workout=workout, last_used=last_used)
    worn_score = _score(just_worn, workout=workout, last_used=last_used)
    assert rested_score > worn_score
