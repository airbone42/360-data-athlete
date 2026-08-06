"""Impact-load streak computation.

Running loads bone, tendon and fascia through ground impact; cycling,
swimming and indoor-trainer work do not. An athlete whose limiters are
impact-driven (achilles / plantar / ITB / stress-reaction history) can be
perfectly recovered by every autonomic marker and still be accumulating
structural load simply because the runs sit on consecutive days.

The derived signals already in the context do not surface that pattern:

- ``lastRestDay`` counts *any* logged activity as a training day, so a
  10-minute mobility routine masks a rest day and a pure bike day looks
  identical to a hard run day.
- ``daysSinceIntense`` looks **backwards** at intensity, not at the
  impact pattern the *planned* day would create.

So a plan can add a fourth consecutive running day — with a long run and
a quality session inside the streak — without a single field in the
context making that visible. This module computes the missing number
deterministically so the planner is *handed* it and the validator checks
against the same value. Both import from here on purpose: two
implementations would eventually disagree, and a disagreement about
whether a rule fired is worse than no rule.

Athlete-specific tolerance (how long a streak is acceptable, which
limiters make it stricter) belongs in the consumer's ``config/``, not
here — this module only reports the pattern.
"""

from __future__ import annotations

from datetime import date

from app.utils.activity_helpers import activity_date as _shared_activity_date
from app.utils.date_windows import cutoff_iso

# Activity types that transmit ground impact. Treadmill / virtual runs
# count: the surface is softer, the impact cycle is not removed.
IMPACT_TYPES: frozenset[str] = frozenset({"Run", "VirtualRun", "TrailRun"})

# A run at or above this duration counts as a long run for streak
# annotation. Deliberately generic: the point is "a session that carries
# unusual structural load sits inside the streak", not a phase-specific
# long-run definition (that lives in competition_plan.md).
LONG_RUN_MIN_MINUTES = 90

# training_load at or above this marks a quality/hard session when no
# explicit tag is present. Matches the threshold the zone/hard-reize
# helpers use for "this was not an easy day".
QUALITY_LOAD_THRESHOLD = 70

# How far back to walk. A streak longer than this is already reported as
# "at least N" — no planning decision needs more resolution.
MAX_LOOKBACK_DAYS = 14


def _activity_date(activity: dict) -> str:
    return _shared_activity_date(activity)


def _is_impact(activity: dict, impact_types: frozenset[str]) -> bool:
    return (activity.get("type") or "") in impact_types


def _duration_minutes(activity: dict) -> float:
    """Minutes, tolerating both activity shapes.

    Raw intervals.icu activities carry ``moving_time`` in seconds; the
    formatted summaries built for agent consumption carry ``duration_min``.
    Both reach this module (context_builder passes raw dicts, the validator
    passes whatever its loader holds), so read either — silently defaulting
    to 0 would make a long run invisible inside the streak.
    """
    for key, divisor in (("duration_min", 1), ("moving_time", 60)):
        value = activity.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value) / divisor
        except (TypeError, ValueError):
            continue
    return 0.0


def _training_load(activity: dict) -> float | None:
    """Load, tolerating both activity shapes (see :func:`_duration_minutes`)."""
    for key in ("training_load", "icu_training_load"):
        value = activity.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _is_quality(activity: dict) -> bool:
    """Quality by explicit tag first, training load as the fallback."""
    tags = [str(t).lower() for t in (activity.get("tags") or [])]
    if "intervals" in tags:
        return True
    workout_type = (activity.get("workout_type") or "").upper()
    if workout_type in {"INTERVALS", "RACE", "THRESHOLD"}:
        return True
    load = _training_load(activity)
    return load is not None and load >= QUALITY_LOAD_THRESHOLD


def compute_run_day_streak(
    activities: list[dict],
    today: date,
    *,
    impact_types: frozenset[str] = IMPACT_TYPES,
    long_run_min_minutes: int = LONG_RUN_MIN_MINUTES,
) -> dict:
    """Consecutive impact-load (running) days ending at or just before ``today``.

    The streak is the *current* run of consecutive impact days. When today
    already carries a run it is included (``includes_today``); when it does
    not, the streak is the one ending yesterday — which is exactly what a
    planner needs in order to know what planning a run today would create.

    Returns a dict with:
        streak_days         consecutive impact days in the current streak
        includes_today      whether today already carries an impact activity
        prospective_days    streak length if a run were added today
        streak_dates        ISO dates in the streak, oldest first
        run_days_5d         impact days in the trailing 5 days (incl. today)
        run_days_7d         impact days in the trailing 7 days (incl. today)
        prospective_5d      run_days_5d if a run were added today
        contains_long_run   a run >= long_run_min_minutes sits in the streak
        contains_quality    a quality/hard run sits in the streak
        message             one-line human-readable summary
    """
    impact_by_date: dict[str, list[dict]] = {}
    for activity in activities or []:
        if not _is_impact(activity, impact_types):
            continue
        day = _activity_date(activity)
        if day:
            impact_by_date.setdefault(day, []).append(activity)

    includes_today = today.isoformat() in impact_by_date

    # Walk back from today (or yesterday, when today has no run yet) for as
    # long as each consecutive calendar day carries an impact activity.
    streak_dates: list[str] = []
    offset = 0 if includes_today else 1
    while offset < MAX_LOOKBACK_DAYS:
        day = cutoff_iso(today, offset)
        if day not in impact_by_date:
            break
        streak_dates.append(day)
        offset += 1
    streak_dates.reverse()

    streak_activities = [a for d in streak_dates for a in impact_by_date[d]]

    contains_long_run = any(
        _duration_minutes(a) >= long_run_min_minutes for a in streak_activities
    )
    contains_quality = any(_is_quality(a) for a in streak_activities)

    def _days_in_window(window: int) -> int:
        return sum(
            1
            for i in range(window)
            if cutoff_iso(today, i) in impact_by_date
        )

    # Density matters independently of strict consecutiveness: runs on
    # Tue/Thu/Fri/Sat carry four impact days in five even though the longest
    # consecutive streak is three. A single off-day inside the window does
    # not reset structural load the way the streak counter suggests.
    run_days_5d = _days_in_window(5)
    run_days_7d = _days_in_window(7)

    streak_days = len(streak_dates)
    prospective_days = streak_days if includes_today else streak_days + 1

    if streak_days == 0:
        message = (
            f"No current run-day streak "
            f"({run_days_5d} run day(s) in the last 5d, {run_days_7d} in 7d)."
        )
    else:
        span = (
            streak_dates[0]
            if streak_days == 1
            else f"{streak_dates[0]}–{streak_dates[-1]}"
        )
        annotations = []
        if contains_long_run:
            annotations.append("incl. long run")
        if contains_quality:
            annotations.append("incl. quality")
        suffix = f" ({', '.join(annotations)})" if annotations else ""
        tail = (
            ""
            if includes_today
            else f" — a run today would make it {prospective_days}"
        )
        message = (
            f"{streak_days} consecutive run day(s) {span}{suffix}; "
            f"{run_days_5d} run day(s) in the last 5d, {run_days_7d} in 7d{tail}."
        )

    prospective_5d = run_days_5d if includes_today else run_days_5d + 1

    return {
        "streak_days": streak_days,
        "includes_today": includes_today,
        "prospective_days": prospective_days,
        "streak_dates": streak_dates,
        "run_days_5d": run_days_5d,
        "prospective_5d": prospective_5d,
        "run_days_7d": run_days_7d,
        "contains_long_run": contains_long_run,
        "contains_quality": contains_quality,
        "message": message,
    }
