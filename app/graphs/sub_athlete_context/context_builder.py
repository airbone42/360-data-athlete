"""Port of the n8n 'Build Athlete Context' JS code node to Python."""

from __future__ import annotations

import logging
import math
from datetime import date, timedelta
from statistics import median, stdev

logger = logging.getLogger(__name__)

from pydantic import ValidationError

from app.analytics.recovery import (
    MUSCLE_OVERLAP_RULES,
    NINJA_PILLAR_KEYWORDS,
    NINJA_TAG_TO_PILLAR,
    RECOVERY_RULES,
    _extract_rpe_from_line,
    canonicalise_tags,
)
from app.config import settings
from app.graphs.shoe_advisor import build_shoe_context, load_shoe_profiles
from app.graphs.sub_athlete_context.state import AthleteContextState
from app.schemas.context import ContextDict
from app.utils.alerts import notify_error
from app.utils.hr_zones import extract_run_hr_bounds, format_hr_zones
from app.utils.prompt_loader import load_prompt

TOLERANCE_PCT = 0.12
DELOAD_PCT = 0.20
MIN_CTL = 20

CARDIO_TYPES = {"Run", "Ride", "VirtualRide", "VirtualRun"}

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


def build_context(state: AthleteContextState) -> dict:
    """Aggregate all fetched data into a coaching context dict."""
    wellness = state["wellness"]
    activities = state["activities"]
    workouts = state["workouts"]
    events = state["events"]
    wellness_history = state["wellness_history"]
    weather_data = state["weather"]
    today = date.fromisoformat(state["date"])

    activities_with_workout = _pair_activities_with_workouts(activities, workouts)

    hrv = wellness.get("hrv")
    rhr = wellness.get("restingHR")
    sleep_score = wellness.get("sleepScore")
    ctl = wellness.get("ctl")
    atl = wellness.get("atl")
    sleep_secs = wellness.get("sleepSecs")

    sleep_hours = f"{sleep_secs / 3600:.1f}h" if sleep_secs else "-"
    tsb = round(ctl - atl, 1) if ctl is not None and atl is not None else "-"

    ctl_display = _format_ctl(ctl)

    hrv_baseline, hrv_deviation, hrv_context = _compute_hrv_baseline(
        wellness_history, hrv, today
    )
    rhr_baseline, rhr_deviation, rhr_context = _compute_rhr_baseline(
        wellness_history, rhr, today
    )

    weekly_stats = _compute_weekly_stats(wellness_history, today)
    cycle_hint = _analyze_load_cycle(weekly_stats)
    ctl_trend = _compute_ctl_trend(weekly_stats)
    zone_distribution = _compute_zone_distribution(activities)
    tsb_recent: list[float] | None = None
    if wellness_history:
        tsb_vals = [
            float(w["tsb"])
            for w in wellness_history[-7:]
            if w.get("tsb") is not None
        ]
        if tsb_vals:
            tsb_recent = tsb_vals
    meso_load_trend = _compute_meso_load_trend(
        activities, today, ctl, state.get("deload_ctl_threshold"),
        tsb_recent=tsb_recent,
    )
    weekly_zone_balance = _compute_zone_distribution(
        [a for a in activities if (a.get("start_date_local") or "")[:10] >= (today - timedelta(days=7)).isoformat()]
    )
    weekly_hard_reize_balance = _compute_weekly_hard_reize_balance(activities, today)

    last_intense = _find_last_intense_session(activities)
    last_rest_day = _find_last_rest_day(activities, today)

    days_since_intense = _days_since(last_intense, today)
    hrv_cv = _compute_hrv_cv(wellness_history, today)

    hrv_baseline_float_for_signal = float(hrv_baseline) if hrv_baseline != "-" else None
    rhr_baseline_float_for_signal = float(rhr_baseline) if rhr_baseline != "-" else None
    combined_overload_signal = _compute_combined_overload_signal(
        wellness_history,
        hrv_baseline_float_for_signal,
        rhr_baseline_float_for_signal,
        today,
    )

    # HRV readiness classifier (7d-rolling ln-rMSSD vs 60d normal band) —
    # replaces the retired load→HRV regression forecast. Wellness-only; the
    # 90d wellness window from fetch_context covers the 60d band + 7d rolling
    # + the consecutive walk-back.
    hrv_readiness = _compute_hrv_readiness_band(wellness_history, today)
    hrv_cv_trend = hrv_readiness.get("cv_trend")

    intensity_readiness = _compute_intensity_readiness(
        hrv, hrv_baseline, tsb, days_since_intense, hrv_cv,
        combined_overload_signal, hrv_readiness,
    )

    notes = state.get("notes") or []
    hrv_review_pending = _find_pending_hrv_review(hrv_readiness, notes, today)
    athlete_feedback = _format_notes(notes)

    sleep_trend = _compute_sleep_trend(wellness_history, today)
    rhr_trend, rhr_trend_delta = _compute_rhr_trend(wellness_history, today)

    weather_info = _format_weather(weather_data, today)
    event_list = _format_events(events, today)
    race_in_days = _days_to_next_race(events, today)
    deload_state = state.get("deload_state") or {}
    planning_warnings: list[str] = []
    planning_constraints = _compute_planning_constraints(
        events, activities_with_workout, today, deload_state,
        warnings_out=planning_warnings,
    )

    date_str = today.strftime("%A, %d. %B %Y")

    athlete_settings = state.get("athlete_settings") or {}
    hr_bounds = extract_run_hr_bounds(athlete_settings)
    hr_zones_text = format_hr_zones(hr_bounds)
    _raw_prompt = load_prompt("daily_planner").template.replace("{hr_zones}", hr_zones_text)
    # shoeContext will be filled after shoe_ctx is built — placeholder replaced below
    system_prompt = _raw_prompt  # final substitution happens after shoe_ctx is computed
    weather_warning = state.get("weather_warning", False)
    warnings = _collect_warnings(
        hrv, rhr, sleep_score, ctl, atl, hr_zones_text, athlete_settings, weather_warning,
        sleep_trend, rhr_trend_delta,
    )
    warnings.extend(planning_warnings)
    skipped_workouts = _find_skipped_workouts(activities, state["workouts"], today)

    # Shoe context (optional — degrades silently if no shoe backend configured).
    # `shoes` is the backend-neutral shoe list assembled by fetch_context
    # (`strava_shoes` key kept for back-compat); the join key is selected by
    # `shoe_tracking_backend` (intervals → icu_gear_id, strava → strava_id).
    shoe_list: list[dict] = state.get("shoes") or state.get("strava_shoes") or []
    shoe_profiles = load_shoe_profiles()
    shoe_ctx: dict = {}
    if shoe_list:
        try:
            shoe_ctx = build_shoe_context(
                shoes=shoe_list,
                profiles=shoe_profiles,
                activities=activities,
                planned_workouts=[
                    w for w in workouts
                    if w.get("type") == "Run"
                    and (w.get("start_date_local") or "")[:10] == today.isoformat()
                ],  # populated when context is re-fetched after push_workouts
                weather_info=weather_info,
                race_in_days=race_in_days,
                today_str=today.isoformat(),
                backend=settings.shoe_tracking_backend,
            )
        except Exception as e:
            logger.warning("shoe_advisor failed: %s", e)

    shoe_context_text = _format_shoe_context(shoe_ctx)
    system_prompt = system_prompt.replace("{shoeContext}", shoe_context_text)

    today_workouts = _summarize_today_workouts(events, today)

    result = {
        "hrvContext": hrv_context,
        "hrv": hrv if hrv is not None else "-",
        "rhr": rhr if rhr is not None else "-",
        "sleep": sleep_score if sleep_score is not None else "-",
        "sleepHours": sleep_hours,
        "activities": [
            _summarize_activity(a) for a in activities_with_workout
        ],
        "ctl": ctl if ctl is not None else "-",
        "atl": atl if atl is not None else "-",
        "tsb": tsb,
        "ctlDisplay": ctl_display,
        "hrvBaseline": hrv_baseline,
        "hrvDeviation": hrv_deviation,
        "rhrContext": rhr_context,
        "rhrBaseline": rhr_baseline,
        "rhrDeviation": rhr_deviation,
        "combinedOverloadSignal": combined_overload_signal,
        "sleepTrend": sleep_trend,
        "rhrTrend": rhr_trend,
        "ctlTrend": ctl_trend,
        "cycleHint": cycle_hint,
        "zoneDistribution": zone_distribution,
        "weeklyZoneBalance": weekly_zone_balance,
        "weeklyHardReizeBalance": weekly_hard_reize_balance,
        "mesoLoadTrend": meso_load_trend,
        "weatherInfo": weather_info,
        "intensityReadiness": intensity_readiness,
        "daysSinceIntense": days_since_intense,
        "lastRestDay": last_rest_day,
        "athleteFeedback": athlete_feedback,
        "eventList": event_list,
        "raceInDays": race_in_days,
        "planningConstraints": planning_constraints,
        "dateStr": date_str,
        "hrZones": hr_zones_text,
        "hrvReviewPending": hrv_review_pending,
        "hrvReadiness": hrv_readiness,
        "hrvCvTrend": hrv_cv_trend,
        "skippedWorkouts": skipped_workouts,
        "systemPrompt": system_prompt,
        "dataWarnings": warnings,
        # Shoe context (empty dicts/lists when Strava not configured)
        "shoes": shoe_ctx.get("shoes", []),
        "shoeRecommendation": shoe_ctx.get("shoeRecommendation", {}),
        "shoeWarnings": shoe_ctx.get("shoeWarnings", []),
        "shoeFleetWarning": shoe_ctx.get("shoeFleetWarning", {}),
        "todayWorkouts": today_workouts,
    }

    # Validate schema at boundary — alert on violation but return raw dict (no breaking change)
    try:
        ContextDict.model_validate(result, by_alias=True)
    except ValidationError as exc:
        notify_error("build_context schema violation", {"errors": str(exc)[:500]})
        logger.error("context schema violation: %s", exc)

    return result


# ── Helper functions ────────────────────────────────────────────────


