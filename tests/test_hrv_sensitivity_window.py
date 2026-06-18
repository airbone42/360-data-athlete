"""Regression tests for the activity-window constraint in _build_hrv_sensitivity.

The wellness history handed to the sensitivity regression may reach further
back than the activities window (fetch_context: 90d wellness vs. 4w
activities). Days outside the activity coverage are unknown — NOT rest days —
and must not enter the regression as phantom load=0 points: they dilute the
slope and inflate the residual stddev, widening the ±1.5σ review band until
real "needs_review" deviations classify as "expected".
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.graphs.sub_athlete_context.context_builder import _build_hrv_sensitivity

REF = date(2025, 6, 1)
BASELINE = 60.0


def _iso(days_back: int) -> str:
    return (REF - timedelta(days=days_back)).isoformat()


def _window_data() -> tuple[list[dict], list[dict]]:
    """28-day activity window: even offsets train (load 100), odd offsets rest.

    Next-morning HRV: 54 ms after a load day (−10%), 60 ms after a rest day
    (0%) — a perfect line delta = 0 − 0.1·load with zero residuals.
    """
    activities = [
        {"start_date_local": _iso(back) + "T08:00:00", "icu_training_load": 100}
        for back in range(1, 29)
        if back % 2 == 0
    ]
    wellness = []
    for back in range(0, 28):
        hrv = 54.0 if (back + 1) % 2 == 0 else 60.0
        wellness.append({"id": _iso(back), "hrv": hrv})
    return activities, wellness


def test_perfect_fit_inside_activity_window() -> None:
    activities, wellness = _window_data()
    sens = _build_hrv_sensitivity(activities, wellness, BASELINE)
    assert sens is not None
    intercept, slope, res_std, slope_se = sens
    assert intercept == pytest.approx(0.0, abs=1e-9)
    assert slope == pytest.approx(-0.1, abs=1e-9)
    assert res_std == pytest.approx(0.0, abs=1e-9)
    assert slope_se == pytest.approx(0.0, abs=1e-9)  # perfect fit → zero SE


def test_wellness_outside_activity_window_is_not_a_rest_day() -> None:
    """A wellness day 60 days back (outside a 4-week activity window) must
    NOT enter the regression with load=0."""
    activities, wellness = _window_data()
    # Wellness reaches 60-75 days back with strongly elevated HRV — if these
    # days entered as load=0 "rest" pairs (delta +50%), the intercept would
    # be pulled up and the residual stddev would explode.
    phantom = [{"id": _iso(back), "hrv": 90.0} for back in range(60, 76)]

    sens_with_phantom = _build_hrv_sensitivity(activities, wellness + phantom, BASELINE)
    sens_window_only = _build_hrv_sensitivity(activities, wellness, BASELINE)

    assert sens_with_phantom == sens_window_only
    assert sens_with_phantom is not None
    intercept, _slope, res_std, _slope_se = sens_with_phantom
    assert intercept == pytest.approx(0.0, abs=1e-9)
    assert res_std == pytest.approx(0.0, abs=1e-9)


def test_no_activities_returns_none() -> None:
    _, wellness = _window_data()
    assert _build_hrv_sensitivity([], wellness, BASELINE) is None
