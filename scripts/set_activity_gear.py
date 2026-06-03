"""Assign a shoe (gear) to a finished intervals.icu activity.

This is the intervals.icu-backend replacement for the old Strava shoe
footer: instead of writing a text recommendation onto the planned event,
the coach sets the recommended shoe on the *completed* activity, and
intervals.icu accumulates that shoe's mileage natively.

The athlete corrects the choice in intervals.icu if they wore something
else. Idempotent: an activity that already carries an *active* shoe is
left untouched (unless --force). A retired / non-shoe / unknown gear id
(a stale auto-default "phantom") does NOT count as an assignment and is
overwritten so the analysis self-corrects.

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
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.intervals_client import IntervalsClient
from app.config import settings
from app.graphs.shoe_advisor import build_shoe_context, gear_to_shoes, load_shoe_profiles

# Markers written by push_workouts._format_shoe_footer onto the planned event
# (intervals backend). The machine marker carries the gear id directly; the
# human line is the legacy/strava fallback (name → gear id lookup).
_GEAR_MARKER_RE = re.compile(r"\[coach-gear:\s*(g\w+)\]")
_SHOE_REC_RE = re.compile(r"Shoe recommendation:\s*([^\n(—]+)")


async def _fetch_paired_event(icu: IntervalsClient, activity: dict) -> dict:
    """Return the planned event paired with a finished activity (or {})."""
    pid = activity.get("paired_event_id")
    if not pid:
        return {}
    try:
        return await icu.get_event(str(pid)) or {}
    except Exception:
        return {}


def _gear_from_planned_event(plan: dict, gear_list: list[dict]) -> tuple[str | None, str]:
    """Read the push-time shoe pick persisted on the planned event.

    The push-time recommendation already weighed every factor (surface, pace,
    preferences, mileage, rotation, weather), so reading it back is exact and
    avoids re-deriving from the finished activity's partial data. Priority:
    the machine ``[coach-gear:<id>]`` marker, then the human
    "Shoe recommendation: <name>" line mapped to a gear id. Only an *active*
    Shoes-type gear is returned; anything stale falls through to ``None`` so the
    caller re-derives.
    """
    desc = (plan or {}).get("description") or ""
    active = {
        g.get("id"): g
        for g in gear_list
        if (g.get("type") or "") == "Shoes" and not g.get("retired")
    }
    m = _GEAR_MARKER_RE.search(desc)
    if m and m.group(1) in active:
        return m.group(1), f"Plan-Empfehlung: {active[m.group(1)].get('name')}"
    m = _SHOE_REC_RE.search(desc)
    if m:
        name = m.group(1).strip().lower()
        for gid, g in active.items():
            if (g.get("name") or "").strip().lower() == name:
                return gid, f"Plan-Empfehlung: {g.get('name')}"
    return None, ""


async def _recommend_gear_for_activity(
    icu: IntervalsClient,
    activity: dict,
    plan: dict | None = None,
    gear_list: list[dict] | None = None,
) -> dict | None:
    """Return the advisor's primary shoe recommendation for a finished activity.

    Fallback path only — used when the planned event carries no persisted
    push-time pick (legacy / non-coach activities). Treats the activity as the
    'planned run' so the existing scoring (terrain, pace, rotation, mileage)
    applies. Returns the recommendation entry ({gear_id, name, ...}) or None.
    """
    today_str = (activity.get("start_date_local") or date.today().isoformat())[:10]
    # The completed activity carries no `surface` and usually an empty
    # `description`, so terrain detection would default to asphalt and the
    # analysis-time pick would diverge from the push-time pick (which scored
    # against the planned workout's surface/notes). Prefer the linked planned
    # event: its description holds the specialist's terrain wording
    # ("Trail …", "Forstweg …"), which drives the same terrain classification
    # the push-time recommendation used. Fall back to the activity fields when
    # no planned event is paired.
    if plan is None:
        plan = await _fetch_paired_event(icu, activity)
    planned = [{
        "type": activity.get("type"),
        "surface": plan.get("surface") or activity.get("surface") or "",
        "tags": plan.get("tags") or activity.get("tags") or [],
        "workout_type": plan.get("workout_type") or activity.get("workout_type") or "",
        "intensity": plan.get("intensity") or activity.get("intensity") or "",
        "coaching_notes": plan.get("description") or activity.get("description") or "",
    }]
    gear = gear_list if gear_list is not None else await icu.list_gear()
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

    # Fetched once and reused by the idempotency guard and the --auto path.
    gear_list = await icu.list_gear()

    # intervals.icu exposes an assigned shoe as a nested `gear` object
    # ({"id": ...}), not a flat `gear_id` — read the id from there (with a
    # legacy flat-field fallback) so the idempotency guard actually fires.
    existing = (activity.get("gear") or {}).get("id") or activity.get("gear_id")
    if existing and not force:
        # A retired or non-shoe gear id is a stale auto-default ("phantom" —
        # e.g. an old default shoe Garmin/intervals.icu stamps onto every
        # imported activity). That is NOT a real assignment and must not block
        # auto-correction. Only an active Shoes-type gear counts as a genuine
        # existing assignment worth preserving.
        entry = next((g for g in gear_list if g.get("id") == existing), None)
        is_active_shoe = (
            entry is not None
            and (entry.get("type") or "") == "Shoes"
            and not entry.get("retired")
        )
        if is_active_shoe:
            print(f"– {activity_id}: trägt bereits aktiven Schuh gear={existing} — übersprungen (--force zum Überschreiben).")
            return
        label = f"{entry.get('name')} " if entry and entry.get("name") else ""
        print(f"  {activity_id}: vorhandenes gear={existing} {label}ist retired/kein aktiver Schuh (Phantom) — wird ersetzt.")

    reason = ""
    if auto and not gear_id:
        plan = await _fetch_paired_event(icu, activity)
        # 1. Deterministic: use the push-time recommendation persisted on the
        #    planned event (full-context pick). This matches push and analysis
        #    by construction.
        gear_id, why = _gear_from_planned_event(plan, gear_list)
        if gear_id:
            reason = f" ({why})"
        else:
            # 2. Fallback (legacy / non-coach runs without a persisted pick):
            #    re-derive from the planned context.
            primary = await _recommend_gear_for_activity(icu, activity, plan=plan, gear_list=gear_list)
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
