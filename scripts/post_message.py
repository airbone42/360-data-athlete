"""Post a message to an intervals.icu activity or save a feedback note as a NOTE event.

Usage:
    # Post activity message (coaching feedback):
    python3 coach/scripts/post_message.py --activity-id i12345 --message "Gute Einheit!"

    # Save feedback as NOTE event:
    python3 coach/scripts/post_message.py --date YYYY-MM-DD --note "Beine müde"
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


async def _run(args: argparse.Namespace) -> None:
    client = IntervalsClient(settings.intervals_icu_athlete_id)

    if args.activity_id and args.message:
        result = await client.post_activity_message(args.activity_id, args.message)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.date and args.note:
        note_event = [
            {
                "category": "NOTE",
                "start_date_local": f"{args.date}T08:00:00",
                "name": "Athleten-Feedback",
                "description": args.note,
            }
        ]
        result = await client.post_events_bulk(note_event)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print("Error: provide --activity-id + --message, or --date + --note", file=sys.stderr)
        sys.exit(1)


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Post message to intervals.icu")
    parser.add_argument("--activity-id", help="intervals.icu activity ID e.g. i12345678")
    parser.add_argument("--message", help="Message text for activity")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--note", help="Text for NOTE event")
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
