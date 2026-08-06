"""Write-through day-cache consistency for events/NOTEs (P4-5 bug anchor).

post_message wrote NOTEs only to the API; for cold dates (>48h)
fetch_context reads NOTEs exclusively from the notes/ day files — a
HRV-Review marker NOTE written to a cold date was invisible to
_find_pending_hrv_review, so hrvReviewPending re-fired the same review
daily. The write-through now merges written events into the right
day file (category-aware: NOTE → notes/, else events/), update_event
refreshes it, delete_event cleans it. Synthetic 2025 dates.
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.api import intervals_cache
from app.api.intervals_cache import CachedIntervalsClient


TODAY = date(2025, 6, 30)
COLD = "2025-06-20"  # well past the 48h boundary


class _StubClient:
    def __init__(self) -> None:
        self.athlete_id = "i0"
        self.get_notes_calls: list[tuple[str, str]] = []
        self.deleted: list[int] = []

    async def post_events_bulk(self, events):
        return [
            {**e, "id": 100 + i, "category": e.get("category", "NOTE")}
            for i, e in enumerate(events)
        ]

    async def update_event(self, event_id, payload):
        return {"id": event_id, **payload}

    async def delete_event(self, event_id):
        self.deleted.append(event_id)

    async def get_notes(self, oldest, newest):
        self.get_notes_calls.append((oldest, newest))
        return []


@pytest.fixture()
def cached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(intervals_cache, "_today", lambda: TODAY.isoformat())
    monkeypatch.setattr(
        intervals_cache, "_fresh_boundary",
        lambda: (TODAY - timedelta(days=2)).isoformat(),
    )
    c = CachedIntervalsClient.__new__(CachedIntervalsClient)
    c._client = _StubClient()
    c.athlete_id = "i0"
    c._cache = intervals_cache.IntervalsFileCache("i0", tmp_path)
    # steady-state: coverage watermark at today (normal daily operation)
    c._cache.set_coverage_through("notes", TODAY.isoformat())
    c._cache.save_index()
    return c


def _note(day: str, name: str = "HRV-Review") -> dict:
    return {
        "category": "NOTE",
        "start_date_local": f"{day}T00:00:00",
        "name": name,
        "description": f"{name} {day}: alles erklärt",
    }


def test_cold_note_lands_in_notes_day_file_and_is_readable(cached):
    """The exact regression: NOTE posted to a cold date must be visible to
    the cold read path (day files), not buried in events/."""
    asyncio.run(cached.post_events_bulk([_note(COLD)]))

    day_file = cached._cache.read_day("notes", COLD)
    assert day_file and day_file[0]["name"] == "HRV-Review"
    assert cached._cache.read_day("events", COLD) in (None, [])

    notes = asyncio.run(cached.get_notes(COLD, COLD))
    assert [n["name"] for n in notes] == ["HRV-Review"]
    # cold range with coverage at today → no API fetch happened
    assert cached._client.get_notes_calls == []


def test_workout_event_still_goes_to_events_day_file(cached):
    ev = {
        "category": "WORKOUT",
        "start_date_local": f"{COLD}T06:00:00",
        "name": "Run",
    }
    asyncio.run(cached.post_events_bulk([ev]))
    assert cached._cache.read_day("events", COLD)[0]["name"] == "Run"
    assert cached._cache.read_day("notes", COLD) in (None, [])


def test_merge_keeps_existing_day_content(cached):
    cached._cache.write_day("notes", COLD, [{"id": 1, "name": "Athleten-Feedback",
                                            "start_date_local": f"{COLD}T00:00:00"}])
    asyncio.run(cached.post_events_bulk([_note(COLD)]))
    names = sorted(n["name"] for n in cached._cache.read_day("notes", COLD))
    assert names == ["Athleten-Feedback", "HRV-Review"]


def test_update_event_refreshes_day_file(cached):
    created = asyncio.run(cached.post_events_bulk([_note(COLD)]))
    eid = created[0]["id"]
    asyncio.run(cached.update_event(eid, {
        "category": "NOTE",
        "start_date_local": f"{COLD}T00:00:00",
        "name": "HRV-Review",
        "description": "HRV-Review aktualisiert",
    }))
    day = cached._cache.read_day("notes", COLD)
    assert [n["description"] for n in day if n["id"] == eid] == ["HRV-Review aktualisiert"]


def test_delete_event_removes_from_day_file(cached):
    created = asyncio.run(cached.post_events_bulk([_note(COLD)]))
    eid = created[0]["id"]
    assert cached._cache.read_day("notes", COLD)
    asyncio.run(cached.delete_event(eid))
    assert cached._client.deleted == [eid]
    assert all(str(n.get("id")) != str(eid) for n in (cached._cache.read_day("notes", COLD) or []))


def test_future_events_not_day_cached(cached):
    future = (TODAY + timedelta(days=2)).isoformat()
    asyncio.run(cached.post_events_bulk([{
        "category": "WORKOUT", "start_date_local": f"{future}T06:00:00", "name": "Plan",
    }]))
    assert cached._cache.read_day("events", future) in (None, [])
