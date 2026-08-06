"""Load-cycle analytics — weekly stats, CTL trend, meso/deload detection.

Extracted from context_builder (P4-1); context_builder re-imports every name,
so existing importers keep working.
"""
from __future__ import annotations

from datetime import date, timedelta

TOLERANCE_PCT = 0.12


DELOAD_PCT = 0.20


MIN_CTL = 20


# A week whose TSS collapses is a genuine recovery week (illness / holiday /
# planned deload) even when the smoothed 42-day avgCTL only dips slightly —
# used by _analyze_load_cycle to avoid miscounting it as a "load week".
MIN_WEEK_TSS = 60             # absolute floor — below this a week is recovery


DELOAD_WEEK_TSS_RATIO = 0.5   # or below 50% of the other weeks' mean


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


def _compute_weekly_loads(activities: list[dict], today: date) -> list[int]:
    """Weekly TSS sums for the same 4 windows as _compute_weekly_stats
    (KW-4 … KW-1), so _analyze_load_cycle can spot a genuine low-TSS deload
    week that the smoothed avgCTL masks."""
    loads: list[int] = []
    for w in range(3, -1, -1):
        from_date = (today - timedelta(days=(w + 1) * 7)).isoformat()
        to_date = (today - timedelta(days=w * 7)).isoformat()
        loads.append(
            sum(
                int(a.get("icu_training_load") or 0)
                for a in activities
                if from_date <= (a.get("start_date_local") or "")[:10] <= to_date
            )
        )
    return loads


def _is_deload_week(weekly_loads: list[int], i: int) -> bool:
    """True when week *i*'s TSS is a genuine recovery week — an absolute
    low, or well below the other weeks' mean. A single such week (illness /
    holiday / planned deload) barely moves the 42-day-smoothed avgCTL, so the
    CTL-based streak logic would otherwise miscount it as a load week."""
    if not weekly_loads or i >= len(weekly_loads):
        return False
    load = weekly_loads[i]
    others = [w for j, w in enumerate(weekly_loads) if j != i and w > 0]
    if not others:
        return False
    ref = sum(others) / len(others)
    return load < MIN_WEEK_TSS or load < DELOAD_WEEK_TSS_RATIO * ref


def _analyze_load_cycle(
    weekly_stats: list[dict], weekly_loads: list[int] | None = None
) -> str:
    ctl_values = [_safe_float(w["avgCTL"]) for w in weekly_stats]

    load_weeks_in_row = 0
    unplanned_low_weeks = 0

    for i in range(1, len(ctl_values)):
        prev, curr = ctl_values[i - 1], ctl_values[i]
        if prev < MIN_CTL or curr < MIN_CTL:
            continue

        # A genuine low-TSS week resets the streak even if avgCTL held —
        # the smoothed CTL masks an illness/holiday week the weekly TSS shows.
        if weekly_loads is not None and _is_deload_week(weekly_loads, i):
            load_weeks_in_row = 0
            unplanned_low_weeks = 0
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


def _safe_float(val: str) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
