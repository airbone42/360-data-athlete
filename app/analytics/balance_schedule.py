"""Scheduling logic for the balance/proprioception rotation.

The framework's default is one balance unit per training day — the rule is
enforced in `push_workouts._auto_push_balance`, which fires after every main
push. That default is deliberately generous: for an athlete with no ankle
history a short daily drill costs little and the counter never nags.

It is not, however, the dose the prevention evidence describes. Programmes
that actually reduced lateral ankle sprains ran **2–3 sessions per week** of
progressive, perturbation-based work — and progression there runs over task
complexity and unpredictability, not over more repetitions of the same short
drill. An athlete following the evidence therefore wants a *lower* frequency
with a longer, harder session, which the daily auto-push cannot express.

This module supplies the frequency arithmetic, kept pure so it can be tested
without an API client. The default stays 7 (daily): an athlete who configures
nothing sees no behaviour change.

Two design notes worth keeping:

**The window rolls, it does not reset on Monday.** A calendar week lets a
Friday/Saturday/Sunday cluster be followed immediately by Monday/Tuesday/
Wednesday — six sessions in six days, all "within budget". The same reasoning
already governs `weeklyHardReizeBalance`.

**Rotation advances by session, not by date.** The pool holds four distinct
sessions and the date-based pick (`ordinal % 4`) assumes daily execution. At
three sessions a week with a two-day gap the date arithmetic lands on the same
key repeatedly — Monday and Friday are four ordinals apart, so both draw A.
Stepping from the previous session's key instead keeps all four in rotation
whatever the frequency.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

ROTATION_KEYS = ["A", "B", "C", "D"]

# Framework default: one unit per training day, i.e. the behaviour that
# existed before this module. An athlete who sets nothing keeps it.
DEFAULT_SESSIONS_PER_WEEK = 7

_FREQ_RE = re.compile(
    r"balance_sessions_per_week[:\*\s=]*(\d+)",
    re.IGNORECASE,
)


def parse_balance_frequency(status_content: str | None) -> int:
    """Read `balance_sessions_per_week` from athlete_status.md.

    Same shape as the other athlete-specific switches (`impact_streak_max`,
    `rhr_overload_bpm`): a markdown bullet, read with a tolerant regex, with
    the framework default standing when the key is absent. Values are clamped
    to 1..7 — zero would silently disable a standing prescription, which is a
    decision that belongs to the athlete, not to a config typo.
    """
    if not status_content:
        return DEFAULT_SESSIONS_PER_WEEK
    m = _FREQ_RE.search(status_content)
    if not m:
        return DEFAULT_SESSIONS_PER_WEEK
    try:
        value = int(m.group(1))
    except ValueError:
        return DEFAULT_SESSIONS_PER_WEEK
    return max(1, min(7, value))


def min_gap_days(sessions_per_week: int) -> int:
    """Minimum whole days between two balance sessions.

    Spreads the sessions instead of letting them cluster: three a week means
    at least every other day, not three days in a row followed by four off.
    At seven a week the gap is 1, i.e. no constraint beyond one per day.
    """
    return max(1, 7 // max(1, sessions_per_week))


def balance_due(
    target_date: date,
    balance_event_dates: list[date],
    sessions_per_week: int,
) -> tuple[bool, str]:
    """Decide whether a balance unit is due on ``target_date``.

    Returns ``(due, reason)``. The reason is logged rather than inferred at
    the call site, so a skipped push always says which of the two limits it
    hit.

    Counting uses *planned events*, not completed activities. That is correct
    for a scheduler — its job is not to double-book the calendar. Execution
    gaps are a different question and are already covered by the `balance`
    tag due-warnings in the planning context.
    """
    if sessions_per_week >= 7:
        return True, "daily cadence (framework default)"

    window_start = target_date - timedelta(days=6)
    in_window = [d for d in balance_event_dates if window_start <= d <= target_date]
    if len(in_window) >= sessions_per_week:
        return False, (
            f"{len(in_window)}/{sessions_per_week} balance units already in "
            f"{window_start.isoformat()}…{target_date.isoformat()}"
        )

    gap = min_gap_days(sessions_per_week)
    recent = [d for d in in_window if 0 < (target_date - d).days < gap]
    if recent:
        last = max(recent)
        return False, (
            f"last balance unit {(target_date - last).days} day(s) ago, "
            f"minimum gap is {gap}"
        )

    return True, (
        f"{len(in_window)}/{sessions_per_week} in the rolling 7d window"
    )


def next_rotation(previous_key: str | None, target_date: date) -> str:
    """Pick the next rotation key.

    Steps one position on from the previous session's key. Falls back to the
    date-based pick when the previous key is unknown — which is also exactly
    the pre-existing behaviour, so nothing changes for a daily cadence where
    the two agree anyway.
    """
    if previous_key in ROTATION_KEYS:
        idx = ROTATION_KEYS.index(previous_key)  # type: ignore[arg-type]
        return ROTATION_KEYS[(idx + 1) % len(ROTATION_KEYS)]
    return ROTATION_KEYS[target_date.toordinal() % len(ROTATION_KEYS)]
