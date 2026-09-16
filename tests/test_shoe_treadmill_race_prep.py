"""A belt session does not open the race-prep window.

`_detect_terrain_from_context` collapses `treadmill` into the asphalt bucket,
which is correct for tread compound and grip: for those questions a belt
behaves like a firm even surface. It is wrong for the race-prep window, which
is not about tread at all — the window habituates the athlete to the race
**surface** and to the race shoe **at race pace**, and a belt supplies
neither. Before the guard, a race-pace session moved indoors still drew the
designated race shoe, spending its short life on the one session that cannot
use it, and stamping a `[coach-gear]` marker nobody would have chosen.

The two questions therefore get separate answers: terrain stays
asphalt-equivalent, and the prep window closes.
"""
from __future__ import annotations

from app.graphs.shoe_advisor import _is_treadmill, _score_shoe

_TODAY = "2026-09-16"


def _race_profile(**over) -> dict:
    base = {
        "gear_key": "iRACE1",
        "name": "Race Day Shoe",
        "role": "race",
        "terrain": "asphalt",
        "threshold_km": 400,
        "primary_race": True,
        "race_prep_days": 25,
        "recommended_tags": ["race", "intervals"],
    }
    base.update(over)
    return base


def _score(profile, *, indoor: bool, race_in_days: int | None = 25) -> float | None:
    shoe = {
        "gear_key": profile["gear_key"],
        "name": profile["name"],
        "distance_km": 42.0,
    }
    return _score_shoe(
        profile,
        shoe,
        "asphalt",
        False,
        None,
        race_in_days,
        _TODAY,
        {},
        workout_type="INTERVALS",
        workout_keys=["run", "intervals"],
        indoor=indoor,
    )


# ── _is_treadmill: both writers can declare a belt ────────────────────────


def test_surface_field_declares_a_belt() -> None:
    assert _is_treadmill({"surface": "treadmill"}) is True


def test_indoor_flag_declares_a_belt() -> None:
    """The planner writes `indoor`, the specialist writes `surface`."""
    assert _is_treadmill({"indoor": True}) is True
    assert _is_treadmill({"indoor": "true"}) is True


def test_outdoor_surfaces_are_not_a_belt() -> None:
    for surface in ("asphalt", "forest-path", "trail", "track"):
        assert _is_treadmill({"surface": surface}) is False
    assert _is_treadmill({}) is False


# ── The prep window closes on a belt ─────────────────────────────────────


def test_race_role_shoe_is_disqualified_indoors_inside_the_prep_window() -> None:
    """The hard filter: `role: race` only passes on a RACE workout or in the
    prep window, and a belt no longer counts as the latter."""
    assert _score(_race_profile(), indoor=True) is None


def test_same_shoe_still_passes_outdoors_inside_the_prep_window() -> None:
    assert _score(_race_profile(), indoor=False) is not None


def test_race_typed_workout_still_passes_indoors() -> None:
    """An actual race on a belt is a strange plan, but if it is prescribed the
    shoe is not the thing to argue about — the RACE path is untouched."""
    shoe = {"gear_key": "iRACE1", "name": "Race Day Shoe", "distance_km": 42.0}
    score = _score_shoe(
        _race_profile(),
        shoe,
        "asphalt",
        False,
        None,
        25,
        _TODAY,
        {},
        workout_type="RACE",
        workout_keys=["run", "race"],
        indoor=True,
    )
    assert score is not None


def test_primary_race_bonus_is_withheld_indoors() -> None:
    """A `role: daily` race shoe is not disqualified, so the +50 must go.

    This is the case that actually bit: the designated race shoe is kept on
    `role: daily` on purpose, so the hard filter never sees it and only the
    bonus decides. Indoors it has to lose to a rested trainer.
    """
    daily_race_shoe = _race_profile(role="daily")
    outdoor = _score(daily_race_shoe, indoor=False)
    indoor = _score(daily_race_shoe, indoor=True)
    assert outdoor is not None and indoor is not None
    assert outdoor - indoor == 50.0


def test_bonus_is_withheld_regardless_of_how_close_the_race_is() -> None:
    daily_race_shoe = _race_profile(role="daily")
    for days in (0, 1, 7, 25):
        outdoor = _score(daily_race_shoe, indoor=False, race_in_days=days)
        indoor = _score(daily_race_shoe, indoor=True, race_in_days=days)
        assert outdoor is not None and indoor is not None
        assert outdoor - indoor == 50.0, f"race_in_days={days}"


def test_outside_the_prep_window_indoor_changes_nothing() -> None:
    """The guard must not be a second, hidden penalty on ordinary sessions."""
    daily_race_shoe = _race_profile(role="daily")
    outdoor = _score(daily_race_shoe, indoor=False, race_in_days=99)
    indoor = _score(daily_race_shoe, indoor=True, race_in_days=99)
    assert outdoor == indoor
