"""RPE-vs-intensity mismatch: does the effort report match the heart rate?

A prescribed intensity band can be wrong, and the usual signals cannot say
so. Sessions executed inside a faulty band reproduce it rather than
contradict it — their HR ceilings then read as confirmation that the band
was right. The one channel that stays independent is the athlete's own
effort report: a block that comes back far easier than its heart rate
predicts is evidence against the band.

This module supplies the pure pieces (parsing, windowing, verdict) so the
audit check and any caller share one implementation. Fetching lives in the
caller.

Threshold constants are research-derived and carry their source inline; do
not tune them by feel.
"""

from __future__ import annotations

import re
from typing import Any

# ── RPE parsing ──────────────────────────────────────────────────────
#
# RPE arrives as free text in day notes and activity descriptions, in the
# shapes people actually type: "RPE 6", "RPE: 6", "RPE 7-8", "RPE 6,5" and
# — the shape that matters in practice — "RPE Renntempo-Block: 6", where a
# label sits between the token and the number. A short same-line gap is
# therefore allowed, deliberately short so that prose like "RPE war
# niedrig, gestern lag sie bei 8" does not get harvested. A range is read
# as its midpoint: an athlete writing 7-8 is describing one effort.
_RPE_RE = re.compile(
    r"RPE\b[^\d\n]{0,30}?"
    r"(?P<value>\d{1,2}(?:[.,]\d)?(?:\s*[-–]\s*\d{1,2}(?:[.,]\d)?)?)",
    re.IGNORECASE,
)


def parse_rpe_values(text: str | None) -> list[float]:
    """Every RPE figure mentioned in a free-text block, in order."""
    if not text:
        return []
    out: list[float] = []
    for m in _RPE_RE.finditer(text):
        raw = m.group("value").replace(",", ".").replace("–", "-")
        parts = [p for p in raw.split("-") if p.strip()]
        try:
            nums = [float(p) for p in parts]
        except ValueError:
            continue
        if not nums:
            continue
        value = sum(nums) / len(nums)
        if 0 < value <= 10:
            out.append(round(value, 2))
    return out


# ── Intensity of the hard part ───────────────────────────────────────


def best_rolling_mean(values: list[float | int | None], window_s: int) -> float | None:
    """Highest mean over any contiguous `window_s` samples (1 Hz assumed).

    Session averages are useless here: a 10-minute quality block inside an
    easy hour disappears into the mean. The peak sustained window is what
    the prescription actually addressed.
    """
    clean = [float(v) for v in values if v]
    if window_s <= 0 or len(clean) < window_s:
        return None
    running = sum(clean[:window_s])
    best = running
    for i in range(window_s, len(clean)):
        running += clean[i] - clean[i - window_s]
        if running > best:
            best = running
    return best / window_s


def pct_of_threshold(hr: float | None, lthr: float | int | None) -> float | None:
    if not hr or not lthr:
        return None
    return hr / float(lthr) * 100.0


# ── Erwartungs-Korridor und Auslöse-Schwellen ────────────────────────
#
# Source: framework/research/rpe-vs-percent-lthr-endurance-run.md
#
# The literature gives no point mapping from %LTHR to an RPE value — only a
# corridor roughly two CR10 points wide, and the spread around it is large
# (between athletes SD ≈ 1 CR10; within one athlete SEM 0.3–1.05). That is
# the whole reason the thresholds below sit where they do: a one-point
# deviation is test-retest noise, and a check that fires on noise gets
# ignored, which is worse than no check.
#
# Corridor: (pct_lthr_low, pct_lthr_high, cr10_floor, cr10_ceiling)
CORRIDOR: tuple[tuple[int, int, float, float], ...] = (
    (85, 89, 2, 4),
    (90, 94, 4, 6),
    (95, 99, 5, 7),
    (100, 102, 7, 8),
    (103, 106, 8, 10),
    (107, 999, 9, 10),
)

MIN_BLOCK_MIN = 8            # below this the RPE steady state is not established
ACTIVITY_START_BUFFER_MIN = 10   # cardiac-startup window is not a block
LOW_PRIMARY_DELTA = 2.0      # ≥ 2 CR10 under the floor — beyond population SD
LOW_STRONG_SINGLE_DELTA = 3.0
LOW_STRONG_RECURRENT_COUNT = 2
RECURRENT_WINDOW_DAYS = 14
HIGH_PRIMARY_DELTA = 2.0
HOT_TEMP_C = 22              # anchor: heat-pace-penalty-at-fixed-hr.md
OUTDOOR_FLOOR_ADJUST = -1    # outdoor RPE runs ~2 CR10 below indoor at equal HR
HEAT_FLOOR_ADJUST = -1
MAX_DECOUPLING_PCT = 10      # anchor: compliance-decoupling-thresholds.md


def corridor_for(pct_lthr: float) -> tuple[float, float] | None:
    for lo, hi, floor, ceiling in CORRIDOR:
        if lo <= pct_lthr <= hi:
            return float(floor), float(ceiling)
    return None


