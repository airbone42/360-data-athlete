"""Tests for the load→HRV slope-significance gate and the low_signal verdict.

When the personal load→HRV slope is statistically indistinguishable from 0 (its
95% CI includes 0), the regression carries no load-predictive signal. The
forecast must then declare "low_signal" instead of a confident
expected/needs_review verdict the planner would lean on, and the slope>0 sanity
warning must not fire on such noise. See framework/research/hrv-forecast-model.md.
"""
from __future__ import annotations

from datetime import date, timedelta
from math import isfinite

from app.graphs.sub_athlete_context.context_builder import (
    _build_hrv_sensitivity,
    _compute_hrv_responses,
    _slope_is_significant,
)

BASELINE = 60.0


def test_slope_significance_decision() -> None:
    assert _slope_is_significant(-0.20, 0.05) is True       # |t| = 4.0
    assert _slope_is_significant(0.0019, 0.0356) is False   # flat real-world case
    assert _slope_is_significant(0.10, float("inf")) is False
    assert _slope_is_significant(-0.10, 0.0) is True         # perfect fit, nonzero slope


def test_build_hrv_sensitivity_returns_finite_slope_se() -> None:
    """A noisy-but-real relationship → 4-tuple with finite, positive slope SE."""
    ref = date(2025, 6, 1)
    activities, wellness = [], []
    for back in range(1, 29):
        load = 120 if back % 2 == 0 else 0
        activities.append({
            "start_date_local": (ref - timedelta(days=back)).isoformat() + "T08:00:00",
            "icu_training_load": load,
        })
    for back in range(0, 29):
        load = 120 if (back + 1) % 2 == 0 else 0
        noise = 0.6 if back % 3 == 0 else -0.6
        wellness.append({
            "id": (ref - timedelta(days=back)).isoformat(),
            "hrv": BASELINE * (1 - 0.001 * load) + noise,
        })
    sens = _build_hrv_sensitivity(activities, wellness, BASELINE)
    assert sens is not None
    assert len(sens) == 4
    _intercept, _slope, _res_std, slope_se = sens
    assert isfinite(slope_se) and slope_se > 0


def _three_days(ref: date) -> tuple[list[dict], list[dict]]:
    """Three load days (loads 100/60/30) with their next-morning HRV."""
    spec = [(3, 100, 54.0), (2, 60, 57.0), (1, 30, 60.0)]
    acts, well = [], []
    for off, load, next_hrv in spec:
        acts.append({
            "start_date_local": (ref - timedelta(days=off)).isoformat() + "T08:00:00",
            "icu_training_load": load,
        })
        well.append({"id": (ref - timedelta(days=off - 1)).isoformat(), "hrv": next_hrv})
    return acts, well


def test_insignificant_slope_yields_low_signal() -> None:
    acts, well = _three_days(date(2025, 6, 10))
    insignificant = (0.87, 0.0019, 12.26, 0.0356)  # 95% CI includes 0
    resp = _compute_hrv_responses(acts, well, BASELINE, insignificant)
    assert resp
    assert all(r["verdict"] == "low_signal" for r in resp.values())


def test_significant_slope_yields_real_verdict() -> None:
    acts, well = _three_days(date(2025, 6, 10))
    significant = (0.0, -0.1, 2.0, 0.01)  # |t| = 10 → clearly significant
    resp = _compute_hrv_responses(acts, well, BASELINE, significant)
    assert resp
    assert all(r["verdict"] != "low_signal" for r in resp.values())
    assert {r["verdict"] for r in resp.values()} <= {"expected", "needs_review", "under_stimulus"}
