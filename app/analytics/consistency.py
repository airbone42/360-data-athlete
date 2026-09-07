"""Training consistency — the streak of weeks that actually held together.

Volume and quality are visible everywhere in this system: CTL, the zone
distribution, the hard-stimulus balance, the type history. Consistency is
not, and for an athlete rebuilding a base it is frequently the binding
constraint — three interrupted weeks cost more than any single session
gains, and nothing in the context surfaced that.

The field answers one question: **how many complete weeks in a row met the
athlete's own floor for run days and kilometres?** Plus the same figure as a
ratio over the look-back window, so a single good streak does not read as a
trend.

Three deliberate choices:

**ISO weeks, not a rolling window.** The neighbouring hard-stimulus field
rolls, and rightly so — it answers "what is still open right now". This one
answers "how many weeks held", which is a calendar statement the athlete has
to be able to check against their own memory. A rolling definition would
produce a number nobody can verify by looking at a calendar.

**The current week is excluded from the streak.** It is incomplete by
definition; counting it would make the streak flicker between Monday and
Sunday. It is reported separately as a progress line.

**A week with no recorded activity at all is marked, not silently counted as
a miss.** The distinction matters: no data and no training look identical to
a naive counter, and only one of them is a training finding.

Both thresholds are athlete configuration with **no framework default**.
Without them the field describes the weeks and says explicitly that no streak
claim is possible — inventing a floor would be asserting a training standard
the athlete never set.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from app import sports
from app.utils.activity_helpers import activity_date

DEFAULT_LOOKBACK_WEEKS = 12

_MIN_RUN_DAYS_RE = re.compile(r"consistency_min_run_days[:\*\s=]*(\d+)", re.IGNORECASE)
_MIN_WEEK_KM_RE = re.compile(
    r"consistency_min_week_km[:\*\s=]*([0-9]+(?:[.,][0-9]+)?)", re.IGNORECASE
)
_NEUTRAL_WEEKS_RE = re.compile(
    r"consistency_neutral_weeks[:\*\s=]*(.+)", re.IGNORECASE
)
_ISO_WEEK_RE = re.compile(r"(\d{4})-W(\d{1,2})")


def parse_consistency_thresholds(
    status_content: str | None,
) -> tuple[int | None, float | None, set[str]]:
    """Read the two floors and the neutral-week list from athlete_status.md.

    Returns ``(min_run_days, min_week_km, neutral_weeks)``. Either threshold
    may be None — the caller then describes the weeks without claiming a
    streak.
    """
    if not status_content:
        return None, None, set()

    days_m = _MIN_RUN_DAYS_RE.search(status_content)
    km_m = _MIN_WEEK_KM_RE.search(status_content)
    neutral_m = _NEUTRAL_WEEKS_RE.search(status_content)

    min_days = int(days_m.group(1)) if days_m else None
    min_km: float | None = None
    if km_m:
        try:
            min_km = float(km_m.group(1).replace(",", "."))
        except ValueError:
            min_km = None

    neutral: set[str] = set()
    if neutral_m:
        for year, week in _ISO_WEEK_RE.findall(neutral_m.group(1)):
            neutral.add(f"{year}-W{int(week):02d}")

    return min_days, min_km, neutral


def _iso_key(d: date) -> str:
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def weekly_run_summary(
    activities: list[dict],
    today: date,
    weeks: int = DEFAULT_LOOKBACK_WEEKS,
) -> list[dict]:
    """Per ISO week: run days, run km, whether the week is complete and covered.

    ``covered`` is False for a week the activity window does not fully span —
    the window edge cuts one week in half, and a half week counted as a miss
    would be an artefact of the fetch depth rather than of training.
    """
    if weeks < 1:
        return []

    # Monday of the current week, then step back.
    this_monday = today - timedelta(days=today.weekday())
    starts = [this_monday - timedelta(weeks=i) for i in range(weeks)]
    starts.reverse()

    dated: list[tuple[date, dict]] = []
    for a in activities:
        try:
            dated.append((date.fromisoformat(activity_date(a)), a))
        except (ValueError, TypeError):
            continue
    earliest = min((d for d, _ in dated), default=None)

    out: list[dict] = []
    for start in starts:
        end = start + timedelta(days=6)
        in_week = [(d, a) for d, a in dated if start <= d <= end]

        run_days = {
            d for d, a in in_week if a.get("type") in sports.RUN_TYPES
        }
        run_m = sum(
            (a.get("distance") or 0)
            for _, a in in_week
            if a.get("type") in sports.RUN_TYPES
        )
        out.append({
            "iso_week": _iso_key(start),
            "start": start.isoformat(),
            "run_days": len(run_days),
            "run_km": round(run_m / 1000, 1),
            "total_activities": len(in_week),
            "complete": end < today,
            # The window has to reach back past the Monday for the week to be
            # judgeable at all.
            "covered": earliest is not None and earliest <= start,
        })
    return out


def compute_consistency_streak(
    activities: list[dict],
    today: date,
    min_run_days: int | None,
    min_week_km: float | None,
    neutral_weeks: set[str] | None = None,
    weeks: int = DEFAULT_LOOKBACK_WEEKS,
) -> str:
    """Render the consistency field as one compact block.

    Without configured thresholds the output is purely descriptive and says
    so — no streak is claimed, because there is no floor to measure against.
    """
    neutral = neutral_weeks or set()
    summary = weekly_run_summary(activities, today, weeks)
    judged = [w for w in summary if w["covered"]]
    if not judged:
        return "Consistency: no activity window available."

    current = next((w for w in summary if not w["complete"]), None)
    finished = [w for w in judged if w["complete"]]

    days_line = ", ".join(str(w["run_days"]) for w in finished)
    km_line = ", ".join(f"{w['run_km']:.0f}" for w in finished)
    lines = [
        f"Consistency ({len(finished)} complete ISO weeks, Mon–Sun):",
        f"  run days/week: {days_line}",
        f"  km/week:       {km_line}",
    ]
    if current:
        lines.append(
            f"  current week (incomplete): {current['run_days']} run days / "
            f"{current['run_km']:.0f} km"
        )

    empty = [w["iso_week"] for w in finished if w["total_activities"] == 0]
    if empty:
        lines.append(
            f"  ⚠️ no activity recorded at all in: {', '.join(empty)} — "
            f"a tracking gap and a rest week look identical here"
        )

    if min_run_days is None or min_week_km is None:
        lines.append(
            "  ℹ️ No thresholds configured (consistency_min_run_days / "
            "consistency_min_week_km) — no streak claim possible."
        )
        return "\n".join(lines)

    def _holds(w: dict) -> bool:
        return w["run_days"] >= min_run_days and w["run_km"] >= min_week_km

    # Current streak: walk back from the most recent complete week. A neutral
    # week (holiday, illness, declared by the athlete) pauses rather than
    # breaks — telling "could not" from "did not" is the athlete's call, not
    # an inference the counter should make.
    streak = 0
    for w in reversed(finished):
        if w["iso_week"] in neutral:
            continue
        if _holds(w):
            streak += 1
        else:
            break

    longest = 0
    run = 0
    for w in finished:
        if w["iso_week"] in neutral:
            continue
        if _holds(w):
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    hit = sum(1 for w in finished if _holds(w))
    km_txt = f"{min_week_km:g}"
    lines.append(
        f"  ✓ streak: {streak} consecutive week(s) with ≥ {min_run_days} run "
        f"days and ≥ {km_txt} km (longest in window: {longest}; "
        f"{hit}/{len(finished)} weeks met the floor)"
    )
    if neutral & {w["iso_week"] for w in finished}:
        paused = sorted(neutral & {w["iso_week"] for w in finished})
        lines.append(f"  (paused, not counted either way: {', '.join(paused)})")
    return "\n".join(lines)