def _summarize_activity(a: dict) -> dict:
    """Reduce a full activity object to the fields the planner actually needs.

    `name` and `event_description` are athlete-/Strava-roundtrip-controlled
    and end up in specialist briefings → sanitize at this write boundary
    (mirrors history_fetcher._format_activity).
    """
    from app.utils.sanitize import escape_for_prompt

    raw_name = a.get("name") or ""
    result: dict = {
        "date": (a.get("start_date_local") or "")[:10],
        "type": a.get("type"),
        "name": escape_for_prompt(raw_name, max_len=200) if raw_name else raw_name,
        "tags": a.get("tags"),
        "workout_type": a.get("workout_type"),
        "training_load": a.get("icu_training_load"),
        "duration_min": round(a.get("moving_time", 0) / 60) or None,
    }
    if a.get("event_description"):
        result["coaching_notes"] = escape_for_prompt(a["event_description"], max_len=500)
    return result


def _pair_activities_with_workouts(
    activities: list[dict], workouts: list[dict]
) -> list[dict]:
    workout_map = {w["id"]: w for w in workouts if "id" in w}
    result: list[dict] = []
    for a in activities:
        paired_id = a.get("paired_event_id")
        if paired_id and paired_id in workout_map:
            result.append(
                {**a, "event_description": workout_map[paired_id].get("description")}
            )
        else:
            result.append(a)
    return result


def _find_skipped_workouts(
    activities: list[dict],
    workouts: list[dict],
    today: date,
) -> list[dict]:
    """Find coach-planned workouts from past days that have no paired activity.

    Only checks events with UID starting with 'coach-' (our own workouts).
    """
    paired_ids: set[int] = {
        a["paired_event_id"]
        for a in activities
        if a.get("paired_event_id") is not None
    }

    skipped: list[dict] = []
    for w in workouts:
        if w.get("category") != "WORKOUT":
            continue
        uid = str(w.get("uid", ""))
        if not uid.startswith("coach-"):
            continue
        w_date = (w.get("start_date_local") or "")[:10]
        if not w_date or w_date >= today.isoformat():
            continue  # only past days
        if w.get("id") in paired_ids:
            continue  # was executed
        skipped.append({
            "id": w["id"],
            "date": w_date,
            "name": w.get("name", "?"),
        })

    return skipped


def _format_ctl(ctl: float | None) -> str:
    if ctl is None:
        return "-"
    if ctl < MIN_CTL:
        return (
            f"{ctl:.1f} ⚠️ tracking window too short"
            " — no valid fitness indicator"
        )
    return f"{ctl:.1f}"


