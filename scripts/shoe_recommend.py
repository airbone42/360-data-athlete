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
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.strava_client import StravaClient
from app.graphs.shoe_advisor import build_shoe_context, load_shoe_profiles, write_shoe_log

logger = logging.getLogger(__name__)


async def recommend(workouts: list[dict], weather: str, date_str: str) -> dict:
    """Library function: return shoe context dict (importable by training_flow.py)."""
    run_workouts = [w for w in workouts if w.get("type") == "Run"]
    if not run_workouts:
        return {}

    client = StravaClient()
    shoes = await client.list_shoes()
    profiles = load_shoe_profiles()

    # Pull last 30d Strava activities so the advisor sees real gear_id usage
    # (intervals.icu activities don't carry gear_id reliably; the local
    # shoe_log.json only tracks what was *recommended*, not what was *worn*).
    strava_ok = True
    try:
        after_epoch = int(time.time()) - 30 * 86400
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
    )

    # Persist recommendation only as fallback when Strava is down — otherwise
    # write_shoe_log would shadow the real gear_id data on the next call.
    if not strava_ok:
        primary = (ctx.get("shoeRecommendation") or {}).get("primary") or {}
        if primary.get("strava_id"):
            write_shoe_log(primary["strava_id"], date_str)

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
