"""Port of the n8n 'Build Athlete Context' JS code node to Python."""

from __future__ import annotations

import logging
import math
import re
from datetime import date, datetime, timedelta
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
from app.utils.activity_helpers import activity_date
from app.utils.alerts import notify_error
from app.utils.date_windows import cutoff_iso
from app.utils.hr_zones import extract_run_hr_bounds, format_hr_zones
from app.utils.impact_load import compute_run_day_streak
from app.analytics.zones import (  # noqa: F401 — re-exported for callers/tests
    CARDIO_TYPES,
    HARD_STIMULUS_MIN_Z4_Z5_SECS,
    _compute_weekly_hard_reize_balance,
    _compute_zone_distribution,
    _correct_cardiac_drift,
    _fmt,
    _z4_z5_secs,
    is_hard_stimulus,
)
from app.analytics.load_cycles import (  # noqa: F401 — re-exported for callers/tests
    DELOAD_PCT,
    DELOAD_WEEK_TSS_RATIO,
    MIN_CTL,
    MIN_WEEK_TSS,
    TOLERANCE_PCT,
    _analyze_load_cycle,
    _compute_ctl_trend,
    _compute_meso_load_trend,
    _compute_weekly_loads,
    _compute_weekly_stats,
    _is_deload_week,
    _safe_float,
)
from app import sports
from app.analytics.hrv import (  # noqa: F401 — re-exported for callers/tests
    HRV_BAND_HOLD_DAYS,
    HRV_BAND_K,
    HRV_BAND_MIN_REF,
    HRV_BAND_MIN_ROLL,
    HRV_BAND_REF_DAYS,
    HRV_BAND_ROLL_DAYS,
    HRV_CVTREND_DEADBAND_PCT,
    HRV_CVTREND_MIN_PTS,
    _compute_combined_overload_signal,
    _compute_hrv_baseline,
    _compute_hrv_cv,
    _compute_hrv_cv_trend,
    _compute_hrv_readiness_band,
    _compute_rhr_baseline,
    _compute_rhr_trend,
    _compute_sleep_trend,
)
from app.utils.prompt_loader import load_prompt


# ── Coach markers persisted on planned event descriptions ────────────
# Written by push_workouts._format_shoe_footer (intervals.icu backend); read
# back here so the context-time shoe recommendation reproduces the push-time
# pick from identical inputs. The gear marker is also parsed by
# scripts/set_activity_gear.py; keep the regex compatible.
_COACH_GEAR_MARKER_RE = re.compile(r"\[coach-gear:\s*([A-Za-z0-9_-]+)\]")
_COACH_PLAN_MARKER_RE = re.compile(r"\[coach-plan:([^\]]+)\]")
_COACH_PLAN_ALLOWED_KEYS = {"surface", "workout_type", "intensity"}


def _parse_coach_plan_marker(description: str | None) -> dict:
    """Extract planner metadata from a ``[coach-plan:key=value,…]`` marker.

    Returns an empty dict when no marker is present. Only whitelisted keys are
    returned so a stray token in an athlete-edited description cannot inject an
    unexpected field into the workout dict fed into the shoe advisor.
    """
    if not description:
        return {}
    m = _COACH_PLAN_MARKER_RE.search(description)
    if not m:
        return {}
    result: dict = {}
    for token in m.group(1).split(","):
        if "=" not in token:
            continue
        k, _, v = token.partition("=")
        k = k.strip()
        v = v.strip()
        if not v or k not in _COACH_PLAN_ALLOWED_KEYS:
            continue
        result[k] = v
    return result


def _parse_coach_gear_marker(description: str | None) -> str | None:
    """Extract the pinned gear id from a ``[coach-gear:<id>]`` marker."""
    if not description:
        return None
    m = _COACH_GEAR_MARKER_RE.search(description)
    return m.group(1) if m else None


