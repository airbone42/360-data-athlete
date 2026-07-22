"""File-based cache for intervals.icu API data.

Structure:
    coach/cache/
        activities/YYYY-MM-DD.json   — array of activities for that day
        events/YYYY-MM-DD.json       — array of events for that day
        wellness/YYYY-MM-DD.json     — wellness snapshot for that day
        streams/{activity_id}.json   — activity streams (opt-in)
        messages/{activity_id}.json  — activity messages
        settings.json                — athlete settings (24h TTL)
        index.json                   — central lookup index

The 48-hour rule:
    Data older than 2 days is served from cache.
    Data from the last 48h (and all future events) is always re-fetched from API.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from app.api.intervals_client import IntervalsClient
from app.utils.alerts import notify_error

logger = logging.getLogger(__name__)


def _is_day_cache_stale(subdir: str, day: str) -> bool:
    """Return True if the cached day file is older than 48 hours (or missing)."""
    p = _CACHE_ROOT / subdir / f"{day}.json"
    if not p.exists():
        return True
    age_hours = (datetime.now().timestamp() - p.stat().st_mtime) / 3600
    return age_hours > 48

from app.utils.paths import CACHE_DIR as _CACHE_ROOT  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_boundary() -> str:
    """Date string 2 days ago — everything before this is cold (cached)."""
    return (date.today() - timedelta(days=2)).isoformat()


def _today() -> str:
    return date.today().isoformat()


# Keywords matched as whole words in activity name (lowercase)
_RACE_KEYWORDS = {
    "wettkampf", "rennen", "marathon", "halbmarathon", "10k", "5k", "triathlon",
    "duathlon", "swimrun", "race", "competition", "meisterschaft",
}
_TEST_KEYWORDS = {
    "leistungstest", "stufentest", "schwellentest", "ftp test", "ftp-test",
    "time trial", "zeitfahren", "inscyd", "cptest", "cp test",
}


def _is_special(activity: dict) -> str | None:
    """Return 'race', 'test', or None based on name keywords."""
    name = (activity.get("name") or "").lower()
    words = set(name.replace("-", " ").split())
    if words & _RACE_KEYWORDS or any(k in name for k in _RACE_KEYWORDS if " " in k):
        return "race"
    if any(k in name for k in _TEST_KEYWORDS):
        return "test"
    return None


def _activity_index_entry(activity: dict) -> dict:
    act_id = str(activity.get("id", ""))
    return {
        "id": act_id,
        "date": (activity.get("start_date_local") or "")[:10],
        "type": activity.get("type", ""),
        "tags": activity.get("tags") or [],
        "name": activity.get("name", ""),
        "moving_time": activity.get("moving_time"),
        "distance": activity.get("distance"),
        "icu_training_load": activity.get("icu_training_load"),
        "workout_type": activity.get("workout_type"),
        "has_streams": (Path(_CACHE_ROOT) / "streams" / f"{act_id}.json").exists(),
        "has_messages": (Path(_CACHE_ROOT) / "messages" / f"{act_id}.json").exists(),
    }


def _event_index_entry(event: dict) -> dict:
    return {
        "id": event.get("id"),
        "date": (event.get("start_date_local") or event.get("start_date") or "")[:10],
        "category": event.get("category", ""),
        "type": event.get("type", ""),
        "tags": event.get("tags") or [],
        "name": event.get("name", ""),
        "uid": event.get("uid", ""),
    }


def _note_index_entry(note: dict) -> dict:
    return {
        "id": note.get("id"),
        "date": (note.get("start_date_local") or note.get("start_date") or "")[:10],
        "name": note.get("name", ""),
    }


# ---------------------------------------------------------------------------
# IntervalsFileCache
# ---------------------------------------------------------------------------

class IntervalsFileCache:
    """File-based cache with a central index for fast lookups."""

    def __init__(self, athlete_id: str, cache_dir: Path | None = None) -> None:
        self._athlete_id = athlete_id
        self._root = (cache_dir or _CACHE_ROOT).resolve()
        self._index: dict | None = None  # lazy-loaded

    # --- Directory helpers --------------------------------------------------

    def _dir(self, subdir: str) -> Path:
        p = self._root / subdir
        p.mkdir(parents=True, exist_ok=True)
        return p

    # --- Index --------------------------------------------------------------

    def _index_path(self) -> Path:
        self._root.mkdir(parents=True, exist_ok=True)
        return self._root / "index.json"

    def load_index(self) -> dict:
        if self._index is not None:
            return self._index
        p = self._index_path()
        if p.exists():
            try:
                self._index = json.loads(p.read_text())
                return self._index
            except Exception:
                logger.warning("cache: index.json corrupt, resetting")
        self._index = {
            "_updated_at": "",
            "activities": [],
            "events": [],
            "notes": [],
            "special": [],
            "compound_events": [],
        }
        return self._index

    # --- Coverage watermark -------------------------------------------------
    #
    # A day-file is only written when a day actually HAS items, so "no file"
    # is ambiguous: it means either "fetched, nothing that day" or "never
    # fetched". Without a watermark the cold path silently reports the second
    # case as an empty day — any date that aged past the fresh boundary while
    # no session ran is then invisible forever (the multi-day-gap case:
    # holiday, illness, travel). The watermark records how far the API has
    # actually been queried per subdir so the gap can be re-fetched once.

    def coverage_through(self, subdir: str) -> str | None:
        return (self.load_index().get("_coverage") or {}).get(subdir)

    def set_coverage_through(self, subdir: str, day: str) -> None:
        idx = self.load_index()
        coverage = idx.setdefault("_coverage", {})
        if day > (coverage.get(subdir) or ""):
            coverage[subdir] = day

    def save_index(self) -> None:
        if self._index is None:
            return
        self._index["_updated_at"] = datetime.now().isoformat(timespec="seconds")
        try:
            self._index_path().write_text(json.dumps(self._index, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.warning("cache: could not save index: %s", e)

    def update_index_activities(self, activities: list[dict]) -> None:
        idx = self.load_index()
        existing_ids = {a["id"] for a in idx["activities"]}
        special_ids = {s["id"] for s in idx["special"]}
        for act in activities:
            act_id = str(act.get("id", ""))
            if not act_id:
                continue
            entry = _activity_index_entry(act)
            if act_id not in existing_ids:
                idx["activities"].append(entry)
                existing_ids.add(act_id)
            else:
                # Update existing entry
                for i, a in enumerate(idx["activities"]):
                    if a["id"] == act_id:
                        idx["activities"][i] = entry
                        break
            # Special check
            special_cat = _is_special(act)
            if special_cat and act_id not in special_ids:
                idx["special"].append({
                    "id": act_id,
                    "date": entry["date"],
                    "type": entry["type"],
                    "category": special_cat,
                    "name": entry["name"],
                    "distance": entry["distance"],
                    "moving_time": entry["moving_time"],
                })
                special_ids.add(act_id)
        # Keep sorted by date asc
        idx["activities"].sort(key=lambda a: a.get("date", ""))
        idx["special"].sort(key=lambda a: a.get("date", ""))
        # Re-detect compound events for affected days
        affected_dates = {str(act.get("start_date_local") or "")[:10] for act in activities if act.get("start_date_local")}
        if affected_dates:
            self.rebuild_compound_events()

    def update_index_events(self, events: list[dict], category: str = "WORKOUT") -> None:
        idx = self.load_index()
        key = "notes" if category == "NOTE" else "events"
        existing_ids = {str(e["id"]) for e in idx[key]}
        for ev in events:
            ev_id = str(ev.get("id", ""))
            if not ev_id or ev_id in existing_ids:
                continue
            entry = _note_index_entry(ev) if category == "NOTE" else _event_index_entry(ev)
            idx[key].append(entry)
            existing_ids.add(ev_id)
        idx[key].sort(key=lambda e: e.get("date", ""))

    def refresh_file_refs(self) -> None:
        """Update has_streams / has_messages flags in all index activity entries based on actual files."""
        idx = self.load_index()
        streams_dir = self._root / "streams"
        messages_dir = self._root / "messages"
        for entry in idx["activities"]:
            act_id = entry["id"]
            entry["has_streams"] = (streams_dir / f"{act_id}.json").exists()
            entry["has_messages"] = (messages_dir / f"{act_id}.json").exists()

    def rebuild_compound_events(self) -> None:
        """Detect and index all multi-sport days: races AND training bricks.

        Any day with 2+ different endurance sport types counts — because
        the second/third activity is always performed under accumulated fatigue,
        which is the critical context for performance analysis.

        Sequence order: Swim → Bike → Run (standard triathlon order).

        Category classification (with or without swim recorded):
          ironman          : Bike ≥ 150km  AND  Run ≥ 38km
          half_ironman     : Bike ≥ 70km   AND  Run ≥ 18km
          olympic_tri      : Bike ≥ 35km   AND  Run ≥ 9km   (± swim)
          sprint_tri       : Bike ≥ 15km   AND  Run ≥ 3km   (± swim)
          swim_bike        : Swim + Bike only (no run)
          swim_run         : Swim + Run only (no bike)
          brick_training   : any other Bike+Run combination
        """
        idx = self.load_index()
        from collections import defaultdict

        SWIM_TYPES = {"Swim", "OpenWaterSwim", "SwimPool"}
        BIKE_TYPES = {"Ride", "VirtualRide"}
        RUN_TYPES  = {"Run", "VirtualRun"}

        by_day: dict[str, list[dict]] = defaultdict(list)
        for a in idx["activities"]:
            if a.get("date"):
                by_day[a["date"]].append(a)

        def _classify(swim_km: float, bike_km: float, run_km: float) -> str:
            has_swim = swim_km >= 0.3
            has_bike = bike_km >= 5
            has_run  = run_km  >= 1
            # Full distance (with or without swim recorded)
            if bike_km >= 150 and run_km >= 38:
                return "ironman"
            if bike_km >= 70 and run_km >= 18:
                return "half_ironman"
            # Triathlon distances (swim optional — may not be recorded)
            if has_bike and has_run:
                if (has_swim or True) and bike_km >= 35 and run_km >= 9:
                    return "olympic_tri"
                if (has_swim or True) and bike_km >= 15 and run_km >= 3:
                    return "sprint_tri"
                return "brick_training"
            if has_swim and has_bike and not has_run:
                return "swim_bike"
            if has_swim and has_run and not has_bike:
                return "swim_run"
            return "brick_training"

        def _comp(type_acts: list[dict], dist_m: float) -> dict:
            return {
                "type": type_acts[0]["type"] if type_acts else "",
                "activity_ids": [a["id"] for a in type_acts],
                "distance_km": round(dist_m / 1000, 2),
                "time_min": sum((a.get("moving_time") or 0) for a in type_acts) // 60,
            }

        compound: list[dict] = []
        for day, acts in sorted(by_day.items()):
            swim_acts = [a for a in acts if a["type"] in SWIM_TYPES]
            bike_acts = [a for a in acts if a["type"] in BIKE_TYPES]
            run_acts  = [a for a in acts if a["type"] in RUN_TYPES]

            # Need at least 2 different endurance types
            sport_types_present = sum([bool(swim_acts), bool(bike_acts), bool(run_acts)])
            if sport_types_present < 2:
                continue

            swim_m = sum((a.get("distance") or 0) for a in swim_acts)
            bike_m = sum((a.get("distance") or 0) for a in bike_acts)
            run_m  = sum((a.get("distance") or 0) for a in run_acts)

            # Minimum meaningful effort: avoid tiny cool-down runs after bike
            if bike_acts and run_acts and run_m < 1000:
                continue
            if swim_acts and bike_acts and bike_m < 5000:
                continue

            all_acts = swim_acts + bike_acts + run_acts
            total_load = sum((a.get("icu_training_load") or 0) for a in all_acts)
            total_time = sum((a.get("moving_time") or 0) for a in all_acts)
            total_dist = swim_m + bike_m + run_m

            category = _classify(swim_m / 1000, bike_m / 1000, run_m / 1000)

            # Build components in Swim → Bike → Run order
            components: list[dict] = []
            if swim_acts:
                components.append(_comp(swim_acts, swim_m))
            if bike_acts:
                components.append(_comp(bike_acts, bike_m))
            if run_acts:
                components.append(_comp(run_acts, run_m))

            compound.append({
                "date": day,
                "category": category,
                "total_distance_km": round(total_dist / 1000, 1),
                "total_moving_time_min": total_time // 60,
                "total_load": round(total_load),
                "components": components,
            })

        idx["compound_events"] = compound
        logger.info("cache: detected %d compound events", len(compound))

    def remove_index_event(self, event_id: int | str) -> None:
        idx = self.load_index()
        eid = str(event_id)
        idx["events"] = [e for e in idx["events"] if str(e.get("id")) != eid]
        idx["notes"] = [n for n in idx["notes"] if str(n.get("id")) != eid]

    # --- Index queries -------------------------------------------------------

    def query_by_type(self, activity_type: str, limit: int = 30) -> list[dict]:
        idx = self.load_index()
        matches = [a for a in idx["activities"] if a.get("type") == activity_type]
        return matches[-limit:]

    def query_by_tags(self, tags: list[str], limit: int = 30) -> list[dict]:
        idx = self.load_index()
        tag_set = set(t.lower() for t in tags)
        matches = [a for a in idx["activities"] if tag_set & set(t.lower() for t in (a.get("tags") or []))]
        return matches[-limit:]

    def query_special(self, category: str | None = None) -> list[dict]:
        idx = self.load_index()
        if category:
            return [s for s in idx["special"] if s.get("category") == category]
        return list(idx["special"])

    def query_date_range(self, oldest: str, newest: str) -> list[dict]:
        idx = self.load_index()
        return [a for a in idx["activities"] if oldest <= a.get("date", "") <= newest]

    def cached_dates_in_range(self, subdir: str, oldest: str, newest: str) -> list[str]:
        """Return sorted list of dates with cached files in range."""
        d = self._root / subdir
        if not d.exists():
            return []
        dates = []
        for f in d.iterdir():
            if f.suffix == ".json":
                dt = f.stem
                if oldest <= dt <= newest:
                    dates.append(dt)
        return sorted(dates)

    # --- Day-level file I/O -------------------------------------------------

    def read_day(self, subdir: str, day: str) -> list[dict] | None:
        p = self._root / subdir / f"{day}.json"
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            logger.warning("cache: corrupt file %s, ignoring", p)
            p.unlink(missing_ok=True)
            return None

    def write_day(self, subdir: str, day: str, data: list[dict]) -> None:
        try:
            self._dir(subdir)
            p = self._root / subdir / f"{day}.json"
            p.write_text(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.warning("cache: could not write %s/%s: %s", subdir, day, e)

    # --- ID-level file I/O --------------------------------------------------

    def read_by_id(self, subdir: str, item_id: str) -> dict | list | None:
        p = self._root / subdir / f"{item_id}.json"
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            logger.warning("cache: corrupt file %s/%s, ignoring", subdir, item_id)
            p.unlink(missing_ok=True)
            return None

    def write_by_id(self, subdir: str, item_id: str, data: Any) -> None:
        try:
            self._dir(subdir)
            p = self._root / subdir / f"{item_id}.json"
            p.write_text(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.warning("cache: could not write %s/%s: %s", subdir, item_id, e)

    def delete_by_id(self, subdir: str, item_id: str) -> None:
        p = self._root / subdir / f"{item_id}.json"
        p.unlink(missing_ok=True)

    # --- Settings -----------------------------------------------------------

    def read_settings(self) -> dict | None:
        p = self._root / "settings.json"
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text())
            cached_at_str = data.get("_cached_at", "")
            if cached_at_str:
                cached_at = datetime.fromisoformat(cached_at_str)
                if datetime.now() - cached_at < timedelta(hours=24):
                    return data
            return None  # expired
        except Exception:
            return None

    def write_settings(self, data: dict) -> None:
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            payload = {**data, "_cached_at": datetime.now().isoformat(timespec="seconds")}
            (self._root / "settings.json").write_text(json.dumps(payload, ensure_ascii=False))
        except Exception as e:
            logger.warning("cache: could not write settings: %s", e)


# ---------------------------------------------------------------------------
# CachedIntervalsClient
# ---------------------------------------------------------------------------

class CachedIntervalsClient:
    """Drop-in wrapper for IntervalsClient with transparent file caching.

    - Data older than 48h → served from cache files
    - Data within 48h, future events, weather → always fresh from API
    - Write operations (post/delete) pass through and update the cache
    """

    def __init__(self, athlete_id: str | None = None, cache_dir: Path | None = None) -> None:
        self._client = IntervalsClient(athlete_id)
        self.athlete_id = self._client.athlete_id
        self._cache = IntervalsFileCache(self.athlete_id, cache_dir)

    # --- Range fetch helpers ------------------------------------------------

    def _load_cached_range(self, subdir: str, oldest: str, newest: str) -> list[dict]:
        """Load all cached day-files for dates in [oldest, newest]."""
        days = self._cache.cached_dates_in_range(subdir, oldest, newest)
        result: list[dict] = []
        for day in days:
            items = self._cache.read_day(subdir, day)
            if items:
                result.extend(items)
        return result

    def _save_day_grouped(self, subdir: str, items: list[dict], date_key: str = "start_date_local") -> None:
        """Group items by date and write one file per day."""
        by_day: dict[str, list[dict]] = {}
        for item in items:
            day = (item.get(date_key) or item.get("start_date") or "")[:10]
            if day:
                by_day.setdefault(day, []).append(item)
        for day, day_items in by_day.items():
            self._cache.write_day(subdir, day, day_items)

    @staticmethod
    def _merge_by_id(
        cached: list[dict],
        fresh: list[dict],
        id_key: str = "id",
        sort_key: Callable[[dict], str] | None = None,
    ) -> list[dict]:
        """Merge two lists, fresh wins on duplicate IDs, sorted chronologically.

        Default sort key is start_date_local/start_date (activities, events,
        notes). Wellness records carry their date in ``id`` and have no
        start_date field — without an explicit ``sort_key`` every wellness
        key would be "" and late-fetched gap days would land at the end of
        the list, corrupting consumers that slice ``[-7:]`` / ``[-90:]``.
        """
        merged: dict[str, dict] = {str(a[id_key]): a for a in cached if id_key in a}
        for a in fresh:
            if id_key in a:
                merged[str(a[id_key])] = a
        if sort_key is None:
            def sort_key(a: dict) -> str:
                return a.get("start_date_local") or a.get("start_date") or ""
        return sorted(merged.values(), key=sort_key)

    # --- Fetch-window helper ------------------------------------------------

    def _fetch_start(self, subdir: str, oldest: str, boundary: str) -> str:
        """First date the API must be queried for, gaps included.

        Normally the API is only asked for the hot range (``boundary``
        onwards) and everything older comes from day-files. But a stretch
        that aged past ``boundary`` while no session ran was never cached at
        all, and the cold path cannot tell that apart from a genuinely empty
        day. The coverage watermark closes that: whatever lies between the
        last covered day and the hot range is re-fetched once, after which
        the watermark moves up and the normal hot-only path resumes.
        """
        covered = self._cache.coverage_through(subdir)
        if covered is None:
            # Pre-watermark cache (or a fresh one): the extent of the gap is
            # unknown, so query the whole requested range once to self-heal.
            return oldest
        gap_start = (date.fromisoformat(covered) + timedelta(days=1)).isoformat()
        return max(oldest, min(boundary, gap_start))

    # --- Activities ---------------------------------------------------------

    async def get_activities(self, oldest: str, newest: str) -> list[dict]:
        boundary = _fresh_boundary()
        hot_start = self._fetch_start("activities", oldest, boundary)
        cold_end = min(hot_start, newest)

        cached: list[dict] = []
        if oldest < cold_end:
            cached = self._load_cached_range("activities", oldest, cold_end)

        fresh: list[dict] = []
        if hot_start <= newest:
            try:
                fresh = await self._client.get_activities(hot_start, newest)
                self._save_day_grouped("activities", fresh)
                self._cache.update_index_activities(fresh)
                self._cache.set_coverage_through("activities", min(newest, _today()))
                self._cache.save_index()
            except Exception as e:
                logger.warning("cache: activities API failed, using cache only: %s", e)
                if _is_day_cache_stale("activities", _today()):
                    notify_error("Cache stale + intervals.icu API down (activities)", {"error": str(e)})

        return self._merge_by_id(cached, fresh)

    # --- Events -------------------------------------------------------------

    async def get_events(self, oldest: str, newest: str) -> list[dict]:
        today = _today()
        boundary = _fresh_boundary()

        # Always fetch fresh: hot range (last 48h, gaps included) + future
        hot_start = self._fetch_start("events", oldest, boundary)

        cached: list[dict] = []
        cold_end = min(hot_start, newest, today)
        if oldest < cold_end:
            cached = self._load_cached_range("events", oldest, cold_end)

        fresh: list[dict] = []
        if hot_start <= newest:
            try:
                fresh = await self._client.get_events(hot_start, newest)
                # Cache only past events (not future)
                past_fresh = [e for e in fresh if (e.get("start_date_local") or e.get("start_date") or "")[:10] < boundary]
                if past_fresh:
                    self._save_day_grouped("events", past_fresh)
                    self._cache.update_index_events(past_fresh)
                self._cache.set_coverage_through("events", min(newest, today))
                self._cache.save_index()
            except Exception as e:
                logger.warning("cache: events API failed, using cache only: %s", e)
                if _is_day_cache_stale("events", _today()):
                    notify_error("Cache stale + intervals.icu API down (events)", {"error": str(e)})

        return self._merge_by_id(cached, fresh)

    # --- Notes --------------------------------------------------------------

    async def get_notes(self, oldest: str, newest: str) -> list[dict]:
        boundary = _fresh_boundary()
        hot_start = self._fetch_start("notes", oldest, boundary)
        cold_end = min(hot_start, newest)

        cached: list[dict] = []
        if oldest < cold_end:
            cached = self._load_cached_range("notes", oldest, cold_end)

        fresh: list[dict] = []
        if hot_start <= newest:
            try:
                fresh = await self._client.get_notes(hot_start, newest)
                past_fresh = [n for n in fresh if (n.get("start_date_local") or n.get("start_date") or "")[:10] < boundary]
                if past_fresh:
                    self._save_day_grouped("notes", past_fresh)
                    self._cache.update_index_events(past_fresh, category="NOTE")
                self._cache.set_coverage_through("notes", min(newest, _today()))
                self._cache.save_index()
            except Exception as e:
                logger.warning("cache: notes API failed, using cache only: %s", e)
                if _is_day_cache_stale("notes", _today()):
                    notify_error("Cache stale + intervals.icu API down (notes)", {"error": str(e)})

        return self._merge_by_id(cached, fresh)

    # --- Wellness (single day) ----------------------------------------------

    async def get_wellness(self, day: str) -> dict:
        if day < _today():
            cached = self._cache.read_day("wellness", day)
            if cached and isinstance(cached, list) and cached:
                return cached[0]
            elif isinstance(cached, dict):
                return cached
        try:
            data = await self._client.get_wellness(day)
            if day < _today():
                self._cache.write_day("wellness", day, [data])
            return data
        except Exception as e:
            logger.warning("cache: wellness API failed for %s: %s", day, e)
            if _is_day_cache_stale("wellness", day):
                notify_error("Cache stale + intervals.icu API down (wellness)", {"day": day, "error": str(e)})
            return {}

    # --- Wellness history ---------------------------------------------------

    async def get_wellness_history(self, oldest: str, newest: str) -> list[dict]:
        today = _today()
        # Collect cached daily records
        cached_days = self._cache.cached_dates_in_range("wellness", oldest, min(newest, today))
        cached: list[dict] = []
        for day in cached_days:
            items = self._cache.read_day("wellness", day)
            if items:
                if isinstance(items, list):
                    cached.extend(items)
                else:
                    cached.append(items)

        # Determine which days are missing
        all_days: set[str] = set()
        d = date.fromisoformat(oldest)
        end = date.fromisoformat(min(newest, today))
        while d <= end:
            all_days.add(d.isoformat())
            d += timedelta(days=1)
        cached_day_set = set(cached_days)
        missing = all_days - cached_day_set

        if missing or newest > today:
            # Fetch from API to fill gaps + today
            fetch_oldest = min(missing | {newest}) if missing else newest
            try:
                fresh = await self._client.get_wellness_history(fetch_oldest, newest)
                for record in fresh:
                    day = record.get("id", "")[:10]
                    if day and day < today:
                        self._cache.write_day("wellness", day, [record])
                # Wellness records carry their date in `id` — sort by it so
                # back-filled gap days land in chronological position.
                return self._merge_by_id(
                    cached, fresh, id_key="id",
                    sort_key=lambda r: r.get("id") or "",
                )
            except Exception as e:
                logger.warning("cache: wellness_history API failed: %s", e)
                if _is_day_cache_stale("wellness", _today()):
                    notify_error("Cache stale + intervals.icu API down (wellness_history)", {"error": str(e)})
                return cached

        return sorted(cached, key=lambda r: r.get("id", ""))

    # --- Athlete settings ---------------------------------------------------

    async def get_athlete_settings(self) -> dict:
        cached = self._cache.read_settings()
        if cached:
            return {k: v for k, v in cached.items() if not k.startswith("_")}
        try:
            data = await self._client.get_athlete_settings()
            self._cache.write_settings(data)
            return data
        except Exception as e:
            logger.warning("cache: athlete_settings API failed: %s", e)
            notify_error("intervals.icu athlete_settings API down", {"error": str(e)})
            return {}

    # --- Weather (never cached) ---------------------------------------------

    async def get_weather_forecast(self) -> dict:
        return await self._client.get_weather_forecast()

    # --- Single activity ----------------------------------------------------

    async def get_activity(self, activity_id: str) -> dict:
        cached = self._cache.read_by_id("activity_detail", activity_id)
        if cached and isinstance(cached, dict):
            act_date = (cached.get("start_date_local") or "")[:10]
            if act_date < _fresh_boundary():
                return cached
        try:
            data = await self._client.get_activity(activity_id)
            act_date = (data.get("start_date_local") or "")[:10]
            if act_date and act_date < _fresh_boundary():
                self._cache.write_by_id("activity_detail", activity_id, data)
            return data
        except Exception as e:
            if cached:
                logger.warning("cache: activity API failed, serving stale cache: %s", e)
                return cached  # type: ignore[return-value]
            raise

    # --- Activity messages --------------------------------------------------

    async def get_activity_messages(self, activity_id: str) -> list[dict]:
        # Check if activity is old enough to cache messages
        act_detail = self._cache.read_by_id("activity_detail", activity_id)
        act_date = (act_detail.get("start_date_local") or "")[:10] if isinstance(act_detail, dict) else ""

        if act_date and act_date < _fresh_boundary():
            cached = self._cache.read_by_id("messages", activity_id)
            if cached is not None and isinstance(cached, list):
                return cached

        try:
            data = await self._client.get_activity_messages(activity_id)
            if act_date and act_date < _fresh_boundary():
                self._cache.write_by_id("messages", activity_id, data)
                # Update has_messages flag in index
                idx = self._cache.load_index()
                for entry in idx["activities"]:
                    if entry["id"] == activity_id:
                        entry["has_messages"] = True
                        break
                self._cache.save_index()
            return data
        except Exception as e:
            logger.warning("cache: messages API failed for %s: %s", activity_id, e)
            return []

    # --- Streams (permanent cache) ------------------------------------------

    async def get_streams(
        self,
        activity_id: str,
        types: str = "time,heartrate,latlng,velocity_smooth,cadence,altitude,distance",
    ) -> dict[str, list]:
        cached = self._cache.read_by_id("streams", activity_id)
        if cached is not None and isinstance(cached, dict):
            return cached
        data = await self._client.get_streams(activity_id, types)
        self._cache.write_by_id("streams", activity_id, data)
        return data

    # --- Single event -------------------------------------------------------

    async def get_event(self, event_id: str) -> dict:
        cached = self._cache.read_by_id("event_detail", event_id)
        if cached and isinstance(cached, dict):
            ev_date = (cached.get("start_date_local") or cached.get("start_date") or "")[:10]
            today = _today()
            if ev_date and ev_date < _fresh_boundary() and ev_date <= today:
                return cached
        data = await self._client.get_event(event_id)
        ev_date = (data.get("start_date_local") or data.get("start_date") or "")[:10]
        if ev_date and ev_date < _fresh_boundary() and ev_date <= _today():
            self._cache.write_by_id("event_detail", event_id, data)
        return data

    async def get_today_workouts(self, day: str) -> list[dict]:
        return await self._client.get_today_workouts(day)

    # --- Write-through operations -------------------------------------------

    async def post_events_bulk(self, events: list[dict]) -> list[dict]:
        result = await self._client.post_events_bulk(events)
        # Cache past events returned by the API
        boundary = _fresh_boundary()
        past = [e for e in result if (e.get("start_date_local") or e.get("start_date") or "")[:10] < boundary]
        if past:
            self._save_day_grouped("events", past)
            self._cache.update_index_events(past)
            self._cache.save_index()
        return result

    async def post_activity_message(self, activity_id: str, content: str) -> dict:
        result = await self._client.post_activity_message(activity_id, content)
        # Invalidate cached messages so next read re-fetches
        self._cache.delete_by_id("messages", activity_id)
        return result

    async def delete_event(self, event_id: int) -> None:
        await self._client.delete_event(event_id)
        self._cache.delete_by_id("event_detail", str(event_id))
        self._cache.remove_index_event(event_id)
        self._cache.save_index()

    async def delete_activity_message(self, activity_id: str, message_id: int) -> None:
        await self._client.delete_activity_message(activity_id, message_id)
        self._cache.delete_by_id("messages", activity_id)
