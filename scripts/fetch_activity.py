"""Fetch activity detail + paired workout event + wellness from intervals.icu.

Raw streams are left out by default: they run to hundreds of KB, far past the
tool-output limit, and the per-lap / per-zone numbers come from
``analyse_activity.py``. ``--streams`` adds them for debugging.

Usage:
    python3 scripts/fetch_activity.py --activity-id i12345678
    python3 scripts/fetch_activity.py --activity-id i12345678 --streams
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.intervals_cache import CachedIntervalsClient as IntervalsClient
from app.config import settings
from app.utils.activity_helpers import activity_date as _activity_date
from app.utils.tracing import script_span, set_span_io


async def _fetch(athlete_id: str, activity_id: str, with_streams: bool = False) -> dict:
    client = IntervalsClient(athlete_id)

    activity = await client.get_activity(activity_id)
    streams: dict = await client.get_streams(activity_id) if with_streams else {}

    # Fetch paired workout event if available
    planned_workout: dict = {}
    paired_event_id = activity.get("paired_event_id")
    if paired_event_id:
        try:
            planned_workout = await client.get_event(str(paired_event_id))
        except Exception:
            pass

    # Fetch wellness for activity date
    activity_date = _activity_date(activity)
    wellness: dict = {}
    if activity_date:
        try:
            wellness = await client.get_wellness(activity_date)
        except Exception:
            pass

    result = {
        "activity": activity,
        "planned_workout": planned_workout,
        "wellness": wellness,
        "activity_date": activity_date,
    }
    if with_streams:
        result["streams"] = streams
    return result


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch activity detail from intervals.icu")
    parser.add_argument("--activity-id", required=True, help="Activity ID e.g. i12345678")
    parser.add_argument(
        "--streams", action="store_true",
        help="Include raw streams (debug only — hundreds of KB; use analyse_activity.py)",
    )
    args = parser.parse_args()

    athlete_id = settings.intervals_icu_athlete_id
    display = f"Fetch activity detail — {args.activity_id}"
    with script_span(
        "fetch_activity",
        display_name=display,
        activity_id=args.activity_id,
    ):
        result = asyncio.run(_fetch(athlete_id, args.activity_id, args.streams))
        act = result.get("activity") or {}
        set_span_io(
            input={"activity_id": args.activity_id, "streams": args.streams},
            output=f"{act.get('type', '?')} · {act.get('name', '?')}",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.streams else 1))


if __name__ == "__main__":
    main()