def evaluate_block(
    *,
    pct_lthr: float | None,
    rpe: float | None,
    duration_min: float,
    start_offset_min: float = 99.0,
    outdoor: bool = True,
    temp_c: float | None = None,
    decoupling_pct: float | None = None,
    prior_low_primaries: int = 0,
) -> dict[str, Any] | None:
    """Verdict for one qualifying block, or None when nothing is signalled.

    Returns a dict with `verdict` in {RPE_LOW_PRIMARY, RPE_LOW_STRONG,
    RPE_HIGH_RECURRENT}, the corridor actually used after confounder
    adjustment, and the confounders that were applied — a finding the reader
    cannot audit is a finding they cannot act on.

    Deliberately not implemented: the research proposes re-running the
    comparison against first-half HR when decoupling is high. That needs a
    corridor re-resolution on a different intensity and would make the
    verdict depend on an unvalidated second path, so a block whose
    decoupling exceeds the ceiling is skipped instead of guessed at.
    """
    if rpe is None or pct_lthr is None:
        return None
    if duration_min < MIN_BLOCK_MIN:
        return None
    if start_offset_min < ACTIVITY_START_BUFFER_MIN:
        return None
    if decoupling_pct is not None and decoupling_pct > MAX_DECOUPLING_PCT:
        return None

    bounds = corridor_for(pct_lthr)
    if bounds is None:
        return None
    floor, ceiling = bounds

    applied: list[str] = []
    if outdoor:
        floor += OUTDOOR_FLOOR_ADJUST
        applied.append("outdoor")
    if temp_c is not None and temp_c >= HOT_TEMP_C:
        floor += HEAT_FLOOR_ADJUST
        applied.append(f"heat≥{HOT_TEMP_C}°C")

    delta_low = floor - rpe
    delta_high = rpe - ceiling

    base = {
        "pct_lthr": round(pct_lthr, 1),
        "rpe": rpe,
        "corridor": (floor, ceiling),
        "confounders_applied": applied,
        "duration_min": round(duration_min, 1),
    }

    if delta_low >= LOW_STRONG_SINGLE_DELTA:
        return {**base, "verdict": "RPE_LOW_STRONG", "delta": round(delta_low, 1),
                "reason": "single_large"}
    if delta_low >= LOW_PRIMARY_DELTA:
        if prior_low_primaries + 1 >= LOW_STRONG_RECURRENT_COUNT:
            return {**base, "verdict": "RPE_LOW_STRONG",
                    "delta": round(delta_low, 1), "reason": "recurrent",
                    "recurrent_n": prior_low_primaries + 1}
        return {**base, "verdict": "RPE_LOW_PRIMARY", "delta": round(delta_low, 1)}
    if delta_high >= HIGH_PRIMARY_DELTA and prior_low_primaries == 0:
        # The high direction is a readiness signal, not a band signal, and
        # single occurrences are not reported: routing belongs to the
        # HRV/RHR overload path.
        return {**base, "verdict": "RPE_HIGH_RECURRENT", "delta": round(delta_high, 1)}
    return None


# ── Kandidaten-Auswahl ───────────────────────────────────────────────
#
# Session-RPE is a single number for a whole session, so attributing it to
# one intensity only holds when the session has one dominant quality block.
# The research is explicit that a multi-block session breaks the mapping.
# Approximation used here: a day qualifies only when exactly one activity
# carries upper-zone time and the day's note carries exactly one RPE value.
# Ambiguity is dropped rather than resolved by guessing.

UPPER_ZONE_MIN_SECONDS = 240   # some genuine time above the aerobic zones


def _day(value: str | None) -> str:
    return (value or "")[:10]


def upper_zone_seconds(activity: dict) -> int:
    zones = activity.get("icu_hr_zone_times") or []
    if len(zones) < 5:
        return 0
    return int(zones[3] or 0) + int(zones[4] or 0)


def select_candidates(activities: list[dict], notes: list[dict]) -> list[dict]:
    """Days where one quality session meets exactly one reported RPE."""
    rpe_by_day: dict[str, float] = {}
    for note in notes or []:
        values = parse_rpe_values(note.get("description"))
        if len(values) == 1:
            day = _day(note.get("start_date_local"))
            if day in rpe_by_day:      # two notes, two values — ambiguous
                rpe_by_day[day] = float("nan")
            else:
                rpe_by_day[day] = values[0]

    by_day: dict[str, list[dict]] = {}
    for act in activities or []:
        by_day.setdefault(_day(act.get("start_date_local")), []).append(act)

    out: list[dict] = []
    for day, rpe in sorted(rpe_by_day.items()):
        if rpe != rpe:                  # NaN — ambiguous day
            continue
        quality = [a for a in by_day.get(day, [])
                   if upper_zone_seconds(a) >= UPPER_ZONE_MIN_SECONDS]
        if len(quality) != 1:
            continue
        out.append({"date": day, "rpe": rpe, "activity": quality[0]})
    return out


def is_outdoor(activity: dict) -> bool:
    if activity.get("trainer") or activity.get("icu_ignore_pace"):
        return False
    return str(activity.get("type") or "").lower() != "virtualrun"
