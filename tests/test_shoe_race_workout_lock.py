"""Tests for the race-day shoe lock (P5-4, tasks.md).

`_score_shoe`'s `role == "race"` branch computes a local `is_race_workout`
flag (historically factored out as a `_is_race_workout` helper) that gates
whether a race-role shoe is even eligible for a given workout. P0-4 (see
tasks.md) found and fixed a bug where the flag read
`profile.get("workout_type")` — a key that never exists on a shoe profile —
instead of the incoming `workout_type` argument (the workout actually being
scored), so the flag was always `False` and the race lock only ever fired
via the `race_in_days <= race_prep_days` prep-window branch, never via an
actual RACE-typed workout.

These tests pin the current (correct) contract:
- a race-role shoe is eligible when the workout's `workout_type` is "RACE"
  (case-insensitive), OR when `race_in_days` falls inside `race_prep_days`
  (inclusive boundary);
- otherwise it is disqualified (`_score_shoe` returns None);
- the lock only applies to `role == "race"` profiles.
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
    }
    base.update(over)
    return base


def _shoe(**over) -> dict:
    base = {"gear_key": "iRACE1", "name": "Race Day Shoe", "distance_km": 50.0}
    base.update(over)
    return base


def _score(profile, *, workout_type="", race_in_days=None):
    return _score_shoe(
        profile,
        _shoe(gear_key=profile["gear_key"]),
        "asphalt",
        False,
        None,
        race_in_days,
        _TODAY,
        {},
        workout_type=workout_type,
    )


def test_race_shoe_available_for_race_workout_type():
    profile = _profile()
    assert _score(profile, workout_type="RACE") is not None


def test_race_shoe_disqualified_for_non_race_non_prep_workout():
    profile = _profile()
    assert _score(profile, workout_type="EASY", race_in_days=None) is None


def test_race_shoe_available_inside_prep_window():
    profile = _profile(race_prep_days=7)
    assert _score(profile, workout_type="EASY", race_in_days=5) is not None


def test_race_shoe_disqualified_outside_prep_window():
    profile = _profile(race_prep_days=7)
    assert _score(profile, workout_type="EASY", race_in_days=8) is None


def test_race_shoe_prep_window_boundary_is_inclusive():
    profile = _profile(race_prep_days=7)
    assert _score(profile, workout_type="EASY", race_in_days=7) is not None


def test_race_shoe_workout_type_match_is_case_insensitive():
    profile = _profile()
    assert _score(profile, workout_type="race") is not None
    assert _score(profile, workout_type="Race") is not None


def test_race_shoe_disqualified_with_no_race_in_days_and_wrong_type():
    """race_in_days=None must not accidentally satisfy the prep-window check."""
    profile = _profile(race_prep_days=7)
    assert _score(profile, workout_type="LONG", race_in_days=None) is None


def test_non_race_role_ignores_the_race_lock_entirely():
    """A daily-role shoe is never gated by workout_type via the race lock —
    the branch simply must not fire for role != 'race'."""
    profile = _profile(role="daily")
    assert _score(profile, workout_type="EASY", race_in_days=None) is not None
