"""Detect same-day "Koppeleinheit" (previous load) for a given activity.

Returns information about earlier activities completed on the SAME local
date BEFORE the given activity's start time. The Strava-Publisher agent
uses this to compose the optional Vorbelastungs-header line in the
insights block (e.g. „Auf 65 min Z2-Rad heute Morgen").

Classification:
  - ride         → Ride / VirtualRide
  - legs         → WeightTraining or Workout with leg-oriented tag/name
  - double-run   → another Run / VirtualRun earlier same day
  - other        → any other non-trivial activity (>10 min) — still
                   reported so the agent can decide
  - null         → no eligible earlier activity

Heuristic for `legs`: type ∈ {WeightTraining, Workout} AND
  - has tag matching `legs` / `beine` (legacy) / `plyo` (config/workout_parser
    VALID_TAGS), OR name contains a leg keyword (Squat, Lunge, Kniebeuge, RDL,
    calf raise, Wadenheben, Plyo, Beine, Sprung, jump).

Output (JSON, stdout):
    {
      "activity_id": "i12345678",
      "coupling": null  |  {
        "type":         "ride|legs|double-run|other",
        "earlier_id":   "i99999999",
        "earlier_type": "Ride",
        "duration_min": 65,
        "summary":      "65 min Ride (Z2)",
        "gap_min":      125         # minutes between earlier end and this start
      }
    }

Usage:
    python3 scripts/strava_coupling.py --activity-id i12345678
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.intervals_client import IntervalsClient
from app.utils.strava_titles import parse_iso
from app.utils.tracing import script_span, set_span_io

_LEG_KEYWORDS = re.compile(
    r"\b(squat|kniebeug|lunge|ausfall|rdl|romanian|deadlift|kreuzheb|"
    r"waden|calf|plyo|sprung|jump|beine|legs|leg\s*day|hip\s*thrust|"
    r"step[\s-]?up|pistol)\b",
    re.IGNORECASE,
)
# Bilingual leg-tag synonyms ("beine" = legacy German, "legs" = new canonical).
_LEG_TAGS = {"beine", "legs", "plyo"}

_RIDE_TYPES = {"Ride", "VirtualRide"}
_RUN_TYPES = {"Run", "VirtualRun"}
_STRENGTH_TYPES = {"WeightTraining", "Workout"}

_MIN_EARLIER_DURATION_S = 600  # ignore < 10 min stubs


def _moving_minutes(a: dict) -> int:
    secs = a.get("moving_time") or a.get("elapsed_time") or 0
    try:
        return int(round(float(secs) / 60))
    except Exception:
        return 0


def _classify(a: dict) -> str | None:
    t = a.get("type") or ""
    if t in _RIDE_TYPES:
        return "ride"
    if t in _RUN_TYPES:
        return "double-run"
    if t in _STRENGTH_TYPES:
        tags = {(tag or "").lower() for tag in (a.get("tags") or [])}
        name = (a.get("name") or "")
        desc = (a.get("description") or "")
        if tags & _LEG_TAGS:
            return "legs"
        if _LEG_KEYWORDS.search(name) or _LEG_KEYWORDS.search(desc):
            return "legs"
        return "other"
    return "other"


def _format_summary(a: dict, cls: str) -> str:
    mins = _moving_minutes(a)
    typ = a.get("type") or "Activity"
    intensity_hint = ""
    avg_hr = a.get("average_heartrate") or a.get("icu_average_heartrate")
    if isinstance(avg_hr, (int, float)) and avg_hr > 0:
        intensity_hint = f" · {int(round(avg_hr))} bpm avg"
    return f"{mins} min {typ}{intensity_hint}"


async def _coupling(activity_id: str) -> dict:
    iv = IntervalsClient()
    target = await iv.get_activity(activity_id)
    target_start = parse_iso(target["start_date"])
    day = target_start.date().isoformat()
    same_day = await iv.get_activities(oldest=day, newest=day)

    earlier: list[tuple[dict, float]] = []
    for a in same_day:
        if a.get("id") == activity_id:
            continue
        if (a.get("moving_time") or 0) < _MIN_EARLIER_DURATION_S:
            continue
        try:
            a_start = parse_iso(a["start_date"])
        except Exception:
            continue
        if a_start >= target_start:
            continue
        a_end = a_start + timedelta(seconds=a.get("elapsed_time") or 0)
        gap_s = (target_start - a_end).total_seconds()
        earlier.append((a, gap_s))

    if not earlier:
        return {"activity_id": activity_id, "coupling": None}

    # Closest-by-time before this activity wins.
    earlier.sort(key=lambda pair: pair[1])
    chosen, gap_s = earlier[0]
    cls = _classify(chosen) or "other"

    return {
        "activity_id": activity_id,
        "coupling": {
            "type": cls,
            "earlier_id": chosen.get("id"),
            "earlier_type": chosen.get("type"),
            "duration_min": _moving_minutes(chosen),
            "summary": _format_summary(chosen, cls),
            "gap_min": int(round(gap_s / 60)),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Same-day coupling detection for an activity.")
    parser.add_argument("--activity-id", required=True, help="z.B. i12345678")
    args = parser.parse_args()

    display = f"Strava coupling — {args.activity_id}"
    with script_span("strava_coupling", display_name=display, activity_id=args.activity_id):
        result = asyncio.run(_coupling(args.activity_id))
        coupling = result.get("coupling")
        set_span_io(
            input={"activity_id": args.activity_id},
            output=(coupling and coupling.get("summary")) or "no coupling",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
