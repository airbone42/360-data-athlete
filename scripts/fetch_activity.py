"""Fetch activity detail + streams + paired workout event from intervals.icu.

Usage:
    python3 coach/scripts/fetch_activity.py --activity-id i12345678
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
from app.utils.tracing import script_span, set_span_io


async def _fetch(athlete_id: str, activity_id: str) -> dict:
    client = IntervalsClient(athlete_id)

    activity, streams = await asyncio.gather(
        client.get_activity(activity_id),
        client.get_streams(activity_id),
    )

    # Fetch paired workout event if available
    planned_workout: dict = {}
    paired_event_id = activity.get("paired_event_id")
    if paired_event_id:
        try:
            planned_workout = await client.get_event(str(paired_event_id))
        except Exception:
            pass

    # Fetch wellness for activity date
    activity_date = (activity.get("start_date_local") or "")[:10]
    wellness: dict = {}
    if activity_date:
        try:
            wellness = await client.get_wellness(activity_date)
        except Exception:
            pass

    return {
        "activity": activity,
        "streams": streams,
        "planned_workout": planned_workout,
        "wellness": wellness,
        "activity_date": activity_date,
    }


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch activity detail from intervals.icu")
    parser.add_argument("--activity-id", required=True, help="Activity ID e.g. i12345678")
    args = parser.parse_args()

    athlete_id = settings.intervals_icu_athlete_id
    display = f"Fetch activity detail — {args.activity_id}"
    with script_span(
        "fetch_activity",
        display_name=display,
        activity_id=args.activity_id,
    ):
        result = asyncio.run(_fetch(athlete_id, args.activity_id))
        act = result.get("activity") or {}
        streams = result.get("streams") or {}
        set_span_io(
            input={"activity_id": args.activity_id},
            output=f"{act.get('type', '?')} · {act.get('name', '?')} · {len(streams)} streams",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
