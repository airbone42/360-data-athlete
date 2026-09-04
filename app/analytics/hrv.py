"""HRV/RHR wellness analytics — baselines, overload signal, readiness band, trends.

Extracted from context_builder (P4-1); context_builder re-imports every name,
so existing importers keep working.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from statistics import median, stdev

from app.utils.date_windows import cutoff_iso

# ── HRV readiness classifier (7d-rolling ln-rMSSD vs 60d normal band) ──
# Framework defaults; athlete-overridable later via config. The band is
# mean ± k·SD of daily ln-rMSSD over the reference window (Vesterinen /
# HRV4Training default, k=0.5). See
# framework/research/hrv-prediction-vs-readiness-modeling.md.
HRV_BAND_K = 0.5


HRV_BAND_REF_DAYS = 60


HRV_BAND_ROLL_DAYS = 7


HRV_BAND_HOLD_DAYS = 3


HRV_BAND_MIN_REF = 30  # < N valid daily values in 60d window → insufficient_data


HRV_BAND_MIN_ROLL = 4  # Plews plateau: ≥3-4 valid measurements/week


HRV_CVTREND_MIN_PTS = 4


HRV_CVTREND_DEADBAND_PCT = 10.0


def _compute_hrv_baseline(
    wellness_history: list[dict], hrv: float | None, today: date
) -> tuple[str, str | None, str]:
    cutoff = cutoff_iso(today, 90)
    hrv_values = [
        d["hrv"]
        for d in wellness_history
        if d.get("id", "") >= cutoff and d.get("hrv") is not None
    ]

    if not hrv_values:
        baseline_str = "-"
        deviation = None
    else:
        baseline = median(hrv_values)
        baseline_str = f"{baseline:.0f}"
        if hrv is not None:
            deviation = f"{(hrv - baseline) / baseline * 100:.0f}"
        else:
            deviation = None

    if deviation is not None and hrv is not None:
        sign = "+" if float(deviation) > 0 else ""
        hrv_context = (
            f"{hrv} ms (90d-Median: {baseline_str} ms, {sign}{deviation}%)"
        )
    else:
        hrv_context = f"{hrv} ms" if hrv is not None else "-"

    return baseline_str, deviation, hrv_context


def _compute_rhr_baseline(
    wellness_history: list[dict], rhr: float | None, today: date
) -> tuple[str, str | None, str]:
    """RHR baseline analog to HRV: 90d-median + deviation %.

    Mirrors ``_compute_hrv_baseline`` semantics so RHR drift surfaces in the
    same shape as HRV drift. Complements the short-window ``_compute_rhr_trend``
    (3d-vs-3d) which is an early warning, while this long-window baseline is
    the long-window overload reference. **Its bpm step is a convention, not a
    literature value** — the citation that once justified it was retracted on
    2026-09-01 (see ``framework/research/hrv-rhr-baseline-methodology.md``);
    the athlete-configurable threshold lives in ``rhr_overload_bpm``.

    Returns ``(baseline_str, deviation_str, rhr_context_str)``. ``deviation``
    is signed integer percent; ``rhr_context_str`` is the human-readable
    format used by the planner ("44 bpm (90d-Median: 40 bpm, +10%)").
    """
    cutoff = cutoff_iso(today, 90)
    rhr_values = [
        d["restingHR"]
        for d in wellness_history
        if d.get("id", "") >= cutoff and d.get("restingHR") is not None
    ]

    if not rhr_values:
        baseline_str = "-"
        deviation = None
    else:
        baseline = median(rhr_values)
        baseline_str = f"{baseline:.0f}"
        if rhr is not None and baseline > 0:
            deviation = f"{(rhr - baseline) / baseline * 100:.0f}"
        else:
            deviation = None

    if deviation is not None and rhr is not None:
        sign = "+" if float(deviation) > 0 else ""
        rhr_context = (
            f"{rhr} bpm (90d-Median: {baseline_str} bpm, {sign}{deviation}%)"
        )
    else:
        rhr_context = f"{rhr} bpm" if rhr is not None else "-"

    return baseline_str, deviation, rhr_context


# TSB below which the third marker of the convergence signal fires. The
# value mirrors `config.example/recovery_protocol.md`; like the bpm step it
# is an operating convention, not a literature threshold.
TSB_OVERLOAD_THRESHOLD = -15.0


def _compute_combined_overload_signal(
    wellness_history: list[dict],
    hrv_baseline_float: float | None,
    rhr_baseline_float: float | None,
    today: date,
    rhr_overload_bpm: float = 5.0,
    tsb_threshold: float = TSB_OVERLOAD_THRESHOLD,
) -> dict | None:
    """Convergence overload trigger — two of three markers, per Meeusen.

    For each of the last N days, check how many of **three** markers fired:
      - HRV below 90d-median (any negative deviation counts; SWC-based
        filtering happens elsewhere)
      - RHR ≥ baseline + ``rhr_overload_bpm``
      - TSB ≤ ``tsb_threshold`` (computed per day from that day's CTL/ATL)

    **Why three and not two.** The documented rule has always been the
    Meeusen convergence idea — no single marker diagnoses overreaching, so
    look for agreement between several. The implementation checked HRV
    **and** RHR only, which is stricter than documented in one specific and
    unhelpful way: it cannot fire at all without HRV. An athlete who is an
    HRV non-responder, or whose wearable simply dropped the value, had no
    overload signal available even when RHR and TSB both pointed the same
    way. Requiring two of three keeps the conjunction that makes the signal
    specific while removing HRV's veto over it.

    A day counts as a hit when at least two markers are **available and
    firing**; a day with fewer than two available markers cannot be judged
    and ends the streak rather than silently counting as clean.

    **The bpm threshold is a convention, not a literature value.** It was
    previously documented as "literature-anchored" on the strength of a single
    coaching article; a citation audit found the attributed sentence absent from
    that source, so the justification has been withdrawn (see the research doc
    below). The default of 5 bpm is kept because changing an athlete's readiness
    gate is a training decision, not a redaction — but it is now overridable per
    athlete via ``rhr_overload_bpm`` in ``config/athlete_status.md``, the same
    split already used for ``impact_streak_max``.

    What actually makes this signal specific is the **conjunction** (HRV below
    baseline AND RHR elevated) plus the **consecutive-day** requirement — not
    the size of the bpm step.

    Returns a dict ``{verdict, days, message}`` or ``None`` when neither
    baseline is available. ``verdict``:

      - ``"deload"``  — 3+ consecutive days both signals fired → deload trigger
      - ``"watch"``   — 1–2 consecutive days both signals fired → monitor
      - ``"clear"``   — today is symptom-free

    Reference: ``framework/research/hrv-rhr-baseline-methodology.md``
    section "RHR and HRV — together or separately?" (Buchheit 2014). The
    RunnersConnect reference formerly cited here was retracted on 2026-09-01.
    """
    # At least two markers must be derivable at all, otherwise there is no
    # convergence to detect. TSB needs no baseline — it is self-contained.
    available_markers = sum(
        x is not None for x in (hrv_baseline_float, rhr_baseline_float)
    ) + 1
    if available_markers < 2:
        return None

    # Walk backward from today; count consecutive days where at least two of
    # the three markers fire.
    streak = 0
    judged_any = False
    fired_names: set[str] = set()
    for offset in range(0, 7):  # check today + last 6 days
        d_str = cutoff_iso(today, offset)
        entry = next((x for x in wellness_history if x.get("id") == d_str), None)
        if entry is None:
            # No data for this day → stop streak (do not count gaps as hits)
            break

        day_fired: list[str] = []
        day_available = 0

        hrv_val = entry.get("hrv")
        if hrv_baseline_float is not None and hrv_val is not None:
            day_available += 1
            if hrv_val < hrv_baseline_float:
                day_fired.append("HRV")

        rhr_val = entry.get("restingHR")
        if rhr_baseline_float is not None and rhr_val is not None:
            day_available += 1
            if rhr_val >= rhr_baseline_float + rhr_overload_bpm:
                day_fired.append("RHR")

        ctl_val, atl_val = entry.get("ctl"), entry.get("atl")
        if ctl_val is not None and atl_val is not None:
            day_available += 1
            if (ctl_val - atl_val) <= tsb_threshold:
                day_fired.append("TSB")

        # Fewer than two readable markers is an unjudgeable day, not a clean
        # one — treat it like a data gap.
        if day_available < 2:
            break
        judged_any = True
        if len(day_fired) < 2:
            break
        streak += 1
        fired_names.update(day_fired)

    if streak == 0:
        if not judged_any:
            # No day carried two readable markers — silence here means missing
            # data, not an all-clear, and saying "clear" would misreport it.
            return {
                "verdict": "insufficient_data",
                "days": 0,
                "markers": [],
                "message": (
                    "Convergence signal not computable — fewer than two of "
                    "HRV / RHR / TSB readable in the window."
                ),
            }
        return {
            "verdict": "clear",
            "days": 0,
            "markers": [],
            "message": "No convergence overload signal (needs 2 of HRV / RHR / TSB).",
        }
    marker_list = ", ".join(sorted(fired_names))
    if streak >= 3:
        return {
            "verdict": "deload",
            "days": streak,
            "markers": sorted(fired_names),
            "message": (
                f"⛔ Convergence overload: {marker_list} for {streak} consecutive "
                f"days (2-of-3 rule) — deload trigger active."
            ),
        }
    return {
        "verdict": "watch",
        "days": streak,
        "markers": sorted(fired_names),
        "message": (
            f"⚠️ Convergence drift watch: {marker_list} for {streak} day(s) "
            f"(2-of-3 rule) — monitor for deload at 3d."
        ),
    }


def _compute_hrv_cv(wellness_history: list[dict], today: date) -> float | None:
    """Compute within-athlete HRV coefficient of variation over last 60 days.

    CV = stdev / mean × 100. Used for Plews/Buchheit SWC-based intensity_readiness
    trigger (SWC = 0.5-1.0 × CV).

    Returns None if fewer than 20 data points available.
    """
    cutoff = cutoff_iso(today, 60)
    hrv_values = [
        d["hrv"]
        for d in wellness_history
        if d.get("id", "") >= cutoff and d.get("hrv") is not None
    ]
    if len(hrv_values) < 20:
        return None
    mean = sum(hrv_values) / len(hrv_values)
    if mean == 0:
        return None
    sd = stdev(hrv_values)
    return (sd / mean) * 100


def _compute_hrv_cv_trend(wellness_history: list[dict], today: date) -> dict:
    """Advisory day-to-day CV trend of ln-rMSSD: trailing-7d CV vs prior-7d CV.

    Rising day-to-day CV (without a drop in the rolling mean) is an early
    non-functional-overreaching indicator (Plews 2012). ADVISORY ONLY — never
    feeds intensity_readiness or hrvReviewPending; promote to a trigger only
    after per-athlete calibration. A ±deadband keeps noise from flipping the
    label. Returns ``{trend, cv_recent, cv_prior}`` with
    ``trend ∈ {rising, falling, stable, insufficient_data}``.
    """
    ln_map: dict[str, float] = {
        d["id"]: math.log(d["hrv"])
        for d in wellness_history
        if d.get("id") and d.get("hrv") is not None and d["hrv"] > 0
    }

    def _cv_over(lo: int, hi: int) -> float | None:
        vals = [
            ln_map[cutoff_iso(today, o)]
            for o in range(lo, hi + 1)
            if cutoff_iso(today, o) in ln_map
        ]
        if len(vals) < HRV_CVTREND_MIN_PTS:
            return None
        mean = sum(vals) / len(vals)
        if mean == 0:
            return None
        return stdev(vals) / abs(mean) * 100

    cv_recent = _cv_over(0, 6)
    cv_prior = _cv_over(7, 13)
    if cv_recent is None or cv_prior is None:
        return {"trend": "insufficient_data", "cv_recent": cv_recent, "cv_prior": cv_prior}
    rel = (cv_recent - cv_prior) / cv_prior * 100 if cv_prior else 0.0
    if rel > HRV_CVTREND_DEADBAND_PCT:
        trend = "rising"
    elif rel < -HRV_CVTREND_DEADBAND_PCT:
        trend = "falling"
    else:
        trend = "stable"
    return {"trend": trend, "cv_recent": round(cv_recent, 1), "cv_prior": round(cv_prior, 1)}


def _compute_hrv_readiness_band(
    wellness_history: list[dict],
    today: date,
    *,
    k: float = HRV_BAND_K,
    ref_days: int = HRV_BAND_REF_DAYS,
    roll_days: int = HRV_BAND_ROLL_DAYS,
    hold_days: int = HRV_BAND_HOLD_DAYS,
    min_coverage_band: int = HRV_BAND_MIN_REF,
    min_coverage_roll: int = HRV_BAND_MIN_ROLL,
) -> dict:
    """Readiness classifier: 7-day rolling ln-rMSSD vs a 60-day normal band.

    The literature-canonical HRV-guided-training method (Plews/Buchheit,
    Vesterinen, Altini): track the 7-day rolling mean of ln-rMSSD and classify
    it against a normal-range band built from a 60-day reference window
    (mean ± k·SD of daily ln-rMSSD, default k=0.5). A sustained departure below
    the band (``hold_days``+ consecutive days) is the actionable fatigue signal —
    not a single day's value. Replaces the retired load→HRV regression forecast
    (see framework/research/hrv-prediction-vs-readiness-modeling.md).

    intervals.icu ``wellness[].hrv`` is rMSSD in ms → ``ln_rmssd = ln(hrv)``.
    The ``*_ms`` fields are ``exp()`` back-transforms — geometric means in the
    ln domain (the modelling space), NOT arithmetic means of raw ms; do not
    "fix" them to raw means.

    Causal / NO look-ahead: classifying day d uses only data ≤ d. The rolling
    mean reads ``[d-6..d]`` (trailing, never centred); the band reads
    ``[d-59..d]``; the consecutive walk-back recomputes BOTH the rolling mean and
    the band as of each historical day (it never reuses today's band to judge a
    past day). An OOS walk-forward test would otherwise leak via a single fixed
    band reused for all days, a centred rolling window, or interpolating gaps
    from later values.

    Verdicts: ``clear`` (inside band) / ``above`` (above band) / ``watch`` (1-2
    consecutive days below) / ``hold`` (≥``hold_days`` below) / ``insufficient_data``
    (< ``min_coverage_band`` valid daily values in the reference window → caller
    falls back to the existing 90d-median+5% logic in _compute_intensity_readiness).

    Structural twin of ``_compute_combined_overload_signal`` (same walk-back: a
    gap/None day stops the streak).

    Not cycle-aware: luteal-phase HRV runs ~5-10% lower, which can drift a
    cycle-spanning rolling mean below band for endocrine, not training, reasons.
    Out of scope for the male-configured single-athlete setup; see the research
    doc's "Open questions" for the female-athlete generalisation.
    """
    ln_map: dict[str, float] = {
        d["id"]: math.log(d["hrv"])
        for d in wellness_history
        if d.get("id") and d.get("hrv") is not None and d["hrv"] > 0
    }

    def _rolling_mean_as_of(d: date) -> float | None:
        vals = [
            ln_map[cutoff_iso(d, o)]
            for o in range(0, roll_days)
            if cutoff_iso(d, o) in ln_map
        ]
        if len(vals) < min_coverage_roll:
            return None
        return sum(vals) / len(vals)

    def _band_as_of(d: date) -> tuple[float, float, float, float, int] | None:
        vals = [
            ln_map[cutoff_iso(d, o)]
            for o in range(0, ref_days)
            if cutoff_iso(d, o) in ln_map
        ]
        n = len(vals)
        if n < min_coverage_band:
            return None
        mean = sum(vals) / n
        sd = stdev(vals)
        return mean - k * sd, mean + k * sd, mean, sd, n

    cv_trend = _compute_hrv_cv_trend(wellness_history, today)
    band_today = _band_as_of(today)

    if band_today is None:
        n_valid = sum(
            1
            for o in range(0, ref_days)
            if cutoff_iso(today, o) in ln_map
        )
        return {
            "verdict": "insufficient_data",
            "days_below": 0,
            "rolling_mean_ln": None,
            "rolling_mean_ms": None,
            "band_low_ln": None,
            "band_high_ln": None,
            "band_low_ms": None,
            "band_high_ms": None,
            "cv": None,
            "n_ref": n_valid,
            "cv_trend": cv_trend,
        }

    band_low, band_high, mean_ln, sd_ln, n_ref = band_today
    cv = (sd_ln / mean_ln * 100) if mean_ln else None
    roll_today = _rolling_mean_as_of(today)

    if roll_today is None:
        verdict, days_below = "clear", 0
    elif roll_today > band_high:
        verdict, days_below = "above", 0
    elif roll_today >= band_low:
        verdict, days_below = "clear", 0
    else:
        # Below band → count consecutive below-band days, each judged against
        # ITS OWN causal rolling mean + band. A gap/None or the first
        # in-band/above day stops the streak (mirrors
        # _compute_combined_overload_signal).
        streak = 0
        for offset in range(0, ref_days):
            d = today - timedelta(days=offset)
            r = _rolling_mean_as_of(d)
            b = _band_as_of(d)
            if r is None or b is None:
                break
            if r < b[0]:
                streak += 1
            else:
                break
        days_below = streak
        verdict = "hold" if streak >= hold_days else "watch"

    return {
        "verdict": verdict,
        "days_below": days_below,
        "rolling_mean_ln": round(roll_today, 4) if roll_today is not None else None,
        "rolling_mean_ms": (
            round(math.exp(roll_today), 1) if roll_today is not None else None
        ),
        "band_low_ln": round(band_low, 4),
        "band_high_ln": round(band_high, 4),
        "band_low_ms": round(math.exp(band_low), 1),
        "band_high_ms": round(math.exp(band_high), 1),
        "cv": round(cv, 1) if cv is not None else None,
        "n_ref": n_ref,
        "cv_trend": cv_trend,
    }


def _compute_sleep_trend(wellness_history: list[dict], today: date) -> str:
    """7-day rolling average of sleep hours and score.

    Returns a formatted string. Flags chronic sleep deprivation (avg < 6.5h)
    when at least 5 of the last 7 days have data.
    """
    cutoff = cutoff_iso(today, 7)
    days = [
        d for d in wellness_history
        if d.get("id", "") > cutoff and d.get("id", "") <= today.isoformat()
    ]
    sleep_hours_vals = [
        d["sleepSecs"] / 3600
        for d in days
        if d.get("sleepSecs") is not None
    ]
    sleep_score_vals = [
        d["sleepScore"]
        for d in days
        if d.get("sleepScore") is not None
    ]

    if not sleep_hours_vals:
        return "-"

    avg_hours = sum(sleep_hours_vals) / len(sleep_hours_vals)
    avg_score = sum(sleep_score_vals) / len(sleep_score_vals) if sleep_score_vals else None

    score_str = f" | Score: {avg_score:.0f}" if avg_score is not None else ""
    trend = f"7d-Schnitt: {avg_hours:.1f}h{score_str} ({len(sleep_hours_vals)} Tage)"

    if len(sleep_hours_vals) >= 5 and avg_hours < 6.5:
        trend = f"⚠️ {trend}"

    return trend


def _compute_rhr_trend(
    wellness_history: list[dict], today: date
) -> tuple[str, float | None]:
    """7-day RHR trend to detect overreaching early.

    Compares the 3-day average (days 1–3 ago) to the 3-day average (days 5–7 ago).
    Returns (formatted_string, delta_bpm). delta_bpm is None if insufficient data.
    """
    def _rhr_avg(days_ago_start: int, days_ago_end: int) -> float | None:
        vals = []
        for offset in range(days_ago_start, days_ago_end + 1):
            d = cutoff_iso(today, offset)
            entry = next((x for x in wellness_history if x.get("id") == d), None)
            if entry and entry.get("restingHR") is not None:
                vals.append(entry["restingHR"])
        return sum(vals) / len(vals) if vals else None

    recent = _rhr_avg(1, 3)   # last 3 days
    earlier = _rhr_avg(5, 7)  # 3 days from 5-7 days ago

    if recent is None or earlier is None:
        return "-", None

    delta = recent - earlier
    sign = f"+{delta:.0f}" if delta >= 0 else f"{delta:.0f}"
    trend = f"{recent:.0f} bpm (7d: {sign} bpm)"

    if delta > 3:
        trend = f"⚠️ {trend} – rising resting HR"

    return trend, delta
