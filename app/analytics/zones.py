"""HR-zone analytics — distribution, cardiac-drift correction, hard-stimulus detection.

Extracted from context_builder (P4-1); context_builder re-imports every name,
so existing importers keep working.
"""
from __future__ import annotations

from datetime import date, timedelta

from app import sports

from app.utils.activity_helpers import activity_date

# Run + bike variants from the sport registry (excludes Swim on purpose:
# swim HR zones are not comparable to the run/bike zone model used here).
CARDIO_TYPES = sports.RUN_TYPES | sports.BIKE_TYPES


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


def _fold_zones(raw: list, n: int = 5) -> tuple[list[float], bool]:
    """Fold zone times beyond the n-th into the top bucket.

    A 7-zone model (e.g. a ride profile) must not lose Z6/Z7 time. Returns
    (n-bucket list, whether anything was folded).
    """
    raw = list(raw)
    folded = len(raw) > n
    head = raw[:n]
    if folded:
        head[n - 1] = head[n - 1] + sum(raw[n:])
    head += [0] * (n - len(head))
    return head, folded


def _zone_sums(with_hr: list[dict]) -> tuple[list[float], bool]:
    sums = [0, 0, 0, 0, 0]
    any_folded = False
    for a in with_hr:
        raw, folded = _fold_zones(a.get("icu_hr_zone_times") or [])
        any_folded = any_folded or folded
        corrected = _correct_cardiac_drift(raw, a.get("moving_time", 0))
        for i, secs in enumerate(corrected):
            sums[i] += secs
    return sums, any_folded


def _zones_text(sums: list[float], top_plus: bool, sep: str = " | ") -> str:
    total = sum(sums)
    labels = [f"Z{i + 1}" for i in range(5)]
    if top_plus:
        labels[4] = "Z5+"
    return sep.join(
        f"{lab}: {round(s / total * 100)}%" for lab, s in zip(labels, sums)
    )


def _compute_zone_distribution(activities: list[dict]) -> str:
    cardio = [a for a in activities if a.get("type") in CARDIO_TYPES]
    with_hr = [
        a for a in cardio if any(s > 0 for s in (a.get("icu_hr_zone_times") or []))
    ]
    without_hr = [a for a in cardio if a not in with_hr]

    zone_sums, top_plus = _zone_sums(with_hr)

    total_secs = sum(zone_sums)
    total_min_no_hr = sum(
        round(a.get("moving_time", 0) / 60) for a in without_hr
    )

    if total_secs == 0:
        return "No HR data available"

    total_min_hr = round(total_secs / 60)
    zones_str = _zones_text(zone_sums, top_plus)
    result = f"{zones_str} ({total_min_hr} min with HR data)"

    # Per-sport split when the window mixes sports: each sport's zone times
    # come from intervals.icu against that sport's own zone bounds, so "Z2"
    # differs in bpm between run and ride.
    by_family: dict[str, list[dict]] = {}
    for a in with_hr:
        fam = sports.canonical_type(a.get("type"))
        if fam in ("Run", "Ride"):
            by_family.setdefault(fam, []).append(a)
    if len(by_family) > 1:
        parts = []
        for fam in ("Run", "Ride"):
            sums, plus = _zone_sums(by_family[fam])
            if sum(sums) > 0:
                parts.append(f"{fam}: {_zones_text(sums, plus, ' ')}")
        result += " | " + " | ".join(parts)

    if without_hr:
        missing = ", ".join(
            f"{activity_date(a)} {a.get('type', '')}"
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
    """Total seconds spent in Z4 and above according to icu_hr_zone_times.

    A 7-zone model (common for Ride profiles) carries Z6/Z7 above Z5; that
    time is at least as hard and counts here, consistent with the "Z5+"
    folding in the zone distribution.
    """
    zone_times = list(activity.get("icu_hr_zone_times") or [])
    return float(sum(t or 0 for t in zone_times[3:]))


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
        d_str = activity_date(a)
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


def _fmt(val: float | None, suffix: str) -> str:
    if val is None:
        return "-"
    return f"{val:.1f}{suffix}"
