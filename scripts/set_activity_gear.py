"""Assign a shoe (gear) to a finished intervals.icu activity.

This is the intervals.icu-backend replacement for the old Strava shoe
footer: instead of writing a text recommendation onto the planned event,
the coach sets the recommended shoe on the *completed* activity, and
intervals.icu accumulates that shoe's mileage natively.

The athlete corrects the choice in intervals.icu if they wore something
else. Idempotent: an activity that already carries a gear_id is left
untouched (unless --force).

Usage:
    # explicit shoe
    python3 scripts/set_activity_gear.py --activity-id i12345 --gear-id b9876
    # let the advisor pick the recommended shoe for the activity
    python3 scripts/set_activity_gear.py --activity-id i12345 --auto
    # preview only
    python3 scripts/set_activity_gear.py --activity-id i12345 --auto --dry-run

Used by /analyse step 6.55 (intervals backend only).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.intervals_client import IntervalsClient
from app.config import settings
from app.graphs.shoe_advisor import build_shoe_context, gear_to_shoes, load_shoe_profiles


async def _recommend_gear_for_activity(icu: IntervalsClient, activity: dict) -> dict | None:
    """Return the advisor's primary shoe recommendation for a finished activity.

    Treats the activity as the 'planned run' so the existing scoring
    (terrain, pace, rotation, mileage) applies. Returns the recommendation
    entry ({gear_id, name, ...}) or None.
    """
    today_str = (activity.get("start_date_local") or date.today().isoformat())[:10]
    planned = [{
        "type": activity.get("type"),
        "surface": activity.get("surface") or "",
        "tags": activity.get("tags") or [],
        "workout_type": activity.get("workout_type") or "",
        "intensity": activity.get("intensity") or "",
        "coaching_notes": activity.get("description") or "",
    }]
    gear = await icu.list_gear()
    shoes = gear_to_shoes(gear)
    profiles = load_shoe_profiles()
    # Recent activities for rotation context (gear_id already set on past runs).
    oldest = (date.fromisoformat(today_str) - timedelta(days=30)).isoformat()
    try:
        recent = await icu.get_activities(oldest, today_str)
    except Exception:
        recent = []
    ctx = build_shoe_context(
        shoes=shoes,
        profiles=profiles,
        activities=recent,
        planned_workouts=planned,
        weather_info="",
        race_in_days=None,
        today_str=today_str,
        backend="intervals",
    )
    return (ctx.get("shoeRecommendation") or {}).get("primary")


async def _run(activity_id: str, gear_id: str | None, auto: bool, dry_run: bool, force: bool) -> None:
    icu = IntervalsClient()
    activity = await icu.get_activity(activity_id)

    if activity.get("type") not in ("Run", "VirtualRun"):
        print(f"– {activity_id}: keine Lauf-Aktivität ({activity.get('type')}) — übersprungen.")
        return

    # intervals.icu exposes an assigned shoe as a nested `gear` object
    # ({"id": ...}), not a flat `gear_id` — read the id from there (with a
    # legacy flat-field fallback) so the idempotency guard actually fires.
    existing = (activity.get("gear") or {}).get("id") or activity.get("gear_id")
    if existing and not force:
        print(f"– {activity_id}: trägt bereits gear={existing} — übersprungen (--force zum Überschreiben).")
        return

    reason = ""
    if auto and not gear_id:
        primary = await _recommend_gear_for_activity(icu, activity)
        if not primary or not primary.get("gear_id"):
            print(f"– {activity_id}: keine Schuh-Empfehlung ermittelt — nichts gesetzt.")
            return
        gear_id = primary["gear_id"]
        reason = f" ({primary.get('name')} — {primary.get('reason', '')})".rstrip()

    if not gear_id:
        print("⚠ Weder --gear-id noch --auto angegeben.", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print(f"[DRY-RUN] würde gear_id={gear_id} auf {activity_id} setzen{reason}.")
        return

    await icu.set_activity_gear(activity_id, gear_id)
    print(f"✓ {activity_id}: gear_id={gear_id} gesetzt{reason}.")


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Assign a shoe to an intervals.icu activity")
    parser.add_argument("--activity-id", required=True)
    parser.add_argument("--gear-id", help="intervals.icu gear id to assign")
    parser.add_argument("--auto", action="store_true", help="Let the shoe advisor pick the shoe")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing gear_id")
    args = parser.parse_args()

    if settings.shoe_tracking_backend != "intervals" and not args.gear_id:
        print(
            f"⚠ SHOE_TRACKING_BACKEND={settings.shoe_tracking_backend!r} — --auto braucht das "
            "intervals-Backend. Mit explizitem --gear-id trotzdem möglich.",
            file=sys.stderr,
        )
        sys.exit(1)

    asyncio.run(_run(args.activity_id, args.gear_id, args.auto, args.dry_run, args.force))


if __name__ == "__main__":
    main()
