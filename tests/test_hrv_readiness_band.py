"""Tests for the 7d-rolling ln-rMSSD vs 60d-band readiness classifier.

Replaces the retired load→HRV regression tests. Covers band membership, the
causal (no look-ahead) reference, consecutive-day watch/hold counting, the
insufficient_data fallback, gaps/coverage, hrv guards, the advisory CV trend,
the band-based review-pending trigger, and intensity_readiness wiring.

Synthetic fixtures use 2025 dates (public-repo athlete-agnostic rule). Several
band tests pass ``roll_days=1`` so the 7-day smoothing collapses to the daily
value, giving exact control over consecutive-day counts; the 7-day rolling math
and causal guarantee are tested separately with the default window.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from app.graphs.sub_athlete_context.context_builder import (
    _compute_hrv_cv_trend,
    _compute_hrv_readiness_band,
    _compute_intensity_readiness,
    _find_pending_hrv_review,
)

REF = date(2025, 6, 30)


def _iso(back: int) -> str:
    return (REF - timedelta(days=back)).isoformat()


def _series(overrides: dict[int, float | None] | None = None, days: int = 60) -> list[dict]:
    """60-day wellness series ~50 ms with two spread days (offsets 30/31) so the
    band has a non-zero SD. ``overrides`` maps offset→hrv; value ``None`` omits
    that day (a gap)."""
    overrides = overrides or {}
    out: list[dict] = []
    for back in range(0, days):
        if back in overrides:
            v = overrides[back]
            if v is None:
                continue
        elif back == 30:
            v = 41.0
        elif back == 31:
            v = 61.0
        else:
            v = 50.0
        out.append({"id": _iso(back), "hrv": float(v)})
    return out


# ── Band membership ────────────────────────────────────────────────


def test_clear_inside_band() -> None:
    res = _compute_hrv_readiness_band(_series(), REF)
    assert res["verdict"] == "clear"
    assert res["days_below"] == 0
    assert res["n_ref"] == 60


def test_above_band() -> None:
    res = _compute_hrv_readiness_band(_series({i: 65.0 for i in range(0, 7)}), REF)
    assert res["verdict"] == "above"
    assert res["days_below"] == 0


def test_sustained_drop_is_hold() -> None:
    res = _compute_hrv_readiness_band(_series({i: 40.0 for i in range(0, 12)}), REF)
    assert res["verdict"] == "hold"
    assert res["days_below"] >= 3


# ── Consecutive-day counting (roll_days=1 → exact daily control) ───


def test_one_day_below_is_watch() -> None:
    res = _compute_hrv_readiness_band(
        _series({0: 45.0}), REF, roll_days=1, min_coverage_roll=1
    )
    assert res["verdict"] == "watch"
    assert res["days_below"] == 1


def test_two_days_below_is_watch() -> None:
    res = _compute_hrv_readiness_band(
        _series({0: 45.0, 1: 45.0}), REF, roll_days=1, min_coverage_roll=1
    )
    assert res["verdict"] == "watch"
    assert res["days_below"] == 2


def test_three_consecutive_below_is_hold() -> None:
    res = _compute_hrv_readiness_band(
        _series({0: 45.0, 1: 45.0, 2: 45.0}), REF, roll_days=1, min_coverage_roll=1
    )
    assert res["verdict"] == "hold"
    assert res["days_below"] == 3


def test_gap_breaks_the_streak() -> None:
    # below today & -1, -2 MISSING, -3 below → gap stops the count at 2.
    res = _compute_hrv_readiness_band(
        _series({0: 45.0, 1: 45.0, 2: None, 3: 45.0}),
        REF,
        roll_days=1,
        min_coverage_roll=1,
    )
    assert res["verdict"] == "watch"
    assert res["days_below"] == 2


# ── 7-day rolling math + causal guarantee ──────────────────────────


def test_rolling_mean_is_geometric_over_seven_days() -> None:
    vals = [50.0, 52.0, 48.0, 51.0, 49.0, 53.0, 47.0]
    res = _compute_hrv_readiness_band(
        _series({i: vals[i] for i in range(7)}), REF
    )
    expected = math.exp(sum(math.log(v) for v in vals) / len(vals))
    assert res["rolling_mean_ms"] == pytest.approx(expected, abs=0.1)


def test_no_look_ahead_future_days_ignored() -> None:
    base = _series()
    with_future = base + [
        {"id": (REF + timedelta(days=k)).isoformat(), "hrv": 200.0} for k in (1, 2, 3)
    ]
    assert _compute_hrv_readiness_band(with_future, REF) == _compute_hrv_readiness_band(base, REF)


def test_back_transform_matches_ln_band() -> None:
    res = _compute_hrv_readiness_band(_series(), REF)
    assert res["band_low_ms"] == pytest.approx(round(math.exp(res["band_low_ln"]), 1))
    assert res["band_high_ms"] == pytest.approx(round(math.exp(res["band_high_ln"]), 1))


# ── insufficient_data + coverage ───────────────────────────────────


def test_insufficient_data_below_threshold() -> None:
    res = _compute_hrv_readiness_band(_series(days=25), REF)
    assert res["verdict"] == "insufficient_data"
    assert res["n_ref"] == 25
    assert res["rolling_mean_ms"] is None
    assert res["cv_trend"] is not None


def test_exactly_thirty_values_classifies() -> None:
    res = _compute_hrv_readiness_band(_series(days=30), REF)
    assert res["verdict"] != "insufficient_data"
    assert res["n_ref"] == 30


# ── hrv guards ─────────────────────────────────────────────────────


def test_nonpositive_and_none_hrv_excluded() -> None:
    res = _compute_hrv_readiness_band(
        _series({0: 0.0, 1: -5.0, 2: None}), REF
    )
    # offsets 0/1 (≤0) and 2 (missing) drop out; the remaining valid days
    # (all ~50) keep the rolling mean inside the band — no crash.
    assert res["verdict"] == "clear"


# ── advisory CV trend ──────────────────────────────────────────────


def _cv_series(recent: list[float], prior: list[float]) -> list[dict]:
    out = [{"id": _iso(i), "hrv": v} for i, v in enumerate(recent)]
    out += [{"id": _iso(7 + i), "hrv": v} for i, v in enumerate(prior)]
    return out


def test_cv_trend_rising() -> None:
    res = _compute_hrv_cv_trend(
        _cv_series([35, 65, 35, 65, 35, 65, 35], [49, 51, 49, 51, 49, 51, 49]), REF
    )
    assert res["trend"] == "rising"


def test_cv_trend_falling() -> None:
    res = _compute_hrv_cv_trend(
        _cv_series([49, 51, 49, 51, 49, 51, 49], [35, 65, 35, 65, 35, 65, 35]), REF
    )
    assert res["trend"] == "falling"


def test_cv_trend_stable() -> None:
    res = _compute_hrv_cv_trend(
        _cv_series([49, 51, 49, 51, 49, 51, 49], [49, 51, 49, 51, 49, 51, 49]), REF
    )
    assert res["trend"] == "stable"


def test_cv_trend_insufficient() -> None:
    res = _compute_hrv_cv_trend(_cv_series([50, 50, 50], [50, 50, 50, 50]), REF)
    assert res["trend"] == "insufficient_data"


# ── band-based review-pending trigger ──────────────────────────────


def test_review_pending_on_watch_without_note() -> None:
    band = {"verdict": "watch", "days_below": 1, "rolling_mean_ms": 47.0,
            "band_low_ms": 49.0, "band_high_ms": 55.0}
    pending = _find_pending_hrv_review(band, [], REF)
    assert pending is not None
    assert pending["verdict"] == "watch"
    assert pending["days_below"] == 1


def test_review_suppressed_by_hrv_review_note_in_window() -> None:
    band = {"verdict": "hold", "days_below": 3}
    notes = [{"start_date_local": _iso(0), "description": "HRV-Review 2025-06-30: schlecht geschlafen", "name": ""}]
    assert _find_pending_hrv_review(band, notes, REF) is None


def test_review_not_suppressed_by_note_outside_window() -> None:
    band = {"verdict": "watch", "days_below": 1}
    notes = [{"start_date_local": _iso(5), "description": "HRV-Review 2025-06-25: ok", "name": ""}]
    assert _find_pending_hrv_review(band, notes, REF) is not None


def test_review_none_when_band_clear_or_missing() -> None:
    assert _find_pending_hrv_review({"verdict": "clear"}, [], REF) is None
    assert _find_pending_hrv_review({"verdict": "above"}, [], REF) is None
    assert _find_pending_hrv_review({"verdict": "insufficient_data"}, [], REF) is None
    assert _find_pending_hrv_review(None, [], REF) is None


# ── intensity_readiness wiring ─────────────────────────────────────


def test_intensity_band_hold_is_red() -> None:
    r = _compute_intensity_readiness(
        50.0, "50", 0.0, 3, None, None, {"verdict": "hold", "days_below": 3}
    )
    assert "🔴" in r and "hold" in r


def test_intensity_band_watch_is_yellow() -> None:
    r = _compute_intensity_readiness(
        50.0, "50", 0.0, 3, None, None, {"verdict": "watch", "days_below": 2}
    )
    assert "🟡" in r and "watch" in r


def test_intensity_combined_deload_outranks_band_hold() -> None:
    r = _compute_intensity_readiness(
        50.0, "50", 0.0, 3, None,
        {"verdict": "deload", "days": 3}, {"verdict": "hold", "days_below": 3},
    )
    assert "🔴" in r and "combined" in r


def test_intensity_band_clear_stays_green() -> None:
    r = _compute_intensity_readiness(
        50.0, "50", 0.0, 3, None, None, {"verdict": "clear"}
    )
    assert "🟢" in r
