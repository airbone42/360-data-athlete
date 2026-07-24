"""Schuh-Empfehlung nach Push — wird mit den geplanten Workouts aufgerufen.

Usage:
    echo '[{"type":"Run","intensity":"low","tags":["run"],"coaching_notes":"Weichboden"}]' \
        | python3 scripts/shoe_recommend.py --weather "moderate rain" --date 2026-04-19
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.api.strava_client import StravaClient
from app.api.intervals_client import IntervalsClient
from app.graphs.shoe_advisor import (
    build_shoe_context,
    gear_to_shoes,
    load_shoe_profiles,
    write_shoe_log,
)

logger = logging.getLogger(__name__)


async def recommend(workouts: list[dict], weather: str, date_str: str) -> dict:
    """Library function: return shoe context dict (importable by training_flow.py).

    The wear-history source MUST follow ``SHOE_TRACKING_BACKEND`` — otherwise the
    rotation signal goes blind after an athlete migrates from Strava to native
    intervals.icu gear. With the ``intervals`` backend the advisor reads gear +
    last-used straight from intervals.icu activities (nested ``gear.id``); the
    legacy ``strava`` backend keeps the Strava API path with a ``shoe_log.json``
    fallback. ``off`` disables the footer entirely.
    """
    run_workouts = [w for w in workouts if w.get("type") == "Run"]
    if not run_workouts:
        return {}

    backend = settings.shoe_tracking_backend
    if backend == "off":
        return {}

    profiles = load_shoe_profiles()

    if backend == "intervals":
        client = IntervalsClient()
        gear = await client.list_gear()
        shoes = gear_to_shoes(gear)
        # Pull last 90d intervals.icu activities so the advisor sees real wear
        # (gear assigned to finished activities via /analyse step 6.55). The
        # window must exceed a typical rotation rest: a shoe idle for 40+ days
        # otherwise falls out of range, its last-used date is unknown, and the
        # rotation reason degrades to a generic "type/terrain" label instead of
        # "N days unused".
        try:
            oldest = (date.fromisoformat(date_str) - timedelta(days=90)).isoformat()
            recent_activities = await client.get_activities(oldest, date_str)
        except Exception as exc:
            logger.warning("intervals.icu activities fetch failed (rotation degraded): %s", exc)
            recent_activities = []
        return build_shoe_context(
            shoes=shoes,
            profiles=profiles,
            activities=recent_activities,
            planned_workouts=run_workouts,
            weather_info=weather,
            race_in_days=None,
            today_str=date_str,
            backend="intervals",
        )

    # Legacy Strava backend.
    client = StravaClient()
    shoes = await client.list_shoes()

    # Pull last 90d Strava activities so the advisor sees real gear_id usage
    # (the local shoe_log.json only tracks what was *recommended*, not *worn*).
    # 90d so a long-idle shoe still resolves a real last-used date for the
    # rotation reason (see the intervals path above).
    strava_ok = True
    try:
        after_epoch = int(time.time()) - 90 * 86400
        recent_activities = await client.list_activities(after_epoch=after_epoch)
    except Exception as exc:
        logger.warning("Strava activities fetch failed (rotation falls back to shoe_log): %s", exc)
        recent_activities = []
        strava_ok = False

    ctx = build_shoe_context(
        shoes=shoes,
        profiles=profiles,
        activities=recent_activities,
        planned_workouts=run_workouts,
        weather_info=weather,
        race_in_days=None,
        today_str=date_str,
        backend="strava",
    )

    # Persist recommendation only as fallback when Strava is down — otherwise
    # write_shoe_log would shadow the real gear_id data on the next call.
    if not strava_ok:
        primary = (ctx.get("shoeRecommendation") or {}).get("primary") or {}
        gear_id = primary.get("gear_id") or primary.get("strava_id")
        if gear_id:
            write_shoe_log(gear_id, date_str)

    return ctx


async def _run(workouts: list[dict], weather: str, date_str: str) -> None:
    ctx = await recommend(workouts, weather, date_str)
    if not ctx:
        print("Kein Lauf-Workout — keine Schuh-Empfehlung nötig.")
        return

    rec = ctx.get("shoeRecommendation", {})
    warnings = ctx.get("shoeWarnings", [])

    if not rec.get("primary"):
        print("Keine Schuh-Empfehlung ermittelt.")
        return

    primary = rec["primary"]
    lines = [f"👟 {primary['name']} ({primary.get('distance_km', 0):.0f} km)"]
    if primary.get("reason"):
        lines.append(f"   {primary['reason']}")

    alt = rec.get("alternative")
    if alt:
        lines.append(f"   Alternative: {alt['name']} ({alt.get('distance_km', 0):.0f} km)")

    for w in warnings:
        lines.append(f"   ⚠ {w['name']}: {w['pct_used']:.0f}% Laufleistung erreicht")

    print("\n".join(lines))


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Schuh-Empfehlung nach Plan-Push")
    parser.add_argument("--weather", default="", help="weatherInfo string")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    raw = sys.stdin.read().strip()
    try:
        parsed = json.loads(raw) if raw else []
        # Accept both a bare workouts array and the full plan-directive object
        if isinstance(parsed, dict):
            parsed = parsed.get("workouts", [])
        workouts = parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        workouts = []

    asyncio.run(_run(workouts, args.weather, args.date))


if __name__ == "__main__":
    main()
