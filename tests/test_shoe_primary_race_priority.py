"""Tests for the primary-race priority bonus in `_score_shoe`.

Rationale: during the race-prep window the designated race shoe
(`primary_race: true`) is deliberately habituated in race-pace / quality
sessions. Without a priority bonus, the rotation-freshness bonus (up to
+28) can hand such a slot to a fresher daily trainer whose
`recommended_tags` also match — inverting the habituation intent. The
bonus (+50) applies only when

- the profile is `primary_race`,
- the workout's descriptor keys intersect the shoe's `recommended_tags`,
- and the workout is RACE-typed OR `race_in_days` is inside
  `race_prep_days` (inclusive).

Easy sessions (no tag match) keep rotating normally.
"""
from __future__ import annotations

from app.graphs.shoe_advisor import _score_shoe

_TODAY = "2025-03-15"


def _profile(**over) -> dict:
    base = {
        "gear_key": "iRACE1",
        "name": "Race Day Shoe",
        "role": "race",
        "terrain": "asphalt",
        "threshold_km": 400,
        "primary_race": True,
        "race_prep_days": 21,
        "recommended_tags": ["race", "intervals"],
    }
    base.update(over)
    return base


def _daily_profile(**over) -> dict:
    base = {
        "gear_key": "iDAILY1",
        "name": "Fresh Daily Trainer",
        "role": "daily",
        "terrain": "asphalt",
        "threshold_km": 500,
        "recommended_tags": ["intervals", "tempo"],
    }
    base.update(over)
    return base


def _score(profile, *, workout_type="", race_in_days=None, keys=None, last_used=None):
    shoe = {"gear_key": profile["gear_key"], "name": profile["name"], "distance_km": 50.0}
    return _score_shoe(
        profile,
        shoe,
        "asphalt",
        False,
        None,
        race_in_days,
        _TODAY,
        last_used or {},
        workout_type=workout_type,
        workout_keys=keys or [],
    )


def test_primary_race_beats_fresher_daily_inside_prep_window():
    # Race shoe worn 9 days ago (+18 rotation), daily never seen (+28).
    # Without the priority bonus the daily wins; with it the race shoe must.
    race_score = _score(
        _profile(),
        workout_type="INTERVALS",
        race_in_days=13,
        keys=["run", "intervals", "high"],
        last_used={"iRACE1": "2025-03-06"},
    )
    daily_score = _score(
        _daily_profile(),
        workout_type="INTERVALS",
        race_in_days=13,
        keys=["run", "intervals", "high"],
    )
    assert race_score is not None and daily_score is not None
    assert race_score > daily_score


def test_no_bonus_without_tag_match_easy_sessions_keep_rotating():
    # Same shoe, easy-run descriptors: eligible (window) but no tag match,
    # so only the rotation bonus applies — no +50.
    with_match = _score(
        _profile(),
        workout_type="INTERVALS",
        race_in_days=13,
        keys=["intervals"],
        last_used={"iRACE1": "2025-03-06"},
    )
    without_match = _score(
        _profile(),
        race_in_days=13,
        keys=["run", "easy"],
        last_used={"iRACE1": "2025-03-06"},
    )
    assert with_match is not None and without_match is not None
    # +50 priority and +6 tag nudge are both tied to the tag match
    assert with_match - without_match == 56.0


def test_no_bonus_for_non_primary_race_shoe():
    plain = _profile(primary_race=False)
    primary = _profile()
    plain_score = _score(
        plain, workout_type="INTERVALS", race_in_days=13, keys=["intervals"]
    )
    primary_score = _score(
        primary, workout_type="INTERVALS", race_in_days=13, keys=["intervals"]
    )
    assert plain_score is not None and primary_score is not None
    assert primary_score - plain_score == 50.0


def test_bonus_applies_on_race_typed_workout_outside_window():
    # RACE-typed workout with race_in_days unknown: eligibility comes from
    # the RACE type, and so does the priority bonus.
    score_race_type = _score(
        _profile(), workout_type="RACE", race_in_days=None, keys=["race"]
    )
    assert score_race_type is not None
    baseline = _score(
        _profile(primary_race=False),
        workout_type="RACE",
        race_in_days=None,
        keys=["race"],
    )
    assert baseline is not None
    assert score_race_type - baseline == 50.0


def test_prep_window_boundary_inclusive_for_bonus():
    at_boundary = _score(
        _profile(race_prep_days=13),
        workout_type="INTERVALS",
        race_in_days=13,
        keys=["intervals"],
    )
    assert at_boundary is not None
    non_primary = _score(
        _profile(race_prep_days=13, primary_race=False),
        workout_type="INTERVALS",
        race_in_days=13,
        keys=["intervals"],
    )
    assert non_primary is not None
    assert at_boundary - non_primary == 50.0
