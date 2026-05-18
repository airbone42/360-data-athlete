"""Fetch last N sessions of matching workout type + their activity messages.

Wraps: app.graphs.sub_workout_specialist.history_fetcher.fetch_type_history()

Output: JSON array to stdout.

Usage:
    python3 coach/scripts/fetch_type_history.py \\
        --date YYYY-MM-DD \\
        --type Run \\
        [--tags intervals,z4] \\
        [--max-sessions 3]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.intervals_client import IntervalsClient
from app.config import settings
from app.graphs.sub_workout_specialist.history_fetcher import fetch_type_history
from app.utils.tracing import script_span, set_span_io


async def _fetch(athlete_id: str, date_str: str, directive: dict, max_sessions: int) -> list[dict]:
    # Load recent activities for initial filter (4-week window)
    today = date.fromisoformat(date_str)
    from datetime import timedelta
    oldest = (today - timedelta(weeks=4)).isoformat()
    client = IntervalsClient(athlete_id)
    existing_activities = await client.get_activities(oldest, date_str)

    return await fetch_type_history(
        athlete_id=athlete_id,
        date_str=date_str,
        directive=directive,
        existing_activities=existing_activities,
        max_sessions=max_sessions,
    )


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch type history for specialist agent")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--type", required=True, help="Workout type e.g. Run, Ride, WeightTraining")
    parser.add_argument("--tags", default="", help="Comma-separated tags e.g. core,plyo")
    parser.add_argument("--max-sessions", type=int, default=3)
    args = parser.parse_args()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    directive = {"type": args.type, "tags": tags}

    athlete_id = settings.intervals_icu_athlete_id
    tag_suffix = f" [{','.join(tags)}]" if tags else ""
    display = f"Fetch type history — {args.type}{tag_suffix} (last {args.max_sessions})"
    with script_span(
        "fetch_type_history",
        display_name=display,
        type=args.type,
        tags=",".join(tags),
        max_sessions=args.max_sessions,
    ):
        history = asyncio.run(_fetch(athlete_id, args.date, directive, args.max_sessions))
        set_span_io(
            input={"type": args.type, "tags": tags, "max_sessions": args.max_sessions, "date": args.date},
            output=f"{len(history)} sessions",
        )
    print(json.dumps(history, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