def _compute_hrv_baseline(
    wellness_history: list[dict], hrv: float | None, today: date
) -> tuple[str, str | None, str]:
    cutoff = (today - timedelta(days=90)).isoformat()
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
    the literature-anchored overload reference (RunnersConnect: +5 bpm vs
    3-week baseline as robust overload marker — see
    ``framework/research/hrv-rhr-baseline-methodology.md``).

    Returns ``(baseline_str, deviation_str, rhr_context_str)``. ``deviation``
    is signed integer percent; ``rhr_context_str`` is the human-readable
    format used by the planner ("44 bpm (90d-Median: 40 bpm, +10%)").
    """
    cutoff = (today - timedelta(days=90)).isoformat()
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


def _compute_combined_overload_signal(
    wellness_history: list[dict],
    hrv_baseline_float: float | None,
    rhr_baseline_float: float | None,
    today: date,
) -> dict | None:
    """Combined HRV+RHR overload trigger (Buchheit 2014 + RunnersConnect).

    For each of the last N days, check whether **both** signals fired:
      - HRV below 90d-median (any negative deviation counts; SWC-based
        filtering happens elsewhere)
      - RHR ≥ baseline + 5 bpm (literature-anchored robust overload
        threshold, more specific than the 3-bpm 7d short-window warning)

    Returns a dict ``{verdict, days, message}`` or ``None`` when neither
    baseline is available. ``verdict``:

      - ``"deload"``  — 3+ consecutive days both signals fired → deload trigger
      - ``"watch"``   — 1–2 consecutive days both signals fired → monitor
      - ``"clear"``   — today is symptom-free

    Reference: ``framework/research/hrv-rhr-baseline-methodology.md``
    section "RHR and HRV — together or separately?" (Buchheit 2014;
    RunnersConnect overtraining-resting-heart-rate review).
    """
    if hrv_baseline_float is None or rhr_baseline_float is None:
        return None

    # Walk backward from today; count consecutive days both signals fire.
    streak = 0
    for offset in range(0, 7):  # check today + last 6 days
        d_str = (today - timedelta(days=offset)).isoformat()
        entry = next((x for x in wellness_history if x.get("id") == d_str), None)
        if entry is None:
            # No data for this day → stop streak (do not count gaps as hits)
            break
        hrv_val = entry.get("hrv")
        rhr_val = entry.get("restingHR")
        if hrv_val is None or rhr_val is None:
            break
        hrv_below = hrv_val < hrv_baseline_float
        rhr_elevated = rhr_val >= rhr_baseline_float + 5
        if hrv_below and rhr_elevated:
            streak += 1
        else:
            break

    if streak == 0:
        return {"verdict": "clear", "days": 0, "message": "No combined HRV/RHR overload signal."}
    if streak >= 3:
        return {
            "verdict": "deload",
            "days": streak,
            "message": (
                f"⛔ Combined overload: HRV below baseline AND RHR ≥ +5 bpm "
                f"for {streak} consecutive days — deload trigger active."
            ),
        }
    return {
        "verdict": "watch",
        "days": streak,
        "message": (
            f"⚠️ Combined drift watch: HRV below baseline AND RHR ≥ +5 bpm "
            f"for {streak} day(s) — monitor for deload at 3d."
        ),
    }


# ── HRV Readiness (7d-rolling ln-rMSSD vs 60d band) ────────────────


def _compute_hrv_cv(wellness_history: list[dict], today: date) -> float | None:
    """Compute within-athlete HRV coefficient of variation over last 60 days.

    CV = stdev / mean × 100. Used for Plews/Buchheit SWC-based intensity_readiness
    trigger (SWC = 0.5-1.0 × CV).

    Returns None if fewer than 20 data points available.
    """
    cutoff = (today - timedelta(days=60)).isoformat()
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
            ln_map[(today - timedelta(days=o)).isoformat()]
            for o in range(lo, hi + 1)
            if (today - timedelta(days=o)).isoformat() in ln_map
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
            ln_map[(d - timedelta(days=o)).isoformat()]
            for o in range(0, roll_days)
            if (d - timedelta(days=o)).isoformat() in ln_map
        ]
        if len(vals) < min_coverage_roll:
            return None
        return sum(vals) / len(vals)

    def _band_as_of(d: date) -> tuple[float, float, float, float, int] | None:
        vals = [
            ln_map[(d - timedelta(days=o)).isoformat()]
            for o in range(0, ref_days)
            if (d - timedelta(days=o)).isoformat() in ln_map
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
            if (today - timedelta(days=o)).isoformat() in ln_map
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
        "rolling_mean_ln": round(roll_today, 4),
        "rolling_mean_ms": round(math.exp(roll_today), 1),
        "band_low_ln": round(band_low, 4),
        "band_high_ln": round(band_high, 4),
        "band_low_ms": round(math.exp(band_low), 1),
        "band_high_ms": round(math.exp(band_high), 1),
        "cv": round(cv, 1) if cv is not None else None,
        "n_ref": n_ref,
        "cv_trend": cv_trend,
    }


_HRV_REVIEW_PREFIX = "HRV-Review"


def _find_pending_hrv_review(
    hrv_readiness: dict | None,
    notes: list[dict],
    today: date,
) -> dict | None:
    """Surface a pending HRV review when the readiness band is below normal.

    Replaces the retired regression-residual trigger: a review is pending when
    the 7d-rolling ln-rMSSD is below the 60d band (verdict ``watch`` or ``hold``,
    i.e. 1+ consecutive day below) and the athlete has not yet logged an
    ``HRV-Review`` NOTE covering the below-band window. The head coach asks once
    per day for external factors (sleep, stress, alcohol, illness, travel);
    confounder auto-annotation from arbitrary NOTEs is a documented follow-on.
    """
    if not hrv_readiness or hrv_readiness.get("verdict") not in ("watch", "hold"):
        return None

    days_below = hrv_readiness.get("days_below", 0)
    window = {
        (today - timedelta(days=o)).isoformat()
        for o in range(0, max(days_below, 1))
    }
    for note in notes:
        text = (note.get("description") or "") + " " + (note.get("name") or "")
        if _HRV_REVIEW_PREFIX in text:
            d = (note.get("start_date_local") or "")[:10]
            if d in window:
                return None  # already reviewed within the below-band window

    return {
        "date": today.isoformat(),
        "verdict": hrv_readiness["verdict"],
        "days_below": days_below,
        "rolling_mean_ms": hrv_readiness.get("rolling_mean_ms"),
        "band_low_ms": hrv_readiness.get("band_low_ms"),
        "band_high_ms": hrv_readiness.get("band_high_ms"),
    }


def _compute_weekly_stats(
    wellness_history: list[dict], today: date
) -> list[dict]:
    stats: list[dict] = []
    for w in range(3, -1, -1):
        from_date = (today - timedelta(days=(w + 1) * 7)).isoformat()
        to_date = (today - timedelta(days=w * 7)).isoformat()
        week_slice = [
            d
            for d in wellness_history
            if from_date <= d.get("id", "") <= to_date and d.get("ctl") is not None
        ]

        avg_ctl = "-"
        if week_slice:
            avg_ctl = f"{sum(d['ctl'] for d in week_slice) / len(week_slice):.1f}"

        hrv_slice = [d for d in week_slice if d.get("hrv") is not None]
        avg_hrv = "-"
        if hrv_slice:
            avg_hrv = f"{sum(d['hrv'] for d in hrv_slice) / len(hrv_slice):.0f}"

        stats.append({"label": f"KW-{w + 1}", "avgCTL": avg_ctl, "avgHRV": avg_hrv})
    return stats


def _analyze_load_cycle(weekly_stats: list[dict]) -> str:
    ctl_values = [_safe_float(w["avgCTL"]) for w in weekly_stats]

    load_weeks_in_row = 0
    unplanned_low_weeks = 0

    for i in range(1, len(ctl_values)):
        prev, curr = ctl_values[i - 1], ctl_values[i]
        if prev < MIN_CTL or curr < MIN_CTL:
            continue

        change_pct = (curr - prev) / prev

        if change_pct >= -TOLERANCE_PCT:
            load_weeks_in_row += 1
            unplanned_low_weeks = 0
        elif -DELOAD_PCT <= change_pct < -TOLERANCE_PCT:
            load_weeks_in_row += 1
            unplanned_low_weeks += 1
        else:
            load_weeks_in_row = 0
            unplanned_low_weeks = 0

    if load_weeks_in_row >= 3:
        if unplanned_low_weeks > 0:
            return (
                f"⚠️ {load_weeks_in_row} weeks of load cycle"
                f" — {unplanned_low_weeks} of them with a time-shortage dip"
                " (no real deload) — recovery week recommended"
            )
        return (
            f"⚠️ {load_weeks_in_row} consecutive load weeks"
            " — recovery week recommended"
        )
    if unplanned_low_weeks > 0:
        return (
            "🟡 load cycle with a small dip (time shortage)"
            " — next week ramp up gradually, no full jump"
        )
    return "✅ Load cycle unremarkable"


def _compute_ctl_trend(weekly_stats: list[dict]) -> str:
    parts: list[str] = []
    for i, w in enumerate(weekly_stats):
        curr = _safe_float(w["avgCTL"])
        delta = ""
        if i > 0:
            prev = _safe_float(weekly_stats[i - 1]["avgCTL"])
            if prev >= MIN_CTL and curr >= MIN_CTL:
                pct = ((curr - prev) / prev) * 100
                if pct < -TOLERANCE_PCT * 100:
                    if pct >= -DELOAD_PCT * 100:
                        delta = f" (⚡-{abs(pct):.0f}% dip)"
                    else:
                        delta = f" (🔻-{abs(pct):.0f}% reset)"
        parts.append(f"{w['label']}: CTL {w['avgCTL']} | HRV Ø {w['avgHRV']}{delta}")
    return " → ".join(parts)


def _correct_cardiac_drift(zone_times: list[int], moving_time_secs: int) -> list[int]:
    """Redistribute warm-up cardiac-drift seconds (Z3 only) back to Z2.

    Cardiac drift on easy runs: in the first 5–15 min HR is elevated during
    the WU and slips into Z3 despite Z2 pace. The correction removes up to
    600s from Z3 and shifts them into Z2.

    Important (bug fix from real application): Z4/Z5 are NOT touched — on
    threshold / interval / race activities the Z4/Z5 time is real intensity
    work, not drift. Previously the highest zones were blanket-subtracted,
    which systematically under-counted threshold stimuli (e.g. 13 min Z4 →
    displayed as 3 min).

    Additionally: skip the correction when the activity has substantial
    Z4/Z5 share (>5%) — that indicates an intensity session, whose Z3
    portion is then also intentional (tempo / interval rest), not WU drift.
    """
    WARMUP_SECS = 600
    DRIFT_SOURCE_ZONE = 2  # Z3 (0-indexed) — typical drift zone
    TARGET_ZONE = 1  # Z2 (0-indexed)
    INTENSITY_THRESHOLD_PCT = 0.05  # >5% Z4+Z5 → activity is an intensity session

    if moving_time_secs < 1200 or len(zone_times) < 5:
        return zone_times

    total = sum(zone_times)
    if total <= 0:
        return zone_times

    intensity_ratio = (zone_times[3] + zone_times[4]) / total
    if intensity_ratio > INTENSITY_THRESHOLD_PCT:
        # Threshold / interval / race session — Z3 is intentional, no drift correction
        return zone_times

    adjusted = list(zone_times)
    take = min(adjusted[DRIFT_SOURCE_ZONE], WARMUP_SECS)
    adjusted[DRIFT_SOURCE_ZONE] -= take
    adjusted[TARGET_ZONE] += take
    return adjusted


def _compute_zone_distribution(activities: list[dict]) -> str:
    cardio = [a for a in activities if a.get("type") in CARDIO_TYPES]
    with_hr = [
        a for a in cardio if any(s > 0 for s in (a.get("icu_hr_zone_times") or []))
    ]
    without_hr = [a for a in cardio if a not in with_hr]

    zone_sums = [0, 0, 0, 0, 0]
    for a in with_hr:
        raw = list(a.get("icu_hr_zone_times", []))[:5]
        corrected = _correct_cardiac_drift(raw, a.get("moving_time", 0))
        for i, secs in enumerate(corrected):
            zone_sums[i] += secs

    total_secs = sum(zone_sums)
    total_min_no_hr = sum(
        round(a.get("moving_time", 0) / 60) for a in without_hr
    )

    if total_secs == 0:
        return "No HR data available"

    total_min_hr = round(total_secs / 60)
    zones_str = " | ".join(
        f"Z{i + 1}: {round(s / total_secs * 100)}%" for i, s in enumerate(zone_sums)
    )
    result = f"{zones_str} ({total_min_hr} min with HR data)"

    if without_hr:
        missing = ", ".join(
            f"{a.get('start_date_local', '')[:10]} {a.get('type', '')}"
            for a in without_hr
        )
        result += (
            f"\n⚠️ {len(without_hr)} run/ride without HR data"
            f" ({total_min_no_hr} min): {missing}"
        )

    return result


# Default Z4+Z5 threshold for hard-stimulus detection (8 min)
HARD_STIMULUS_MIN_Z4_Z5_SECS = 8 * 60


def _z4_z5_secs(activity: dict) -> float:
    """Total seconds spent in Z4+Z5 according to icu_hr_zone_times."""
    zone_times = list(activity.get("icu_hr_zone_times") or [])[:5]
    return (zone_times[3] if len(zone_times) > 3 else 0) + (
        zone_times[4] if len(zone_times) > 4 else 0
    )


def is_hard_stimulus(
    activity: dict, min_z4_z5_secs: float = HARD_STIMULUS_MIN_Z4_Z5_SECS
) -> bool:
    """Shared hard-session detection used by every intensity consumer.

    An activity counts as a hard stimulus when ANY of:
      - tag "intervals" present
      - Z4+Z5 time ≥ ``min_z4_z5_secs``
      - ``workout_type == "RACE"``

    The checks are independent — a tagged activity without an "intervals"
    tag still qualifies via its Z4/Z5 time or RACE workout_type (previously
    the tag check short-circuited and made the zone fallback unreachable
    for tagged activities).
    """
    tags = [str(t).lower() for t in (activity.get("tags") or [])]
    if "intervals" in tags:
        return True
    if str(activity.get("workout_type") or "").upper() == "RACE":
        return True
    return _z4_z5_secs(activity) >= min_z4_z5_secs


def _compute_weekly_hard_reize_balance(activities: list[dict], today: date) -> str:
    """Audit the rolling-7-day hard-stimulus balance against the 2-stimulus weekly strategy.

    Weekly strategy per training_paradigms.md §93–96:
      - Stimulus 1: run threshold (Z4) — 1×/week
      - Stimulus 2: bike VO2max (Z5) — 1×/week (cross-training, spares Achilles)
    A complete week = both stimuli present. The output flags what's done and
    what's still open, so the coach's weekly outlook can't accidentally
    schedule two run-Z4 sessions and miss the bike-VO2max slot.

    Rolling 7d (today - 6 to today) instead of ISO Mon-Sun week — avoids the
    hard cut at the week boundary (a Saturday bike-VO2max would silently
    disappear from view on the following Monday).

    Hard-stimulus detection (per activity) — shared helper is_hard_stimulus:
      - Run/VirtualRun → "run hard": tag "intervals" OR Z4+Z5 ≥ 8 min OR RACE
      - Ride/VirtualRide → "ride hard": tag "intervals" OR Z4+Z5 ≥ 8 min OR RACE
    """
    window_start = today - timedelta(days=6)
    window_end = today

    run_hard: list[dict] = []
    ride_hard: list[dict] = []
    MIN_Z4_Z5_SECS = HARD_STIMULUS_MIN_Z4_Z5_SECS

    for a in activities:
        d_str = (a.get("start_date_local") or "")[:10]
        try:
            act_date = date.fromisoformat(d_str)
        except (ValueError, TypeError):
            continue
        if act_date < window_start or act_date > window_end:
            continue

        a_type = a.get("type")
        z4_z5 = _z4_z5_secs(a)
        if not is_hard_stimulus(a, min_z4_z5_secs=MIN_Z4_Z5_SECS):
            continue

        descriptor = {
            "date": act_date,
            "name": a.get("name", ""),
            "z4_z5_min": round(z4_z5 / 60),
        }
        if a_type in {"Run", "VirtualRun"}:
            run_hard.append(descriptor)
        elif a_type in {"Ride", "VirtualRide"}:
            ride_hard.append(descriptor)

    def _fmt(items: list[dict]) -> str:
        if not items:
            return "open"
        items_sorted = sorted(items, key=lambda x: x["date"])
        parts = []
        for i in items_sorted:
            extra = f" (Z4+Z5 {i['z4_z5_min']} min)" if i["z4_z5_min"] >= 8 else ""
            parts.append(f"{i['date'].isoformat()} \"{i['name']}\"{extra}")
        return "; ".join(parts)

    run_status = "✓" if run_hard else "⚠️"
    ride_status = "✓" if ride_hard else "⚠️"

    return (
        f"Hard-stimuli balance (rolling 7d {window_start.isoformat()}–{window_end.isoformat()}, "
        f"2-stimuli strategy per training_paradigms.md §93–96):\n"
        f"{run_status} Run threshold/VO2max: {_fmt(run_hard)}\n"
        f"{ride_status} Bike VO2max: {_fmt(ride_hard)}"
    )


def _compute_meso_load_trend(
    activities: list[dict],
    today: date,
    ctl: float | None = None,
    deload_ctl_threshold: float | None = None,
    tsb_recent: list[float] | None = None,
) -> str:
    """
    Analyse 4 rolling 7-day windows (W-4 to W-1) for progressive load build-up.

    Gates (in order; on a hit, no deload signal is emitted):
    1. CTL < deload_ctl_threshold → rebuild phase, systemic fatigue not
       accumulated. Default 24 (framework), override via
       `deload_ctl_threshold` from athlete_status.md.
    2. Last week < MIN_LAST_WEEK_LOAD → too little load for a deload call
    3. "Rebuild after pause" → first 2 weeks very low (holiday / illness),
       then a jump — no real build block, deload not yet needed
    """
    DELOAD_TOLERANCE = 0.10
    CTL_REBUILD_THRESHOLD = deload_ctl_threshold if deload_ctl_threshold is not None else 24
    MIN_LAST_WEEK_LOAD = 60         # TSS/week — below this threshold no meaningful deload
    REBUILD_FIRST_HALF_RATIO = 0.35  # first-2-weeks avg < last week × 35% → pause pattern

    week_loads: list[int] = []
    for weeks_ago in range(4, 0, -1):  # W-4, W-3, W-2, W-1
        window_end = today - timedelta(days=(weeks_ago - 1) * 7 + 1)
        window_start = window_end - timedelta(days=6)
        load = sum(
            int(a.get("icu_training_load") or 0)
            for a in activities
            if window_start.isoformat() <= (a.get("start_date_local") or "")[:10] <= window_end.isoformat()
        )
        week_loads.append(load)

    loads_str = "→".join(str(w) for w in week_loads)

    if all(w == 0 for w in week_loads):
        return f"No training-load data ({loads_str})"

    # Gate 1: CTL too low — athlete is in a rebuild
    if ctl is not None and ctl < CTL_REBUILD_THRESHOLD:
        return (
            f"🔄 Rebuild (CTL {ctl:.1f} < {CTL_REBUILD_THRESHOLD}): {loads_str} "
            f"— recovery week not yet relevant, build takes priority"
        )

    # Gate 2: Absolute load last week too low
    if week_loads[-1] < MIN_LAST_WEEK_LOAD:
        return (
            f"📊 Low volume last week: {loads_str} — no deload needed"
        )

    # Gate 3: Rebuild-after-pause pattern
    first_half_avg = (week_loads[0] + week_loads[1]) / 2
    if (
        first_half_avg < week_loads[-1] * REBUILD_FIRST_HALF_RATIO
        and first_half_avg < MIN_LAST_WEEK_LOAD
    ):
        return (
            f"🔄 Build after pause: {loads_str} "
            f"— early weeks low due to pause, no accumulated build block"
        )

    # TSB-based override — independent of the 4-week progression check
    # (Coggan/Allen: TSB < -30 = diminishing returns; -25 = accumulation risk)
    if tsb_recent is not None and len(tsb_recent) >= 7:
        tsb_7d_mean = sum(tsb_recent[-7:]) / 7
        tsb_below_30_count = sum(1 for v in tsb_recent[-3:] if v < -30)
        if tsb_7d_mean < -25 or tsb_below_30_count >= 3:
            return (
                f"⚠️ TSB trigger: 7d-mean {tsb_7d_mean:.1f} / {tsb_below_30_count} days < -30 "
                f"— recovery week recommended regardless of load progression"
            )

    # Check whether all weeks are progressive (no week >10% below predecessor)
    is_progressive = True
    for i in range(1, len(week_loads)):
        prev = week_loads[i - 1]
        curr = week_loads[i]
        if prev > 0 and curr < prev * (1 - DELOAD_TOLERANCE):
            is_progressive = False
            break

    if is_progressive and week_loads[-1] > 0:
        return (
            f"📈 Progressive build 4W: {loads_str} — "
            f"⚠️ recovery week recommended (reduce intensity / volume)"
        )
    else:
        return f"✅ Implicit recovery present: {loads_str} — no structural deload needed"


def _find_last_intense_session(activities: list[dict]) -> dict | None:
    # activities is sorted oldest-first — iterate newest-first to find the
    # most recent intense session, not the first one ever recorded.
    # Detection is shared with _compute_weekly_hard_reize_balance via
    # is_hard_stimulus (tag OR Z4/Z5 time OR RACE) — a tagged activity with
    # high Z4/Z5 time but no "intervals" tag still counts as intense.
    for a in reversed(activities):
        moving_min = round(a.get("moving_time", 0) / 60)
        if moving_min < 25:
            continue
        if is_hard_stimulus(a, min_z4_z5_secs=120):
            return a

    return None


def _find_last_rest_day(activities: list[dict], today: date) -> str:
    activity_dates = {
        a.get("start_date_local", "")[:10] for a in activities
    }
    for i in range(1, 8):
        d = (today - timedelta(days=i)).isoformat()
        if d not in activity_dates:
            return "yesterday" if i == 1 else f"{i} days ago"
    return "no rest day in the last 7 days"


def _days_since(activity: dict | None, today: date) -> int:
    if not activity:
        return 99
    start = activity.get("start_date_local", "")[:10]
    if not start:
        return 99
    try:
        return (today - date.fromisoformat(start)).days
    except ValueError:
        return 99


def _compute_intensity_readiness(
    hrv: float | None,
    hrv_baseline: str,
    tsb: float | str,
    days_since_intense: int,
    hrv_cv: float | None = None,
    combined_overload_signal: dict | None = None,
    hrv_readiness: dict | None = None,
) -> str:
    # Combined HRV+RHR overload trumps single-signal logic — when both
    # autonomic markers fire for 3+ days the readiness is unambiguously red.
    if combined_overload_signal is not None:
        verdict = combined_overload_signal.get("verdict")
        days = combined_overload_signal.get("days", 0)
        if verdict == "deload":
            return f"🔴 No — combined HRV/RHR overload ({days}d, deload trigger)"
    # Band `hold` (7d-rolling ln-rMSSD below the 60d band for 3+ consecutive
    # days) is the sustained HRV-only fatigue signal — red, second only to the
    # combined HRV+RHR dual signal above. The single-day SWC/5% check below
    # stays as the early-warning layer.
    if hrv_readiness is not None and hrv_readiness.get("verdict") == "hold":
        days = hrv_readiness.get("days_below", 0)
        return f"🔴 No — HRV 7d-rolling below band ({days}d, hold)"
    if hrv is not None and hrv_baseline != "-":
        baseline_val = float(hrv_baseline)
        if hrv_cv is not None:
            # Plews/Buchheit SWC-based threshold: 1.0 × within-athlete CV
            threshold = baseline_val * (1 - hrv_cv / 100)
            if hrv < threshold:
                return f"🔴 No — HRV below baseline (SWC-based, CV {hrv_cv:.1f}%)"
        else:
            # Fallback: fixed 5% below baseline
            if hrv < baseline_val * 0.95:
                return "🔴 No — HRV below baseline"
    if tsb != "-" and float(tsb) < -10:
        return "🔴 No — TSB too negative"
    if days_since_intense < 2:
        return "🟡 Too early — last intense session <2 days ago"
    # Band `watch` (1-2 days below band) is a soft yellow when other gates are green.
    if hrv_readiness is not None and hrv_readiness.get("verdict") == "watch":
        days = hrv_readiness.get("days_below", 0)
        return f"🟡 Borderline — HRV 7d-rolling below band ({days}d, watch)"
    # "watch" verdict on combined signal surfaces as a soft yellow when other
    # gates are green — readiness moves from "yes" to "borderline".
    if (
        combined_overload_signal is not None
        and combined_overload_signal.get("verdict") == "watch"
    ):
        days = combined_overload_signal.get("days", 0)
        return f"🟡 Borderline — HRV/RHR drift watch ({days}d)"
    if days_since_intense >= 3:
        return f"🟢 Yes — last intense session {days_since_intense} days ago"
    return "🟡 Borderline — coach's discretion"


def _format_weather(weather_data: dict, today: date) -> str:
    forecasts = (
        weather_data.get("forecasts", [{}])[0].get("daily", [])
        if weather_data.get("forecasts")
        else []
    )
    today_str = today.isoformat()
    today_wx = next((d for d in forecasts if d.get("id") == today_str), None)

    if not today_wx:
        return "No weather data available"

    temp_max = _fmt(today_wx.get("temp", {}).get("max"), "°C")
    temp_min = _fmt(today_wx.get("temp", {}).get("min"), "°C")
    feels_day = _fmt(today_wx.get("feels_like", {}).get("day"), "°C")
    precip = today_wx.get("rain") or today_wx.get("snow") or 0
    wind_speed = _fmt(today_wx.get("wind_speed"), " km/h")
    # OpenWeather description is third-party text → sanitize for defense-in-depth.
    from app.utils.sanitize import escape_for_prompt
    wx_desc_raw = (today_wx.get("weather") or [{}])[0].get("description", "-")
    wx_desc = escape_for_prompt(wx_desc_raw, max_len=80) if wx_desc_raw else "-"

    parts = [
        wx_desc,
        f"{temp_min}–{temp_max} (feels like {feels_day})",
        f"Wind {wind_speed}",
    ]
    if precip > 0:
        parts.append(f"Precipitation {precip} mm")
    if precip > 5:
        parts.append("⚠️ Indoor preferred")
    try:
        if today_wx.get("temp", {}).get("max") is not None and float(
            today_wx["temp"]["max"]
        ) < 5:
            parts.append("❄️ Cold — intervals possibly indoor")
    except (ValueError, TypeError):
        pass

    return ", ".join(parts)


_WEEKDAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _summarize_today_workouts(events: list[dict], today: date) -> list[dict]:
    """Return compact summaries of today's planned WORKOUT events.

    `name` is athlete-roundtrip-controlled via intervals.icu event edits and
    Strava description sync → sanitize at this write boundary.
    """
    from app.utils.sanitize import escape_for_prompt

    result = []
    today_str = today.isoformat()
    for e in events:
        if e.get("category") != "WORKOUT":
            continue
        start = (e.get("start_date_local") or "")[:10]
        if start != today_str:
            continue
        raw_name = e.get("name", "") or ""
        result.append({
            "id": e.get("id"),
            "name": escape_for_prompt(raw_name, max_len=120) if raw_name else raw_name,
            "type": e.get("type", ""),
            "duration_min": round(e.get("moving_time", 0) / 60) if e.get("moving_time") else None,
            "tags": e.get("tags") or [],
        })
    return result


def _format_events(events: list[dict], today: date) -> str:
    # eventList carries the same NOTE sources as _format_notes (plus RACE_*).
    # Without sanitisation here, NOTE content would bypass the athleteFeedback
    # guard via the eventList path → same injection vector.
    from app.utils.sanitize import escape_for_prompt

    allowed = {"RACE_A", "RACE_B", "RACE_C", "NOTE"}
    lines: list[str] = []
    for e in events:
        if e.get("category") not in allowed:
            continue
        d_str = (e.get("start_date_local") or "-")[:10]
        name = escape_for_prompt(e.get("name", "-") or "-", max_len=120)
        cat = e.get("category", "-")
        raw_desc = e.get("description") or ""
        desc_clean = escape_for_prompt(raw_desc, max_len=200) if raw_desc else ""
        desc = f" ({desc_clean})" if desc_clean else ""
        try:
            event_date = date.fromisoformat(d_str)
            days_until = (event_date - today).days
            wd = _WEEKDAY_EN[event_date.weekday()]
            if days_until < 0:
                rel = f"{abs(days_until)}d ago"
            elif days_until == 0:
                rel = "today"
            elif days_until == 1:
                rel = "tomorrow"
            else:
                rel = f"in {days_until}d"
            # ISO week comparison
            this_week_mon = today - timedelta(days=today.weekday())
            event_week_mon = event_date - timedelta(days=event_date.weekday())
            week_diff = (event_week_mon - this_week_mon).days // 7
            if week_diff == 0:
                week_label = "this week"
            elif week_diff == 1:
                week_label = "next week"
            else:
                week_label = f"in {week_diff} weeks"
            timing = f"{wd}, {rel}, {week_label}"
        except (ValueError, TypeError):
            timing = "?"
        lines.append(f"{d_str} ({timing}) | {cat} | {name}{desc}")
    return "\n".join(lines) if lines else "No upcoming events"


_RELATIVE_DATE_MAP = {
    # German aliases (athlete writes notes in German)
    r"\bheute\b": 0,
    r"\bmorgen\b": 1,
    r"\bübermorgen\b": 2,
    r"\bgestern\b": -1,
    r"\bvorgestern\b": -2,
    # English aliases (athlete writes notes in English)
    r"\btoday\b": 0,
    r"\btomorrow\b": 1,
    r"\bday after tomorrow\b": 2,
    r"\byesterday\b": -1,
    r"\bday before yesterday\b": -2,
}


def _resolve_relative_dates(text: str, note_date: date) -> str:
    """Replace relative date words in note text with absolute dates (YYYY-MM-DD)."""
    import re

    result = text
    for pattern, delta in _RELATIVE_DATE_MAP.items():
        resolved = (note_date + timedelta(days=delta)).isoformat()
        result = re.sub(pattern, resolved, result, flags=re.IGNORECASE)
    return result


def _format_notes(notes: list[dict]) -> str:
    from app.utils.sanitize import escape_for_prompt
    lines: list[str] = []
    for note in notes:
        if note.get("category") != "NOTE":
            continue
        d = (note.get("start_date_local") or "-")[:10]
        # name + desc come from intervals.icu NOTEs (athlete-controlled, but
        # also routinely written back by the coach itself) → escape both before
        # they flow into the planner prompt as athleteFeedback.
        name = escape_for_prompt(note.get("name", ""), max_len=120)
        desc_raw = note.get("description", "") or ""
        try:
            note_date = date.fromisoformat(d)
            desc_raw = _resolve_relative_dates(desc_raw, note_date)
        except (ValueError, TypeError):
            pass
        desc_clean = escape_for_prompt(desc_raw, max_len=200)
        desc = f" | {desc_clean}" if desc_clean else ""
        lines.append(f"{d} | {name}{desc}")
    return "\n".join(lines) if lines else "No athlete feedback"


# Aliases for local use (canonical source: app.analytics.recovery)
_NINJA_PILLAR_KEYWORDS = NINJA_PILLAR_KEYWORDS
_NINJA_TAG_TO_PILLAR = NINJA_TAG_TO_PILLAR


def _strip_warmup_cooldown(notes: str) -> str:
    """Return only the main-set portion of a workout description.

    Pillar detection must not trigger on warm-up / cool-down content
    (e.g. `Reverse Wrist Curls 1×12 (wrist build-up)` in a Core session
    warm-up would otherwise classify the whole session as Grip). Strategy:
    keep only the text between the main-set marker (inclusive) and
    `COOL-DOWN` / `COOLDOWN` (exclusive). If no main-set marker is
    present, fall back to text *after* the first warm-up block
    (everything below the first occurrence of `WARM-UP`/`WARMUP` +
    newline-skipped block). Both German (`HAUPTTEIL`) and English
    (`MAIN SET` / `MAIN BLOCK`) markers are recognised.
    """
    import re
    lower = notes.lower()
    # Cut off cool-down regardless of mode
    cooldown_match = re.search(r"\bcool[\s\-]?down\b", lower)
    if cooldown_match:
        notes = notes[: cooldown_match.start()]
        lower = lower[: cooldown_match.start()]

    # Primary: cut start at main-set marker (German or English)
    main_match = re.search(r"\b(hauptteil|main\s*set|main\s*block)\b", lower)
    if main_match:
        return notes[main_match.start():]

    # Fallback: strip everything from start to the end of the first warm-up
    # paragraph (warm-up block ends at the first blank line after WARM-UP)
    wu_match = re.search(r"\bwarm[\s\-]?up\b", lower)
    if wu_match:
        # Look for the next blank line after the warm-up marker, skip past
        # the warm-up block. If there's no obvious end marker, conservatively
        # skip the first 5 lines after the WARM-UP heading.
        wu_end = lower.find("\n\n", wu_match.end())
        if wu_end == -1:
            return notes  # malformed — fall back to full scan
        return notes[wu_end:]
    return notes


def _detect_ninja_pillar(activity: dict) -> list[str]:
    """Detect which ninja pillars were trained in an activity.

    Checks both tags (fast path) and coaching_notes keywords (catches Core
    exercises embedded in Upper Body sessions, etc.). Warm-up and cool-down
    portions of coaching_notes are stripped before the keyword scan — a
    warm-up wrist-mobility exercise must not count as a Grip-pillar session.
    """
    pillars: set[str] = set()
    tags = [str(t).lower() for t in (activity.get("tags") or [])]

    # Tag-based detection
    for tag, tag_pillars in _NINJA_TAG_TO_PILLAR.items():
        if tag in tags:
            pillars.update(tag_pillars)

    # Keyword-based detection in coaching_notes / event_description
    # (catches unlabelled pillars, e.g. Core exercises embedded in Upper Body sessions)
    raw_notes = (activity.get("coaching_notes") or activity.get("event_description") or "")
    main_notes = _strip_warmup_cooldown(raw_notes).lower()
    for p, keywords in _NINJA_PILLAR_KEYWORDS.items():
        if p not in pillars and any(kw in main_notes for kw in keywords):
            pillars.add(p)

    return sorted(pillars)


def _compute_last_ninja_pillar_history(activities: list[dict], n: int = 5) -> str:
    """Return a human-readable history of the last N ninja sessions with their pillars.

    This allows the planner to see which pillars were *actually* trained (not
    just what the tags say), so it can correctly rotate through the 5 ninja
    pillars.
    """
    # Pillar-relevant tags — sessions without an explicit "ninja" tag but with
    # a pillar tag (e.g. "core", "grip") are also captured, so Core+Balance
    # sessions without a ninja tag are not missed.
    pillar_tags = set(_NINJA_TAG_TO_PILLAR.keys()) | {"ninja"}

    ninja_sessions: list[str] = []
    for a in reversed(activities):
        tags = [str(t).lower() for t in (a.get("tags") or [])]
        pillars = _detect_ninja_pillar(a)
        if not pillars and not (pillar_tags & set(tags)):
            continue
        if not pillars:
            # Tag matched, but pillar detection empty — note as unknown
            pillar_str = "unknown"
        else:
            pillar_str = "+".join(pillars)
        d_str = (a.get("start_date_local") or "")[:10]
        name = a.get("name") or "Ninja"
        ninja_sessions.append(f"{d_str} | {name} | pillars: {pillar_str}")
        if len(ninja_sessions) >= n:
            break

    if not ninja_sessions:
        return "Ninja pillars history: no ninja sessions in recent activities"

    lines = ["Ninja pillars history (last sessions, oldest first):"]
    lines.extend(reversed(ninja_sessions))
    lines.append(
        "→ Next pillar: pick the pillar that lies furthest back and is not blocked today"
    )
    return "\n".join(lines)


_RECOVERY_RULES = RECOVERY_RULES

# (tags_required, warn_days, red_days, label, min_duration_min)
# min_duration_min: minimum activity duration to qualify as a real stimulus for
# this category. Short companion blocks tagged with the category (mini warm-ups,
# pre-fatigue stubs, daily physio routines) would otherwise falsely reset the
# due-counter even though no real pillar stimulus happened. Thresholds align
# with the tagging convention in training_paradigms.md:
#   - Plyo standalone >15 min; ninja session ≥15 min triggers specialist
#   - Leg strength: plyo activation (~16 min, tagged "plyo"+"legs") must NOT
#     reset the leg-strength counter — threshold at 20 min.
#   - Core / mobility / balance: short mini blocks (<10 min) are companion
#     stimuli, not standalone stimuli.
# Trigger tags use the new canonical English form ("legs"). Legacy "beine"-
# tagged sessions still match thanks to `canonicalise_tags()` at the read
# site below.
_COMPLEMENTARY_DUE: list[tuple[list[str], int, int, str, int]] = [
    (["legs"],     5, 7,  "Legs",     20),
    (["plyo"],     3, 5,  "Plyo",     15),
    (["balance"],  5, 8,  "Balance",   8),
    (["mobility"], 3, 5,  "Mobility",  8),
    (["core"],     4, 6,  "Core",     10),
    (["ninja"],    2, 3,  "Ninja",    15),
]


# Config files already warned about as missing — warn once per process, not
# on every context build.
_missing_config_warned: set[str] = set()


def _read_optional_config(filename: str) -> str | None:
    """Read a config file via the standard CONFIG_DIR/CONFIG_FALLBACK resolution.

    Returns None (with a one-time logger.warning) when the file exists in
    neither location — callers degrade to their feature-off default. Path
    resolution goes through app.utils.paths so wrapper setups (COACH_HOME /
    CONFIG_DIR env) are honoured; a path derived from __file__ would point
    inside the framework checkout and silently disable the feature for every
    wrapper consumer.
    """
    from app.utils.paths import resolve_config

    try:
        path = resolve_config(filename)
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        if filename not in _missing_config_warned:
            _missing_config_warned.add(filename)
            logger.warning(
                "config %s not found in CONFIG_DIR or CONFIG_FALLBACK — "
                "dependent context feature disabled",
                filename,
            )
        return None


def _achilles_plyo_locked() -> bool:
    """Check if the Achilles rehab protocol still locks plyometrics (phase 1 or 2 active).

    Phase 1/2 block bilateral plyometrics (pogo, squat jump, box jump) — only
    single-leg hops and balance plyo allowed. Phase 3 = cleared (full plyo
    load allowed again). When phase 1 or 2 are active, the plyo-due trigger
    should NOT be emitted as '🔴 overdue', but as a qualified hint (otherwise
    the planner is pushed toward forbidden exercises).

    In phase 3 (cleared) the function returns False, plyo is marked due
    normally. Re-engages on reactivation of phase 1/2.
    """
    import re as _re

    content = _read_optional_config("athlete_static.md")
    if content is None:
        return False
    return bool(_re.search(r"Achillessehne.*Phase\s*[12]\s*aktiv", content, _re.IGNORECASE))


def _compute_complementary_due(activities: list[dict], today: date) -> str | None:
    """Emit 🟡/🔴 due-warnings for complementary training categories.

    Checks the last activity date per category tag and warns when overdue.
    Only emits output for categories that are at warn or red threshold.

    Special case Plyo: as long as Achilles phase 1 or 2 is active
    (athlete_static.md), the plyo limit is NOT flagged as '🔴 overdue' —
    bilateral jumps are blocked by the rehab protocol. Instead, emit a
    qualified hint pointing to single-leg / balance plyo, so the planner
    is not pushed toward forbidden exercises (pogo, box jump, squat jump).
    With phase 3 active (plyo cleared) → no plyo lock, normal due logic.
    """
    LOOKBACK_DAYS = 60
    cutoff = today - timedelta(days=LOOKBACK_DAYS)

    plyo_locked = _achilles_plyo_locked()

    lines: list[str] = []

    for tags, warn_days, red_days, label, min_duration_min in _COMPLEMENTARY_DUE:
        last_date: date | None = None

        for a in reversed(activities):
            d_str = (a.get("start_date_local") or "")[:10]
            try:
                act_date = date.fromisoformat(d_str)
            except (ValueError, TypeError):
                continue
            if act_date < cutoff:
                break
            # canonicalise_tags expands legacy "beine" → also "legs" so the
            # rule trigger (which uses "legs") matches both forms.
            act_tags = canonicalise_tags(a.get("tags"))
            if not all(t in act_tags for t in tags):
                continue
            if min_duration_min > 0:
                duration_min = (a.get("moving_time") or 0) / 60
                if duration_min < min_duration_min:
                    continue
            last_date = act_date
            break

        if last_date is None:
            days_ago = LOOKBACK_DAYS + 1
        else:
            days_ago = (today - last_date).days

        # Plyo + Achilles rehab phase 1/2 → qualified hint instead of 🔴/🟡
        if label == "Plyo" and plyo_locked and days_ago >= warn_days:
            last_str = last_date.isoformat() if last_date else f">{LOOKBACK_DAYS}d"
            lines.append(
                f"🟡 Plyo restricted by Achilles rehab (phase 1/2) — only "
                f"single-leg hops or balance plyo, NO bilateral jumps "
                f"(box jump, pogo, squat jump). Last plyo session: {last_str}."
            )
            continue

        if days_ago >= red_days:
            last_str = last_date.isoformat() if last_date else f">{LOOKBACK_DAYS}d"
            lines.append(
                f"🔴 {label} overdue — last session {last_str} "
                f"({min(days_ago, LOOKBACK_DAYS)}+ days ago, limit {red_days}d)"
            )
        elif days_ago >= warn_days:
            lines.append(
                f"🟡 {label} due soon — last session {last_date.isoformat()} "  # type: ignore[union-attr]
                f"({days_ago}d ago, warn from {warn_days}d)"
            )

    if not lines:
        return None
    return "Complementary due:\n" + "\n".join(lines)


# Re-evaluation cadence — exercise selection is re-challenged at natural
# boundaries (recovery week, periodization phase change, staleness), NOT
# every session. The helpers below emit a cheap advisory flag: it never
# blocks and never does the re-evaluation itself. When the flag is present
# the /training flow runs the `exercise-reviewer` agent before the
# specialists. The mechanic is generic; every threshold and the phase
# schedule come from config/ (athlete_status.md re-eval block) so no
# athlete specifics live in framework code.
_REEVAL_STALENESS_WEEKS_DEFAULT = 6


def _parse_reeval_config(status_content: str | None) -> dict:
    """Parse the re-eval trigger config from athlete_status.md.

    Returns ``{staleness_weeks, last_reeval_phase, phases}`` where ``phases``
    is a list of ``(name, start_date, end_date)``. A missing block degrades
    to staleness-only defaults (no phase schedule → phase trigger disabled).
    """
    import re as _re

    from app.utils.date_parse import parse_config_date

    weeks = _REEVAL_STALENESS_WEEKS_DEFAULT
    last_phase: str | None = None
    phases: list[tuple[str, date, date]] = []
    if not status_content:
        return {"staleness_weeks": weeks, "last_reeval_phase": None, "phases": phases}

    m = _re.search(r"\*\*staleness_weeks:\*\*\s*(\d+)", status_content)
    if m:
        try:
            weeks = int(m.group(1))
        except ValueError:
            pass

    m = _re.search(r"\*\*last_reeval_phase:\*\*\s*(.+)", status_content)
    if m:
        cand = m.group(1).strip()
        if cand and cand not in ("—", "-", "–"):
            last_phase = cand

    # Phase schedule lines: "Name | YYYY-MM-DD | YYYY-MM-DD" anywhere in the
    # file. A machine-readable mirror of the periodization table in
    # competition_plan.md — the human table stays the documentation source.
    for line in status_content.splitlines():
        pm = _re.match(
            r"\s*([^|]+?)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(\d{4}-\d{2}-\d{2})\s*$",
            line,
        )
        if not pm:
            continue
        start = parse_config_date(pm.group(2))
        end = parse_config_date(pm.group(3))
        if start and end and end >= start:
            phases.append((pm.group(1).strip(), start, end))

    return {"staleness_weeks": weeks, "last_reeval_phase": last_phase, "phases": phases}


def _current_phase(phases: list[tuple[str, date, date]], today: date) -> str | None:
    """Return the phase whose [start, end] window contains today, else None."""
    for name, start, end in phases:
        if start <= today <= end:
            return name
    return None


def _parse_stale_exercises(
    prog_content: str | None, today: date, max_weeks: int
) -> list[str]:
    """Return exercise names whose ``letzte-Re-Eval`` is older than max_weeks.

    Reads the per-exercise Re-Eval block in exercise_progressions.md:
    ``- **Re-Eval:** dient=… | eingeführt=… | letzte-Re-Eval=YYYY-MM-DD | Status=keep``
    The exercise name is the nearest preceding ``##``–``####`` heading.
    Entries with ``Status=retire`` are skipped (no longer in rotation).
    Pure date logic — robust against the canonical-name gap between
    ``exercises_seen`` keywords and progression headings.
    """
    import re as _re

    from app.utils.date_parse import parse_config_date

    if not prog_content:
        return []
    cutoff_days = max_weeks * 7
    stale: list[str] = []
    current_heading: str | None = None
    for line in prog_content.splitlines():
        h = _re.match(r"^#{2,4}\s+(.+?)\s*$", line)
        if h:
            current_heading = h.group(1).strip()
            continue
        if "Re-Eval:" not in line:
            continue
        dm = _re.search(r"letzte-Re-Eval=\s*([0-9.\-]+)", line)
        if not dm:
            continue
        last = parse_config_date(dm.group(1))
        if last is None:
            continue
        status_m = _re.search(r"Status=\s*(\w+)", line)
        status = status_m.group(1).lower() if status_m else ""
        if status == "retire":
            continue
        if (today - last).days > cutoff_days and current_heading:
            stale.append(current_heading)
    return stale


def _reeval_recovery_active(deload_state: dict | None, today: date) -> bool:
    """True when a recovery week is currently active (and not expired)."""
    if not deload_state:
        return False
    from app.utils.date_parse import parse_config_date

    aktiv = (
        str(deload_state.get("aktiv") or deload_state.get("active") or "nein")
        .strip()
        .lower()
    )
    if aktiv not in ("ja", "yes", "true"):
        return False
    ende = deload_state.get("ende_geplant") or deload_state.get("planned_end") or ""
    ende_date = parse_config_date(ende)
    if ende_date is not None and ende_date < today:
        return False
    return True


def _compute_reeval_trigger(today: date, deload_state: dict | None = None) -> str | None:
    """Emit an advisory exercise-re-evaluation flag at natural boundaries.

    Three OR-combined triggers, each reusing existing data:
      A. recovery week active (``deload_state``) — natural deload boundary
      B. periodization phase change vs. ``last_reeval_phase``
         (phase schedule + anchor in athlete_status.md)
      C. staleness — an exercise's ``letzte-Re-Eval`` in
         exercise_progressions.md is older than ``staleness_weeks``

    Returns a single advisory line, or None when nothing fires. Never
    blocks: when present the /training flow runs the `exercise-reviewer`
    agent before the specialists; otherwise the daily loop is unchanged.
    All thresholds/schedules come from config/ so no athlete specifics
    live here.
    """
    cfg = _parse_reeval_config(_read_optional_config("athlete_status.md"))
    reasons: list[str] = []

    if _reeval_recovery_active(deload_state, today):
        reasons.append("recovery week active")

    phase_now = _current_phase(cfg["phases"], today)
    last_phase = cfg["last_reeval_phase"]
    if phase_now and last_phase and phase_now != last_phase:
        reasons.append(f"phase change {last_phase} → {phase_now}")

    stale = _parse_stale_exercises(
        _read_optional_config("exercise_progressions.md"),
        today,
        cfg["staleness_weeks"],
    )
    if stale:
        shown = ", ".join(stale[:5])
        more = f" (+{len(stale) - 5} more)" if len(stale) > 5 else ""
        reasons.append(
            f"{len(stale)} exercise(s) stale >{cfg['staleness_weeks']}w: {shown}{more}"
        )

    if not reasons:
        return None
    return (
        "🔄 Exercise re-evaluation due (" + "; ".join(reasons) + "). "
        "Run the exercise-reviewer agent before the specialists (see "
        "/training) to re-challenge selection vs. goals + level. "
        "Advisory — does not block."
    )


def _compute_recovery_blocks(activities: list[dict], today: date) -> list[str]:
    """Derive active recovery restrictions from recent activity tags.

    `canonicalise_tags()` is applied so legacy "beine"-tagged sessions also
    satisfy the canonical "legs" trigger (bilingual compat during the
    beine → legs migration).
    """
    blocks: list[str] = []
    for trigger_tags, min_days, label in _RECOVERY_RULES:
        # Find most recent activity that has ALL trigger tags
        for a in reversed(activities):
            act_tags = canonicalise_tags(a.get("tags"))
            if not all(t in act_tags for t in trigger_tags):
                # Also check single-tag rules
                if len(trigger_tags) > 1:
                    continue
            if len(trigger_tags) == 1 and trigger_tags[0] not in act_tags:
                continue
            d_str = (a.get("start_date_local") or "")[:10]
            try:
                act_date = date.fromisoformat(d_str)
            except (ValueError, TypeError):
                continue
            days_ago = (today - act_date).days
            if days_ago == 0:
                # Done today — block starts tomorrow
                unblocked = (act_date + timedelta(days=min_days)).isoformat()
                blocks.append(
                    f"⛔ {label} until {unblocked} (last session today, {min_days}d rule)"
                )
            elif days_ago < min_days:
                unblocked = (act_date + timedelta(days=min_days)).isoformat()
                blocks.append(
                    f"⛔ {label} until {unblocked} (last session {days_ago}d ago, {min_days}d rule)"
                )
            break  # only check most recent matching activity
    return blocks


def _compute_filmtipp_status(today: date) -> str:
    """Parse exercise_log.md and return video lock status for planningConstraints.

    Outputs two lines:
    - Locked (<7 days): exercises with a recent video — no film-tip allowed
    - Candidates: exercises tracked in the log but never filmed (last video: —)

    This pre-computes the decision so agents never have to do date arithmetic.
    """
    import re

    content = _read_optional_config("exercise_log.md")
    if content is None:
        return ""

    VIDEO_LOCK_DAYS = 7
    locked: list[str] = []
    candidates: list[str] = []

    for m in re.finditer(
        r"## (.+?)\n.*?\*\*Letztes Video:\*\* ([^\n|]+)",
        content,
        re.DOTALL,
    ):
        exercise = m.group(1).strip()
        raw_date = m.group(2).strip().split(" ")[0]

        # Skip template placeholder lines
        if exercise.startswith("{") or raw_date.startswith("{"):
            continue

        if raw_date == "—" or raw_date == "-":
            candidates.append(exercise)
            continue

        try:
            video_date = date.fromisoformat(raw_date)
        except ValueError:
            continue

        days_ago = (today - video_date).days
        if 0 <= days_ago < VIDEO_LOCK_DAYS:
            unlock = (video_date + timedelta(days=VIDEO_LOCK_DAYS)).isoformat()
            locked.append(f"{exercise} (video {raw_date}, free from {unlock})")

    parts: list[str] = []
    parts.append("📹 Film-tip status (pre-computed from exercise_log.md):")
    if locked:
        parts.append(f"  ⛔ Locked (<{VIDEO_LOCK_DAYS} days): " + " | ".join(locked))
    else:
        parts.append(f"  ⛔ Locked: none")
    if candidates:
        parts.append(
            "  📽 Candidates (no video, film-tip recommended when planned today): "
            + " | ".join(candidates)
        )
    else:
        parts.append("  📽 Candidates: none (all exercises have videos)")
    parts.append(
        "  → All other exercises (not in exercise_log.md) count as never filmed — "
        "consider a film-tip on complex movements."
    )
    return "\n".join(parts)


# Markers that indicate an exercise mentioned in a description line was NOT
# actually performed (planning-notice, explicit skip, deferred). Without this
# filter, a line like "not today (deliberately out): box jumps (blocked)" would
# trigger a plyo-block, even though no plyometric load happened.
# Both German and English markers are recognised so the detection works
# regardless of the athlete's note-writing language.
_EXCLUSION_MARKERS: tuple[str, ...] = (
    # German
    "nicht heute",
    "bewusst raus",
    "bewusst verschoben",
    "verschoben auf",
    "gesperrt",
    "verboten",
    "weggelassen",
    "ausgesetzt",
    "(raus)",
    "(weggelassen)",
    # English
    "not today",
    "deliberately out",
    "deliberately deferred",
    "deferred to",
    "blocked",
    "forbidden",
    "skipped",
    "omitted",
    "paused",
    "(out)",
    "(skip)",
    "(skipped)",
    "(omitted)",
    # stop-criteria / warnings — never a performed exercise, but routinely
    # name an exercise as a pain/abort trigger (e.g. "⛔ STOP … pain on Dead
    # Hang …"). A keyword hit here is a warning reference, not a load.
    "⛔",
    "stop-kriterium",
    "pain-stop",
    "stop (",
    "stop:",
)


def _line_is_exclusion(line: str) -> bool:
    """Return True if a description line marks an exercise as not-performed.

    Used by _compute_muscle_overlap_blocks to skip planning-notes / explicit
    skip-markers, so keyword hits in "didn't do this today" lines don't
    falsely trigger recovery blocks.
    """
    lower = line.lower()
    return any(marker in lower for marker in _EXCLUSION_MARKERS)


def _exercise_name_portion(line: str) -> str:
    """Return the exercise-name segment of a description line.

    Exercise lines follow a "Name: dose | notes" shape — the performed
    exercise is named *before* the first ':' (which separates name from
    dose). A keyword appearing only in the dose / notes / progression-origin
    part (after the ':' — e.g. "Scapular Pullups: 3×8 … from passive Dead
    Hang →") is a reference, not the performed exercise, and must not trigger
    a recovery block. Falls back to the segment before the first '|', else the
    whole line.
    """
    for sep in (":", "|"):
        if sep in line:
            return line.split(sep, 1)[0]
    return line


def _compute_muscle_overlap_blocks(activities: list[dict], today: date) -> list[str]:
    """Derive recovery restrictions from exercise keywords found in activity descriptions.

    Complements _compute_recovery_blocks (tag-based) with description-keyword-based rules.
    RPE is extracted from the matching exercise line to tier block duration (3 tiers).

    Skips lines that contain `_EXCLUSION_MARKERS` ("nicht heute", "bewusst raus",
    "verschoben", "gesperrt", "skipped", …) — those describe exercises that were
    NOT performed (planning-notes / explicit skips).
    """
    blocks: list[str] = []
    for rule in MUSCLE_OVERLAP_RULES:
        keywords: list[str] = rule["keywords"]
        label: str = rule["label"]
        tiers: dict = rule["rpe_tiers"]
        default_tier: str = rule["default_tier"]

        for a in reversed(activities):
            desc = (a.get("description") or "").lower()
            matched_line: str | None = None
            for kw in keywords:
                for line in desc.splitlines():
                    if (
                        kw in _exercise_name_portion(line)
                        and not _line_is_exclusion(line)
                    ):
                        matched_line = line
                        break
                if matched_line is not None:
                    break

            if matched_line is None:
                continue

            d_str = (a.get("start_date_local") or "")[:10]
            try:
                act_date = date.fromisoformat(d_str)
            except (ValueError, TypeError):
                continue

            rpe_val = _extract_rpe_from_line(matched_line)
            if rpe_val is None:
                tier_key = default_tier
            elif rpe_val <= tiers["low"][0]:
                tier_key = "low"
            elif rpe_val <= tiers["mid"][0]:
                tier_key = "mid"
            else:
                tier_key = "high"

            _, hard_days, soft_days = tiers[tier_key]
            if hard_days == 0 and soft_days == 0:
                break  # no block needed, but stop searching (most recent hit found)

            days_ago = (today - act_date).days
            hard_end = act_date + timedelta(days=hard_days)
            soft_end = act_date + timedelta(days=hard_days + soft_days)
            rpe_str = f"RPE {rpe_val:.0f}" if rpe_val is not None else "RPE unknown (conservative)"

            def _add(hard_applicable: bool, soft_applicable: bool) -> None:
                if hard_applicable:
                    blocks.append(
                        f"⛔ {label}: hard block until {hard_end.isoformat()} "
                        f"({rpe_str}, {hard_days}d rule)"
                    )
                if soft_applicable and soft_days > 0:
                    blocks.append(
                        f"ℹ️  {label}: light load (RPE≤5) OK from {hard_end.isoformat()} "
                        f"until {soft_end.isoformat()}"
                    )

            if days_ago == 0:
                _add(hard_days > 0, soft_days > 0)
            elif days_ago < hard_days:
                _add(True, days_ago < hard_days + soft_days)
            elif soft_days > 0 and days_ago < hard_days + soft_days:
                blocks.append(
                    f"ℹ️  {label}: light load only (RPE≤5) until {soft_end.isoformat()} "
                    f"({days_ago}d ago — {rpe_str})"
                )

            break  # only most recent matching activity per rule
    return blocks


def _compute_previous_day_exercises(activities: list[dict], today: date) -> str:
    """Extract exercise names from yesterday's non-cardio activities.

    Provides cross-workout context for specialists so they know which muscle
    groups were loaded the day before. Scans description lines for exercise patterns.
    """
    import re

    yesterday = today - timedelta(days=1)
    cardio = {"Run", "Ride", "VirtualRide", "VirtualRun", "Swim"}
    # ÄÖÜ in the character class catches German exercise names (e.g. "Übung")
    # written by an athlete using a German config; ASCII A-Z covers all
    # English-language descriptions.
    exercise_pattern = re.compile(r"^([A-ZÄÖÜ][^:|\n]{2,40}):\s*\d")

    entries: list[str] = []
    for a in activities:
        d_str = (a.get("start_date_local") or "")[:10]
        try:
            act_date = date.fromisoformat(d_str)
        except (ValueError, TypeError):
            continue
        if act_date != yesterday:
            continue
        if a.get("type") in cardio:
            continue
        name = a.get("name", "Session")
        desc = a.get("description") or ""
        exercises: list[str] = []
        for line in desc.splitlines():
            m = exercise_pattern.match(line.strip())
            if m:
                exercises.append(m.group(1).strip())
        if exercises:
            entries.append(f"- {name}: {', '.join(exercises)}")
        elif desc.strip():
            entries.append(f"- {name}: (description present, exercises not parseable)")

    if not entries:
        return ""
    return "Yesterday's sessions — exercises:\n" + "\n".join(entries)


def _compute_planning_constraints(
    events: list[dict],
    activities: list[dict],
    today: date,
    deload_state: dict | None = None,
    warnings_out: list[str] | None = None,
) -> str:
    """Pre-compute key temporal planning facts from upcoming events.

    Detects upcoming breaks/vacations (NOTE events with break keywords) and
    computes absolute dates so agents never have to resolve relative references.

    ``warnings_out`` (optional) collects dataWarnings raised while parsing —
    e.g. an active recovery week whose planned end date cannot be parsed
    (the auto-expiry would silently never fire).
    """
    import re

    # Break-keyword detection in athlete NOTEs — bilingual to support both
    # German and English note text.  Word boundaries prevent compound-word
    # false positives (e.g. "Ruheposition", "Reisefoto").
    break_keywords = re.compile(
        r"\burlaub\b|\bpause\b|\btrainingspause\b"
        r"|\bkein training\b|\bruhe\b|\breise\b"
        r"|\bverreist\b|\bauszeit\b"
        r"|\bvacation\b|\bno training\b|\brest\b|\btravel\b"
        r"|\baway\b|\btime off\b|\bbreak\b",
        re.IGNORECASE,
    )
    # Exercise-instruction patterns that contain break keywords but describe
    # rep/set structure, not actual training breaks.  When the NOTE text
    # matches one of these, skip the break detection.
    exercise_pause_ctx = re.compile(
        r"\d+\s*s\s+pause"
        r"|\bpause\s+am\b"
        r"|\bpause\s+zwischen\b"
        r"|\bpause\s+nach\b"
        r"|\bruhe(?:position|phase)\b"
        r"|\brest\s+between\b"
        r"|\brest\s+period\b"
        r"|\brest\s+position\b",
        re.IGNORECASE,
    )

    constraints: list[str] = []

    # Recovery-week status — always as the first line (as hard as ⛔ rules).
    # The deload_state dict comes from athlete_status.md and may use either
    # German keys (aktiv/start/ende_geplant/begründung) or English keys
    # (active/start/planned_end/rationale). We accept both for compatibility.
    if deload_state:
        aktiv_raw = (
            deload_state.get("aktiv")
            or deload_state.get("active")
            or "nein"
        )
        aktiv = str(aktiv_raw).strip().lower()
        if aktiv in ("ja", "yes", "true"):
            start = deload_state.get("start") or "—"
            ende = (
                deload_state.get("ende_geplant")
                or deload_state.get("planned_end")
                or "—"
            )
            begruendung = (
                deload_state.get("begründung")
                or deload_state.get("rationale")
                or "—"
            )
            # Auto-expiry: deactivate if planned end is in the past.
            # parse_config_date accepts ISO and DD.MM.YYYY — an ISO-only
            # parse would never expire a German-formatted end date and the
            # recovery week would stay active forever.
            from app.utils.date_parse import parse_config_date

            ende_date = parse_config_date(ende)
            if ende_date is not None:
                if ende_date < today:
                    aktiv = "expired"
            elif warnings_out is not None:
                warnings_out.append(
                    f"Recovery week active but planned end date {ende!r} is "
                    f"not parseable (expected YYYY-MM-DD or DD.MM.YYYY) — "
                    f"auto-expiry disabled, fix the recovery-week block in "
                    f"athlete_status.md"
                )
            if aktiv in ("ja", "yes", "true"):
                constraints.append(
                    f"⛔ RECOVERY WEEK ACTIVE ({start} – {ende}): "
                    f"Running Z1/Z2 only, no tempo / intervals. "
                    f"Strength/Ninja: volume −20%, no max sets. "
                    f"Rationale: {begruendung}"
                )

    for e in events:
        if e.get("category") != "NOTE":
            continue
        text = (e.get("description") or "") + " " + (e.get("name") or "")
        if not break_keywords.search(text):
            continue
        if exercise_pause_ctx.search(text):
            continue

        d_str = (e.get("start_date_local") or "")[:10]
        try:
            break_start = date.fromisoformat(d_str)
        except (ValueError, TypeError):
            continue

        days_until = (break_start - today).days
        last_training = (break_start - timedelta(days=1)).isoformat()

        # Try to detect break end from description
        # Supports: "03.04.–10.04." (no year) and "03.04.2026–10.04.2026"
        first_after = None
        end_match = re.search(
            r"\d{2}\.\d{2}\.?(?:\d{4})?\s*[–\-]+\s*(\d{2})\.(\d{2})\.?(?:(\d{4}))?",
            text,
        )
        if end_match:
            try:
                day = int(end_match.group(1))
                month = int(end_match.group(2))
                year = int(end_match.group(3)) if end_match.group(3) else break_start.year
                break_end = date(year, month, day)
                # Year wrap: "28.12.–03.01." carries no year — the end date
                # defaults to break_start.year and lands BEFORE the start.
                # Roll it into the following year.
                if break_end < break_start:
                    break_end = date(year + 1, month, day)
                # Plausibility guard: still-inverted range or a break longer
                # than 90 days indicates a parse mismatch → ignore end date.
                if break_end < break_start or (break_end - break_start).days > 90:
                    logger.warning(
                        "break end %s implausible relative to start %s — ignoring end date",
                        break_end.isoformat(),
                        break_start.isoformat(),
                    )
                else:
                    first_after = (break_end + timedelta(days=1)).isoformat()
            except (ValueError, IndexError):
                pass

        if days_until < 0:
            continue  # break already started or passed

        rel = (
            "today"
            if days_until == 0
            else "tomorrow"
            if days_until == 1
            else f"in {days_until} days"
        )
        line = (
            f"Break/vacation starts {break_start.isoformat()} ({rel}) — "
            f"last training day: {last_training}"
        )
        if first_after:
            line += f" — first day after: {first_after}"
        constraints.append(line)

    recovery_blocks = _compute_recovery_blocks(activities, today)
    constraints.extend(recovery_blocks)

    muscle_overlap_blocks = _compute_muscle_overlap_blocks(activities, today)
    constraints.extend(muscle_overlap_blocks)

    prev_day = _compute_previous_day_exercises(activities, today)
    if prev_day:
        constraints.append(prev_day)

    # Complementary due-warning — proactive flag when a category is overdue
    due = _compute_complementary_due(activities, today)
    if due:
        constraints.append(due)

    # Exercise re-evaluation cadence — advisory flag at natural boundaries
    # (recovery week / phase change / staleness). Cheap: when absent the
    # daily flow is unchanged; when present /training runs exercise-reviewer
    # before the specialists to re-challenge selection vs. goals + level.
    reeval = _compute_reeval_trigger(today, deload_state)
    if reeval:
        constraints.append(reeval)

    # Video locks and film-tip candidates from exercise_log.md
    video_status = _compute_filmtipp_status(today)
    if video_status:
        constraints.append(video_status)

    # Ninja pillars history — always included so planner can rotate correctly
    ninja_history = _compute_last_ninja_pillar_history(activities)
    constraints.append(ninja_history)

    return "\n".join(constraints) if constraints else "No restrictions"


def _days_to_next_race(events: list[dict], today: date) -> int | None:
    race_cats = {"RACE_A", "RACE_B", "RACE_C"}
    upcoming: list[int] = []
    for e in events:
        if e.get("category") not in race_cats:
            continue
        d_str = (e.get("start_date_local") or "")[:10]
        try:
            days = (date.fromisoformat(d_str) - today).days
            if days >= 0:
                upcoming.append(days)
        except (ValueError, TypeError):
            pass
    return min(upcoming) if upcoming else None


def _safe_float(val: str) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _fmt(val: float | None, suffix: str) -> str:
    if val is None:
        return "-"
    return f"{val:.1f}{suffix}"


def _compute_sleep_trend(wellness_history: list[dict], today: date) -> str:
    """7-day rolling average of sleep hours and score.

    Returns a formatted string. Flags chronic sleep deprivation (avg < 6.5h)
    when at least 5 of the last 7 days have data.
    """
    cutoff = (today - timedelta(days=7)).isoformat()
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
            d = (today - timedelta(days=offset)).isoformat()
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


def _collect_warnings(
    hrv: float | None,
    rhr: float | None,
    sleep_score: float | None,
    ctl: float | None,
    atl: float | None,
    hr_zones_text: str,
    athlete_settings: dict,
    weather_warning: bool = False,
    sleep_trend: str = "",
    rhr_trend_delta: float | None = None,
) -> list[str]:
    warnings: list[str] = []
    if not athlete_settings:
        warnings.append("Athlete settings not loaded — HR zones and sport profile missing")
    if hrv is None:
        warnings.append("HRV not available — recovery assessment limited")
    if rhr is None:
        warnings.append("RHR not available — wearable possibly not synced yet")
    if sleep_score is None:
        warnings.append("Sleep score missing")
    if ctl is None or atl is None:
        warnings.append("CTL/ATL not available — fitness state unknown, TSB cannot be computed")
    if hr_zones_text == "HR-Zonen nicht verfügbar" or hr_zones_text == "HR zones not available":
        warnings.append("HR zones not available — dynamic zone target missing in the prompt")
    if weather_warning:
        warnings.append("Weather data not available — weather context missing from plan")
    if "⚠️" in sleep_trend:
        warnings.append(f"Chronic sleep deficit: {sleep_trend} — more conservative planning recommended")
    if rhr_trend_delta is not None and rhr_trend_delta > 3:
        warnings.append(
            f"⚠️ RHR rise: +{rhr_trend_delta:.0f} bpm in 7 days — possible overreaching signal"
        )
    return warnings


def _format_shoe_context(shoe_ctx: dict) -> str:
    """Render shoe context as a compact Markdown section for the planner prompt."""
    if not shoe_ctx:
        return ""

    lines: list[str] = ["## Shoe manager"]

    shoes = shoe_ctx.get("shoes") or []
    if shoes:
        lines.append("\n**Active shoes:**")
        for s in shoes:
            pct = s.get("pct_used", 0)
            since = s.get("days_since_used")
            since_str = f", {since}d unused" if since is not None else ""
            role_str = " [Race★]" if s.get("primary_race") else (" [Race]" if s.get("role") == "race" else "")
            lines.append(
                f"- {s['name']}{role_str}: {s.get('distance_km', 0):.0f} km"
                f" ({pct:.0f}%{since_str})"
            )

    rec = shoe_ctx.get("shoeRecommendation") or {}
    if rec.get("primary"):
        p = rec["primary"]
        lines.append(f"\n**Recommendation today:** {p['name']} — {p.get('reason', '')}")
        if rec.get("alternative"):
            a = rec["alternative"]
            lines.append(f"**Alternative:** {a['name']} — {a.get('reason', '')}")

    for w in shoe_ctx.get("shoeWarnings") or []:
        lines.append(f"\n{w['msg']}")

    fleet = shoe_ctx.get("shoeFleetWarning") or {}
    if fleet:
        parts: list[str] = []
        if fleet.get("missing_types"):
            parts.append("Fehlende Kategorien: " + ", ".join(fleet["missing_types"]))
        if fleet.get("soon_missing"):
            parts.append("Bald fehlend: " + ", ".join(fleet["soon_missing"]))
        sug = fleet.get("suggestions") or {}
        for cat, model in sug.items():
            parts.append(f"Empfehlung {cat}: {model}")
        if parts:
            lines.append("\n⚠ Sortiments-Warnung: " + " | ".join(parts))

    return "\n".join(lines)
