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


def _wellness(
    today: date,
    days: int,
    hrv: float | None,
    rhr: float | None,
    ctl: float | None = None,
    atl: float | None = None,
) -> dict:
    return {
        "id": (today - timedelta(days=days)).isoformat(),
        "hrv": hrv,
        "restingHR": rhr,
        "ctl": ctl,
        "atl": atl,
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


def test_combined_signal_needs_two_derivable_markers() -> None:
    """One baseline missing is fine — TSB is the third marker and needs none.

    The signal used to require both HRV and RHR baselines, which gave HRV a
    veto over an overload trigger that RHR and TSB can carry on their own.
    """
    today = date(2025, 5, 28)
    history = [_wellness(today, 0, hrv=60.0, rhr=44.0, ctl=40.0, atl=42.0)]
    assert _compute_combined_overload_signal(history, None, 40.0, today) is not None
    assert _compute_combined_overload_signal(history, 65.0, None, today) is not None


def test_combined_signal_reports_insufficient_data_not_clear() -> None:
    """A day with fewer than two readable markers is unjudgeable.

    Reporting "clear" there would present missing data as an all-clear.
    """
    today = date(2025, 5, 28)
    history = [_wellness(today, 0, hrv=None, rhr=44.0)]  # no HRV, no CTL/ATL
    sig = _compute_combined_overload_signal(history, 65.0, 40.0, today)
    assert sig is not None
    assert sig["verdict"] == "insufficient_data"


def test_combined_signal_fires_on_rhr_plus_tsb_without_hrv() -> None:
    """The case the old conjunction could not see: an HRV non-responder, or a
    wearable that dropped the value, with RHR and TSB both pointing down."""
    today = date(2025, 5, 28)
    history = [
        _wellness(today, d, hrv=None, rhr=46.0, ctl=40.0, atl=58.0)
        for d in range(3)
    ]
    sig = _compute_combined_overload_signal(history, 65.0, 40.0, today)
    assert sig is not None
    assert sig["verdict"] == "deload"
    assert sig["markers"] == ["RHR", "TSB"]


def test_combined_signal_still_fires_on_the_classic_hrv_plus_rhr_pair() -> None:
    today = date(2025, 5, 28)
    history = [
        _wellness(today, d, hrv=55.0, rhr=46.0) for d in range(3)
    ]
    sig = _compute_combined_overload_signal(history, 65.0, 40.0, today)
    assert sig is not None
    assert sig["verdict"] == "deload"
    assert sig["markers"] == ["HRV", "RHR"]


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