def _build_shoe_planned_workouts(events: list[dict], today_iso: str) -> list[dict]:
    """Build the planned-workout list the shoe advisor scores against.

    intervals.icu events returned via ``get_events`` do NOT carry the coach's
    ``surface`` / ``workout_type`` / ``intensity`` / ``coaching_notes`` fields
    even though ``push_workouts`` sent them — they are dropped server-side.
    The advisor's terrain/pace filters therefore go blind (terrain defaults to
    "asphalt", pace_bucket to None → no filter) and pick a different shoe than
    the push-time recommendation which received the full planner directive
    directly.

    This builder recovers those fields from the ``[coach-plan:…]`` marker
    written into the event description at push time (see
    ``push_workouts._format_shoe_footer``). When the marker is absent (legacy
    events or non-coach-pushed runs), the fields are left empty rather than
    guessed from prose — a "Wald" mention in a run title should NOT flip the
    terrain filter to trail if the coach's surface tag actually meant
    "forest-path" (asphalt-equivalent for shoe choice). The gear marker,
    when present, is attached as ``_coach_gear_id`` for the SSOT override in
    ``_apply_coach_gear_ssot``.
    """
    planned: list[dict] = []
    for e in events:
        if e.get("type") != "Run":
            continue
        if (e.get("start_date_local") or "")[:10] != today_iso:
            continue
        desc = e.get("description") or ""
        marker = _parse_coach_plan_marker(desc)
        gear = _parse_coach_gear_marker(desc)
        entry: dict = {
            "type": "Run",
            "tags": list(e.get("tags") or []),
            # Only surfaced when the marker carried them — an empty string
            # reads as "unknown" downstream (no filter) rather than as a
            # concrete value. Deliberately not falling back to the raw
            # description text: prose keyword scans against the intervals.icu
            # event body can flip filters based on incidental wording.
            "surface": marker.get("surface", ""),
            "workout_type": marker.get("workout_type", ""),
            "intensity": marker.get("intensity", ""),
            "coaching_notes": "",
        }
        if gear:
            entry["_coach_gear_id"] = gear
        planned.append(entry)
    return planned


