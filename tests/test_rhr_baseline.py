"""Unit tests for RHR baseline + combined HRV/RHR overload signal.

Covers the long-window RHR baseline (90d-median) and the combined-overload
trigger documented in ``framework/research/hrv-rhr-baseline-methodology.md``
(Buchheit 2014 + RunnersConnect overtraining review).
"""
from __future__ import annotations

from datetime import date, timedelta

from app.graphs.sub_athlete_context.context_builder import (
    _compute_combined_overload_signal,
    _compute_rhr_baseline,
)


def _wellness(today: date, days: int, hrv: float | None, rhr: float | None) -> dict:
    return {
        "id": (today - timedelta(days=days)).isoformat(),
        "hrv": hrv,
        "restingHR": rhr,
    }


# ── RHR baseline ────────────────────────────────────────────────────


def test_rhr_baseline_returns_dash_when_no_history() -> None:
    today = date(2025, 5, 28)
    baseline, deviation, ctx = _compute_rhr_baseline([], 44.0, today)
    assert baseline == "-"
    assert deviation is None
    assert ctx == "44.0 bpm"


def test_rhr_baseline_returns_dash_when_rhr_none() -> None:
    today = date(2025, 5, 28)
    history = [_wellness(today, d, hrv=60.0, rhr=40.0) for d in range(1, 31)]
    baseline, deviation, ctx = _compute_rhr_baseline(history, None, today)
    assert baseline == "40"
    assert deviation is None
    assert ctx == "-"


def test_rhr_baseline_90d_median_and_deviation() -> None:
    today = date(2025, 5, 28)
    # 30 entries at 40 bpm → median 40
    history = [_wellness(today, d, hrv=60.0, rhr=40.0) for d in range(1, 31)]
    baseline, deviation, ctx = _compute_rhr_baseline(history, 44.0, today)
    assert baseline == "40"
    assert deviation == "10"  # (44-40)/40*100 = 10
    assert ctx == "44.0 bpm (90d-Median: 40 bpm, +10%)"


def test_rhr_baseline_negative_deviation_signs_correctly() -> None:
    today = date(2025, 5, 28)
    history = [_wellness(today, d, hrv=60.0, rhr=50.0) for d in range(1, 31)]
    baseline, deviation, ctx = _compute_rhr_baseline(history, 45.0, today)
    assert baseline == "50"
    assert deviation == "-10"
    assert ctx == "45.0 bpm (90d-Median: 50 bpm, -10%)"


def test_rhr_baseline_ignores_entries_older_than_90_days() -> None:
    today = date(2025, 5, 28)
    # 60-day window of 40 bpm, plus a 120-day-old outlier at 80 bpm that
    # should be filtered out
    history = [_wellness(today, d, hrv=60.0, rhr=40.0) for d in range(1, 61)]
    history.append(_wellness(today, 120, hrv=60.0, rhr=80.0))
    baseline, _, _ = _compute_rhr_baseline(history, 40.0, today)
    assert baseline == "40"


# ── Combined HRV/RHR overload signal ─────────────────────────────────


def test_combined_signal_returns_none_without_baselines() -> None:
    today = date(2025, 5, 28)
    history = [_wellness(today, 0, hrv=60.0, rhr=44.0)]
    assert _compute_combined_overload_signal(history, None, 40.0, today) is None
    assert _compute_combined_overload_signal(history, 65.0, None, today) is None


def test_combined_signal_clear_when_only_one_marker_fires() -> None:
    today = date(2025, 5, 28)
    # HRV below baseline but RHR not elevated
    history = [_wellness(today, 0, hrv=55.0, rhr=40.0)]
    sig = _compute_combined_overload_signal(history, 65.0, 40.0, today)
    assert sig is not None
    assert sig["verdict"] == "clear"
    assert sig["days"] == 0


def test_combined_signal_watch_at_1_or_2_consecutive_days() -> None:
    today = date(2025, 5, 28)
    history = [
        _wellness(today, 0, hrv=55.0, rhr=46.0),  # both fire — day 0
        _wellness(today, 1, hrv=55.0, rhr=46.0),  # both fire — day 1
        _wellness(today, 2, hrv=60.0, rhr=40.0),  # clear — stops streak
    ]
    sig = _compute_combined_overload_signal(history, 65.0, 40.0, today)
    assert sig["verdict"] == "watch"
    assert sig["days"] == 2


def test_combined_signal_deload_at_3plus_consecutive_days() -> None:
    today = date(2025, 5, 28)
    history = [
        _wellness(today, 0, hrv=55.0, rhr=46.0),
        _wellness(today, 1, hrv=55.0, rhr=46.0),
        _wellness(today, 2, hrv=55.0, rhr=46.0),
        _wellness(today, 3, hrv=60.0, rhr=40.0),
    ]
    sig = _compute_combined_overload_signal(history, 65.0, 40.0, today)
    assert sig["verdict"] == "deload"
    assert sig["days"] == 3
    assert "deload trigger" in sig["message"]


def test_combined_signal_rhr_5bpm_threshold_strict() -> None:
    today = date(2025, 5, 28)
    # RHR at baseline+4 should NOT trigger (threshold is +5)
    history = [_wellness(today, 0, hrv=55.0, rhr=44.0)]
    sig = _compute_combined_overload_signal(history, 65.0, 40.0, today)
    assert sig["verdict"] == "clear"

    # RHR at baseline+5 SHOULD trigger
    history = [_wellness(today, 0, hrv=55.0, rhr=45.0)]
    sig = _compute_combined_overload_signal(history, 65.0, 40.0, today)
    assert sig["verdict"] == "watch"
    assert sig["days"] == 1


def test_combined_signal_data_gap_stops_streak() -> None:
    today = date(2025, 5, 28)
    history = [
        _wellness(today, 0, hrv=55.0, rhr=46.0),  # fires
        # gap at offset 1 (no entry)
        _wellness(today, 2, hrv=55.0, rhr=46.0),
        _wellness(today, 3, hrv=55.0, rhr=46.0),
    ]
    sig = _compute_combined_overload_signal(history, 65.0, 40.0, today)
    # Streak walks today (offset 0) → fires → 1; offset 1 missing → break.
    assert sig["days"] == 1
