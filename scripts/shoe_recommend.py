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
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.api.intervals_client import IntervalsClient
from app.graphs.shoe_advisor import (
    SHOE_ADVISOR_LOOKBACK_DAYS,
    build_shoe_context,
    gear_to_shoes,
    load_shoe_profiles,
)
from app.graphs.sub_athlete_context.context_builder import _days_to_next_race
from app.utils.date_windows import cutoff_iso

logger = logging.getLogger(__name__)

# How far ahead to scan the calendar for the next race. Race-prep shoe
# windows (`race_prep_days`) are a few weeks at most, so 90 days covers
# every window with margin.
RACE_LOOKAHEAD_DAYS = 90


async def recommend(workouts: list[dict], weather: str, date_str: str) -> dict:
    """Library function: return shoe context dict (importable by training_flow.py).

    The advisor reads gear + last-used straight from intervals.icu activities
    (nested ``gear.id``). ``SHOE_TRACKING_BACKEND=off`` disables the footer
    entirely.
    """
    run_workouts = [w for w in workouts if w.get("type") == "Run"]
    if not run_workouts:
        return {}

    if settings.shoe_tracking_backend == "off":
        return {}

    profiles = load_shoe_profiles()

    client = IntervalsClient()
    gear = await client.list_gear()
    shoes = gear_to_shoes(gear)
    # Pull the rotation-look-back window of intervals.icu activities so
    # the advisor sees real wear (gear assigned to finished activities via
    # /analyse step 6.55). The window (`SHOE_ADVISOR_LOOKBACK_DAYS`) must
    # exceed a typical rotation rest: a shoe idle beyond it falls out of
    # range, its last-used date is unknown, and the rotation reason
    # degrades to a generic "type/terrain" label instead of "N days unused".
    try:
        oldest = cutoff_iso(date.fromisoformat(date_str), SHOE_ADVISOR_LOOKBACK_DAYS)
        recent_activities = await client.get_activities(oldest, date_str)
    except Exception as exc:
        logger.warning("intervals.icu activities fetch failed (rotation degraded): %s", exc)
        recent_activities = []
    # The distance to the next race decides whether the designated race
    # shoe is eligible at all (race-day lock / race-prep window in
    # `_score_shoe`). A hardcoded None here silently disqualified the race
    # shoe on every push except RACE-typed workouts — race-pace habituation
    # sessions got a trainer recommended instead. Same helper as
    # fetch_context's `raceInDays`, so both paths cannot diverge.
    race_in_days = None
    try:
        today = date.fromisoformat(date_str)
        newest = (today + timedelta(days=RACE_LOOKAHEAD_DAYS)).isoformat()
        upcoming_events = await client.get_events(date_str, newest)
        race_in_days = _days_to_next_race(upcoming_events, today)
    except Exception as exc:
        logger.warning("intervals.icu events fetch failed (race window unknown): %s", exc)
    return build_shoe_context(
        shoes=shoes,
        profiles=profiles,
        activities=recent_activities,
        planned_workouts=run_workouts,
        weather_info=weather,
        race_in_days=race_in_days,
        today_str=date_str,
    )


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