def _apply_coach_gear_ssot(shoe_ctx: dict, planned_workouts: list[dict]) -> dict:
    """Promote the push-time gear pick to primary when it's still an active shoe.

    Backstop for legacy events pushed before the ``[coach-plan:…]`` marker
    existed: the ``[coach-gear:<id>]`` marker alone is enough to make the
    context recommendation converge on the push pick. When both markers are
    present, the advisor's inputs are already correct and its primary equals
    the pinned shoe — this call is then a no-op.

    Silent when: no marker, marker points to a retired/unknown shoe, or the
    advisor already picked the pinned shoe. When it does override, the
    previously-picked primary is demoted to ``alternative`` so the read side
    still sees a runner-up.
    """
    if not planned_workouts:
        return shoe_ctx
    pinned = planned_workouts[0].get("_coach_gear_id")
    if not pinned:
        return shoe_ctx
    shoes = shoe_ctx.get("shoes") or []
    pinned_shoe = next((s for s in shoes if s.get("gear_key") == pinned), None)
    if not pinned_shoe:
        # Marker references a shoe not in the active enriched list (retired,
        # migrated, or outside a travel subset). Leave the advisor's pick.
        logger.info("coach-gear marker %s not in active shoes — SSOT skipped", pinned)
        return shoe_ctx
    rec = dict(shoe_ctx.get("shoeRecommendation") or {})
    current_primary = rec.get("primary") or {}
    if current_primary.get("gear_id") == pinned:
        return shoe_ctx  # already converged
    since = pinned_shoe.get("days_since_used")
    reasons: list[str] = []
    if since is not None:
        reasons.append(f"{since} days unused")
    reasons.append("push-time pick (coach-gear marker)")
    new_primary = {
        "gear_id": pinned_shoe.get("gear_key"),
        "name": pinned_shoe.get("name"),
        "distance_km": pinned_shoe.get("distance_km"),
        "pct_used": pinned_shoe.get("pct_used"),
        "reason": ", ".join(reasons),
    }
    prev_alt = rec.get("alternative") or {}
    if current_primary.get("gear_id") and current_primary.get("gear_id") != pinned:
        rec["alternative"] = current_primary
    elif prev_alt.get("gear_id") == pinned:
        # The pinned shoe was already the alternative — clear it so we don't
        # list the same shoe twice.
        rec.pop("alternative", None)
    rec["primary"] = new_primary
    return {**shoe_ctx, "shoeRecommendation": rec}


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
    weekly_loads = _compute_weekly_loads(activities, today)
    cycle_hint = _analyze_load_cycle(weekly_stats, weekly_loads)
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
        [a for a in activities if activity_date(a) >= cutoff_iso(today, 7)]
    )
    weekly_hard_reize_balance = _compute_weekly_hard_reize_balance(activities, today)

    last_intense = _find_last_intense_session(activities)
    last_rest_day = _find_last_rest_day(activities, today)

    # Impact-load streak — consecutive running days. Neither lastRestDay
    # (counts any activity, so a mobility block masks a rest day and a bike
    # day looks like a run day) nor daysSinceIntense (backward-looking, and
    # about intensity rather than impact) makes this pattern visible, so a
    # plan can add a fourth consecutive running day unnoticed. Computed in
    # code, not inferred by an agent: validate_plan.py R022 reads the same
    # helper, so the planner and the validator cannot disagree about it.
    run_day_streak = compute_run_day_streak(activities, today)

    # Inter-session recovery window — recovery is a function of elapsed
    # clock-time, not calendar-day gap: a late-evening session before a
    # morning session compresses the overnight window to well under a full
    # day, which a date-only view cannot see. Computed in code so the
    # planner reads the real window instead of estimating from dates.
    last_session_end = _compute_last_session_end(activities)

    days_since_intense = _days_since(last_intense, today)
    hrv_cv = _compute_hrv_cv(wellness_history, today)

    hrv_baseline_float_for_signal = float(hrv_baseline) if hrv_baseline != "-" else None
    rhr_baseline_float_for_signal = float(rhr_baseline) if rhr_baseline != "-" else None
    combined_overload_signal = _compute_combined_overload_signal(
        wellness_history,
        hrv_baseline_float_for_signal,
        rhr_baseline_float_for_signal,
        today,
        _parse_rhr_overload_bpm(_read_optional_config("athlete_status.md")),
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
    # `shoes` is the shoe list assembled by fetch_context from intervals.icu
    # gear; profiles join on `icu_gear_id`.
    shoe_list: list[dict] = state.get("shoes") or []
    shoe_profiles = load_shoe_profiles()
    shoe_ctx: dict = {}
    if shoe_list:
        # Rotation intelligence uses a longer look-back than the general 4-week
        # `activities` window (`SHOE_ADVISOR_LOOKBACK_DAYS` in shoe_advisor);
        # otherwise a shoe idle beyond that window has no last-used date and
        # the recommendation reason silently degrades from "N days unused" to
        # a generic "type/terrain" label — a rotation-blind fallback. Callers
        # that pre-fetched the wider window pass it via `shoe_activities`;
        # legacy callers with only the short-window list fall back to
        # `activities` so the code path stays working (rotation reason then
        # degrades, but the recommendation itself does not).
        shoe_activities: list[dict] = state.get("shoe_activities") or activities
        # Reconstruct the planner metadata the intervals.icu event dict does
        # not preserve — surface / workout_type / intensity are read from the
        # ``[coach-plan:…]`` marker the push writes into the description. Both
        # `workouts` (past+today) and `events` (today+future) can carry today's
        # planned Run; merge dedup-by-id so a re-fetch sees the same entry
        # regardless of which endpoint returned it.
        _seen_event_ids: set = set()
        _run_events: list[dict] = []
        for source in (workouts, events):
            for ev in source:
                ev_id = ev.get("id")
                if ev_id is not None and ev_id in _seen_event_ids:
                    continue
                if ev_id is not None:
                    _seen_event_ids.add(ev_id)
                _run_events.append(ev)
        shoe_planned = _build_shoe_planned_workouts(_run_events, today.isoformat())
        try:
            shoe_ctx = build_shoe_context(
                shoes=shoe_list,
                profiles=shoe_profiles,
                activities=shoe_activities,
                planned_workouts=shoe_planned,
                weather_info=weather_info,
                race_in_days=race_in_days,
                today_str=today.isoformat(),
                backend=settings.shoe_tracking_backend,
            )
            # SSOT backstop: when the coach-gear marker pins a specific active
            # shoe (legacy events pushed before the coach-plan marker existed
            # only carry this one), promote it to primary so the context
            # recommendation matches what was written to the event.
            shoe_ctx = _apply_coach_gear_ssot(shoe_ctx, shoe_planned)
        except Exception as e:
            logger.warning("shoe_advisor failed: %s", e)

    today_workouts = _summarize_today_workouts(events, today)

    # Context-lean gating: the full shoe fleet is only planning-relevant when
    # today actually carries a Run/Ride. On other days the fleet list and the
    # systemPrompt shoe block are dropped (recommendation stays {} anyway —
    # the push-time advisor in push_workouts/shoe_recommend fetches gear
    # itself, independent of this context field).
    run_or_ride_today = any(
        (w.get("type") or "") in (sports.RUN_TYPES | sports.BIKE_TYPES)
        for w in today_workouts
    )
    if not run_or_ride_today:
        shoe_ctx = {
            **shoe_ctx,
            "shoes": [],
            "shoeRecommendation": shoe_ctx.get("shoeRecommendation", {}),
        }

    shoe_context_text = _format_shoe_context(shoe_ctx)
    system_prompt = system_prompt.replace("{shoeContext}", shoe_context_text)

    # coaching_notes (paired event descriptions, up to 500 chars each) are
    # briefing-relevant only for the recent window; older activities keep
    # their metadata (type/tags/load/duration feed streak & balance reads)
    # while per-exercise detail comes from fetch_type_history on demand.
    _notes_cutoff = cutoff_iso(today, 7)

    result = {
        "hrvContext": hrv_context,
        "hrv": hrv if hrv is not None else "-",
        "rhr": rhr if rhr is not None else "-",
        "sleep": sleep_score if sleep_score is not None else "-",
        "sleepHours": sleep_hours,
        "activities": [
            _summarize_activity(
                a,
                include_notes=activity_date(a) >= _notes_cutoff,
            )
            for a in activities_with_workout
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
        "runDayStreak": run_day_streak,
        "lastSessionEnd": last_session_end,
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
        # Shoe context (empty dicts/lists when no shoe backend configured)
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


def _summarize_activity(a: dict, include_notes: bool = True) -> dict:
    """Reduce a full activity object to the fields the planner actually needs.

    `name` and `event_description` are athlete-/third-party-roundtrip-controlled
    and end up in specialist briefings → sanitize at this write boundary
    (mirrors history_fetcher._format_activity).

    `include_notes=False` drops the `coaching_notes` payload (context-lean
    mode for activities outside the recent briefing window — the metadata
    stays, exercise detail comes from fetch_type_history on demand).
    """
    from app.utils.sanitize import escape_for_prompt

    raw_name = a.get("name") or ""
    result: dict = {
        "date": activity_date(a),
        "type": a.get("type"),
        "name": escape_for_prompt(raw_name, max_len=200) if raw_name else raw_name,
        "tags": a.get("tags"),
        "workout_type": a.get("workout_type"),
        "training_load": a.get("icu_training_load"),
        "duration_min": round(a.get("moving_time", 0) / 60) or None,
    }
    if include_notes and a.get("event_description"):
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


# ── HRV Readiness (7d-rolling ln-rMSSD vs 60d band) ────────────────


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
        cutoff_iso(today, o)
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
        activity_date(a) for a in activities
    }
    for i in range(1, 8):
        d = cutoff_iso(today, i)
        if d not in activity_dates:
            return "yesterday" if i == 1 else f"{i} days ago"
    return "no rest day in the last 7 days"


def _compute_last_session_end(
    activities: list[dict], now: datetime | None = None
) -> dict | None:
    """End clock-time of the most recent finished session + hours since.

    Mechanizes the "Inter-session recovery window" rule (framework
    CLAUDE.md): two sessions on consecutive calendar days can be anywhere
    from ~10 h to ~36 h apart depending on when each actually happened —
    the planner must read the elapsed clock-time, never estimate the
    window from dates alone.

    Timestamps are athlete-local (`start_date_local`); `now` defaults to
    server time, which the deployment keeps in the athlete's timezone.
    Returns None when no parseable activity exists.
    """
    now = now or datetime.now()
    best_end: datetime | None = None
    best: dict | None = None
    for a in activities:
        raw = a.get("start_date_local")
        if not raw:
            continue
        try:
            start = datetime.fromisoformat(str(raw).split("+")[0].rstrip("Z"))
        except ValueError:
            continue
        end = start + timedelta(seconds=a.get("moving_time") or 0)
        if end > now:
            continue  # scheduled / future artefacts
        if best_end is None or end > best_end:
            best_end, best = end, a
    if best_end is None or best is None:
        return None
    hours = (now - best_end).total_seconds() / 3600
    return {
        "activityId": best.get("id"),
        "activityName": best.get("name"),
        "endLocal": best_end.isoformat(timespec="minutes"),
        "hoursSinceEnd": round(hours, 1),
    }


def _days_since(activity: dict | None, today: date) -> int:
    if not activity:
        return 99
    start = activity_date(activity)
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
    third-party description sync → sanitize at this write boundary.
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
        d_str = activity_date(a)
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


def _compute_prescription_compliance(today: date) -> str | None:
    """Flag standing prescriptions that were not actually executed.

    Complements `_compute_complementary_due`, which resolves only to the tag
    level. An exercise prescribed inside another block — a lift that hangs off
    the core session, a physio position inside a shoulder block — is invisible
    there: the block runs, the tag is satisfied, and the omission is silent.
    Only exercises that declare a `**Soll-Frequenz:**` in
    `exercise_progressions.md` are tracked, so this stays opt-in per exercise
    rather than flagging every entry in the file.
    """
    from app.analytics.prescription_compliance import (
        compute_prescription_compliance,
        format_findings,
    )
    from app.utils.config_loader import load_config

    findings = compute_prescription_compliance(
        load_config("exercise_progressions"), today
    )
    return format_findings(findings)


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
            d_str = activity_date(a)
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


def _parse_rhr_overload_bpm(status_content: str | None) -> float:
    """Read the athlete's RHR overload step from ``athlete_status.md``.

    Key: ``rhr_overload_bpm`` (default 5). This is the bpm rise above the RHR
    baseline that, **together with** an HRV value below baseline, counts as one
    overload day in ``_compute_combined_overload_signal``.

    It is athlete configuration rather than framework policy for the same reason
    ``impact_streak_max`` is: the right value depends on the athlete's own RHR
    variability, and the framework default is a convention, not a measured
    threshold — the citation that once justified 5 bpm was retracted on
    2026-09-01 after a source audit.
    """
    if not status_content:
        return 5.0
    import re as _re
    m = _re.search(r"rhr_overload_bpm[:*\s=]*([0-9]+(?:[.,][0-9]+)?)", status_content, _re.IGNORECASE)
    if not m:
        return 5.0
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return 5.0


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
            d_str = activity_date(a)
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

            d_str = activity_date(a)
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
    cardio = sports.CARDIO_TYPES
    # ÄÖÜ in the character class catches German exercise names (e.g. "Übung")
    # written by an athlete using a German config; ASCII A-Z covers all
    # English-language descriptions.
    exercise_pattern = re.compile(r"^([A-ZÄÖÜ][^:|\n]{2,40}):\s*\d")

    entries: list[str] = []
    for a in activities:
        d_str = activity_date(a)
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
        last_training = cutoff_iso(break_start, 1)

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

    # Prescription compliance — the due-warning above works on activity TAGS
    # and therefore cannot see a prescribed exercise that lives inside another
    # block: the session runs, the tag is satisfied, and a dropped element
    # leaves no trace. This check compares declared cadences against the
    # exercises actually recorded in the muscle logs. Fail-soft by design — a
    # parsing problem must never cost a plan.
    try:
        prescription = _compute_prescription_compliance(today)
        if prescription:
            constraints.append(prescription)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Prescription-compliance check skipped: %s", exc)

    # Impact-load streak — surfaced as a constraint line so the planner reads
    # the pattern before it plans, not after the athlete catches it. Only
    # emitted once a streak actually exists; a quiet day stays quiet.
    streak = compute_run_day_streak(activities, today)
    if streak["streak_days"] >= 2:
        icon = "🔴" if streak["prospective_days"] >= 4 else "🟡"
        constraints.append(
            f"{icon} Impact-load streak: {streak['message']} "
            "Running is the only impact modality — a cross-training day "
            "(bike/swim) breaks the streak without costing aerobic load."
        )

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
