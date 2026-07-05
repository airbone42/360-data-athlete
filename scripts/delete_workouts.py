"""Delete workout events from intervals.icu.

Usage:
    python3 coach/scripts/delete_workouts.py --event-ids 123,456
    python3 coach/scripts/delete_workouts.py --date YYYY-MM-DD --prefix coach-
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
from app.utils.event_backup import backup_events_before_delete


async def _delete_by_ids(client: IntervalsClient, event_ids: list[int]) -> list[int]:
    # Capture full content BEFORE deleting so it is never silently lost.
    fetched = []
    for eid in event_ids:
        try:
            fetched.append(await client.get_event(str(eid)))
        except Exception:  # noqa: BLE001 — event may already be gone; back up what we can
            pass
    backup_events_before_delete(fetched, reason="delete_workouts --event-ids")
    results = []
    for eid in event_ids:
        await client.delete_event(eid)
        results.append(eid)
    return results


async def _delete_by_prefix(client: IntervalsClient, date_str: str, prefix: str) -> list[str]:
    events = await client.get_events(date_str, date_str)
    to_delete = [e for e in events if str(e.get("uid", "")).startswith(prefix)]
    # Capture full content BEFORE deleting so it is never silently lost.
    backup_events_before_delete(to_delete, reason=f"delete_workouts --prefix {prefix} {date_str}")
    deleted = []
    for e in to_delete:
        await client.delete_event(e["id"])
        deleted.append(e["uid"])
    return deleted


async def _run(args: argparse.Namespace) -> None:
    client = IntervalsClient(settings.intervals_icu_athlete_id)
    if args.event_ids:
        ids = [int(x.strip()) for x in args.event_ids.split(",")]
        deleted = await _delete_by_ids(client, ids)
        print(json.dumps({"deleted_ids": deleted}))
    elif args.date and args.prefix:
        deleted = await _delete_by_prefix(client, args.date, args.prefix)
        print(json.dumps({"deleted_uids": deleted}))
    else:
        print("Error: provide --event-ids or both --date and --prefix", file=sys.stderr)
        sys.exit(1)


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Delete workout events from intervals.icu")
    parser.add_argument("--event-ids", help="Comma-separated event IDs")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--prefix", default="coach-", help="UID prefix filter (default: coach-)")
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
