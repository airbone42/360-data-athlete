"""Pre-populate the intervals.icu file cache with historical data.

Usage:
    python3 scripts/warmup_cache.py
    python3 scripts/warmup_cache.py --weeks 104 --streams

Options:
    --weeks N     How many weeks of history to load (default: 156 = 3 years)
    --streams     Also cache activity streams (large files, opt-in)
    --rebuild     Force full index rebuild from cached files
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.intervals_client import IntervalsClient
from app.api.intervals_cache import IntervalsFileCache, _is_special, _activity_index_entry, _event_index_entry, _note_index_entry
from app.config import settings
from app.utils.logging import configure

logger = configure(__name__, level="INFO")

CHUNK_WEEKS = 12  # fetch in chunks to avoid huge API responses
CONCURRENCY = 5


async def warmup(athlete_id: str, weeks: int, fetch_streams: bool) -> None:
    client = IntervalsClient(athlete_id)
    cache = IntervalsFileCache(athlete_id)

    today = date.today()
    oldest_total = (today - timedelta(weeks=weeks)).isoformat()

    logger.info("Warming up cache: %d weeks back from %s", weeks, today)
    logger.info("Cache dir: %s", cache._root)

    # --- Build date chunks --------------------------------------------------
    chunks: list[tuple[str, str]] = []
    chunk_end = today
    while True:
        chunk_start = chunk_end - timedelta(weeks=CHUNK_WEEKS)
        if chunk_start.isoformat() < oldest_total:
            chunk_start = date.fromisoformat(oldest_total)
        chunks.append((chunk_start.isoformat(), chunk_end.isoformat()))
        if chunk_start.isoformat() <= oldest_total:
            break
        chunk_end = chunk_start - timedelta(days=1)
    chunks.reverse()

    # --- Reset index --------------------------------------------------------
    cache._index = {
        "_updated_at": "",
        "activities": [],
        "events": [],
        "notes": [],
        "special": [],
    }

    sem = asyncio.Semaphore(CONCURRENCY)
    total_activities = 0
    total_events = 0
    total_notes = 0
    total_wellness = 0
    total_messages = 0
    total_streams = 0

    # --- Fetch activities ---------------------------------------------------
    all_activities: list[dict] = []
    for chunk_oldest, chunk_newest in chunks:
        logger.info("  Activities %s → %s ...", chunk_oldest, chunk_newest)
        try:
            acts = await client.get_activities(chunk_oldest, chunk_newest)
        except Exception as e:
            logger.warning("  Failed: %s", e)
            continue

        # Group by day and write
        by_day: dict[str, list[dict]] = {}
        for act in acts:
            day = (act.get("start_date_local") or "")[:10]
            if day:
                by_day.setdefault(day, []).append(act)
        for day, day_acts in by_day.items():
            cache.write_day("activities", day, day_acts)

        all_activities.extend(acts)
        total_activities += len(acts)
        await asyncio.sleep(0.1)

    # Update activity index
    cache.update_index_activities(all_activities)
    cache.rebuild_compound_events()
    idx_snap = cache.load_index()
    n_races = len([s for s in idx_snap["special"] if s["category"] == "race"])
    n_tests = len([s for s in idx_snap["special"] if s["category"] == "test"])
    n_compound = len(idx_snap.get("compound_events", []))
    logger.info("  → %d activities (%d races, %d tests, %d compound events)", total_activities, n_races, n_tests, n_compound)

    # --- Fetch past events --------------------------------------------------
    logger.info("Fetching past events ...")
    all_events: list[dict] = []
    for chunk_oldest, chunk_newest in chunks:
        # Only past events
        if chunk_newest > today.isoformat():
            chunk_newest = today.isoformat()
        try:
            evs = await client.get_events(chunk_oldest, chunk_newest)
        except Exception as e:
            logger.warning("  events %s→%s failed: %s", chunk_oldest, chunk_newest, e)
            continue
        by_day: dict[str, list[dict]] = {}
        for ev in evs:
            day = (ev.get("start_date_local") or ev.get("start_date") or "")[:10]
            if day:
                by_day.setdefault(day, []).append(ev)
        for day, day_evs in by_day.items():
            cache.write_day("events", day, day_evs)
        all_events.extend(evs)
        total_events += len(evs)
        await asyncio.sleep(0.1)

    cache.update_index_events(all_events, category="WORKOUT")
    logger.info("  → %d events", total_events)

    # --- Fetch past notes ---------------------------------------------------
    logger.info("Fetching past notes ...")
    all_notes: list[dict] = []
    for chunk_oldest, chunk_newest in chunks:
        if chunk_newest > today.isoformat():
            chunk_newest = today.isoformat()
        try:
            notes = await client.get_notes(chunk_oldest, chunk_newest)
        except Exception as e:
            logger.warning("  notes %s→%s failed: %s", chunk_oldest, chunk_newest, e)
            continue
        by_day: dict[str, list[dict]] = {}
        for n in notes:
            day = (n.get("start_date_local") or n.get("start_date") or "")[:10]
            if day:
                by_day.setdefault(day, []).append(n)
        for day, day_notes in by_day.items():
            cache.write_day("notes", day, day_notes)
        all_notes.extend(notes)
        total_notes += len(notes)
        await asyncio.sleep(0.1)

    cache.update_index_events(all_notes, category="NOTE")
    logger.info("  → %d notes", total_notes)

    # --- Fetch wellness history ---------------------------------------------
    logger.info("Fetching wellness history ...")
    try:
        wellness_records = await client.get_wellness_history(oldest_total, today.isoformat())
        for record in wellness_records:
            day = record.get("id", "")[:10]
            if day:
                cache.write_day("wellness", day, [record])
        total_wellness = len(wellness_records)
    except Exception as e:
        logger.warning("  wellness_history failed: %s", e)
    logger.info("  → %d wellness records", total_wellness)

    # --- Fetch athlete settings ---------------------------------------------
    logger.info("Fetching athlete settings ...")
    try:
        settings_data = await client.get_athlete_settings()
        cache.write_settings(settings_data)
        logger.info("  → cached")
    except Exception as e:
        logger.warning("  athlete_settings failed: %s", e)

    # --- Fetch messages for endurance activities ----------------------------
    ENDURANCE_TYPES = {"Run", "Ride"}
    endurance_acts = [a for a in all_activities if a.get("type") in ENDURANCE_TYPES]
    logger.info("Fetching messages for %d endurance activities ...", len(endurance_acts))

    async def fetch_messages(act: dict) -> None:
        nonlocal total_messages
        act_id = str(act.get("id", ""))
        if not act_id:
            return
        # Skip if already cached
        if (cache._root / "messages" / f"{act_id}.json").exists():
            return
        async with sem:
            try:
                msgs = await client.get_activity_messages(act_id)
                cache.write_by_id("messages", act_id, msgs)
                total_messages += 1
            except Exception:
                pass
            await asyncio.sleep(0.05)

    await asyncio.gather(*[fetch_messages(a) for a in endurance_acts])
    logger.info("  → %d message sets cached", total_messages)
    cache.refresh_file_refs()

    # --- Optionally fetch streams -------------------------------------------
    if fetch_streams:
        logger.info("Fetching streams for %d activities ...", len(all_activities))

        async def fetch_stream(act: dict) -> None:
            nonlocal total_streams
            act_id = str(act.get("id", ""))
            if not act_id:
                return
            if (cache._root / "streams" / f"{act_id}.json").exists():
                return
            async with sem:
                try:
                    streams = await client.get_streams(act_id)
                    cache.write_by_id("streams", act_id, streams)
                    total_streams += 1
                except Exception:
                    pass
                await asyncio.sleep(0.05)

        await asyncio.gather(*[fetch_stream(a) for a in all_activities])
        logger.info("  → %d stream files cached", total_streams)
        cache.refresh_file_refs()

    # --- Save index ---------------------------------------------------------
    cache.save_index()

    logger.info("")
    logger.info("Cache warmup complete.")
    logger.info(
        "  Activities: %d | Events: %d | Notes: %d | Wellness: %d | Messages: %d | Streams: %d",
        total_activities, total_events, total_notes, total_wellness, total_messages, total_streams,
    )
    idx = cache.load_index()
    logger.info(
        "  Index: %d activities, %d events, %d notes, %d special (%d races, %d tests)",
        len(idx["activities"]),
        len(idx["events"]),
        len(idx["notes"]),
        len(idx["special"]),
        len([s for s in idx["special"] if s["category"] == "race"]),
        len([s for s in idx["special"] if s["category"] == "test"]),
    )


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Warm up intervals.icu file cache")
    parser.add_argument("--weeks", type=int, default=156, help="Weeks of history to load (default: 156 = 3 years)")
    parser.add_argument("--streams", action="store_true", help="Also cache activity streams (large)")
    args = parser.parse_args()

    athlete_id = settings.intervals_icu_athlete_id
    asyncio.run(warmup(athlete_id, args.weeks, args.streams))


if __name__ == "__main__":
    main()
