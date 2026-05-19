"""Post a message to an intervals.icu activity or save a feedback note as a NOTE event.

Usage:
    # Post activity message (coaching feedback — preferred for activity-bound feedback):
    python3 coach/scripts/post_message.py --activity-id i12345 --message "Gute Einheit!"
    python3 coach/scripts/post_message.py --activity-id i12345 --note "Gute Einheit!"   # --note is accepted as alias

    # Save feedback as NOTE event (date-scoped, NOT activity-bound):
    python3 coach/scripts/post_message.py --date YYYY-MM-DD --note "Beine müde"

Routing rule (important — silent-drift case 2026-05-19):
- `--activity-id` is present → ALWAYS post to the activity as a message.
  Accepts both `--message` and `--note` as the text source. Earlier
  versions silently ignored `--note` in combination with `--activity-id`
  and fell through to the date-NOTE path, creating a stray NOTE event
  next to the activity instead of attaching feedback to the activity.
- `--activity-id` absent + `--date` + `--note` → create a date-NOTE.
- Anything else → error.
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

    # Resolve text source: `--message` and `--note` are accepted as aliases
    # when an activity-id is present (the routing decision is driven by
    # whether `--activity-id` is given, not by which text flag the caller
    # picked).
    activity_text = args.message or args.note if args.activity_id else None

    if args.activity_id and activity_text:
        result = await client.post_activity_message(args.activity_id, activity_text)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.activity_id and not activity_text:
        print(
            "Error: --activity-id given but no text provided. Pass --message or --note with the activity-bound feedback.",
            file=sys.stderr,
        )
        sys.exit(1)

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
        print(
            "Error: provide --activity-id + (--message or --note), or --date + --note.",
            file=sys.stderr,
        )
        sys.exit(1)


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Post message to intervals.icu")
    parser.add_argument("--activity-id", help="intervals.icu activity ID e.g. i12345678")
    parser.add_argument("--message", help="Message text for activity (accepted alongside --note when --activity-id is set)")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--note", help="Text for NOTE event (or — when --activity-id is set — activity-bound feedback)")
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
