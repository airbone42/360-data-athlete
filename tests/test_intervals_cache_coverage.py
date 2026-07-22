"""Tests for the activity/event/note cache coverage watermark.

A day-file is only written when a day actually has items, so "no file on
disk" is ambiguous — it means either "fetched, nothing happened that day" or
"never fetched at all". Before the watermark the cold path read the second
case as an empty day, which made any date that aged past the 48h fresh
boundary while no session ran permanently invisible (holiday / illness /
travel gaps). These tests pin the re-fetch behaviour.

Synthetic fixtures use 2025 dates (public-repo athlete-agnostic rule).
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.api import intervals_cache
from app.api.intervals_cache import CachedIntervalsClient


TODAY = date(2025, 6, 30)


class _StubClient:
    """Records the ranges it was asked for and replays canned activities."""

    def __init__(self, activities: list[dict] | None = None) -> None:
        self.athlete_id = "i0"
        self.calls: list[tuple[str, str]] = []
        self._activities = activities or []

    async def get_activities(self, oldest: str, newest: str) -> list[dict]:
        self.calls.append((oldest, newest))
        return [
            a for a in self._activities
            if oldest <= a["start_date_local"][:10] <= newest
        ]


def _activity(day: date, act_id: str) -> dict:
    return {
        "id": act_id,
        "start_date_local": f"{day.isoformat()}T07:00:00",
        "type": "Run",
        "name": f"run-{act_id}",
    }


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """CachedIntervalsClient on a throwaway cache dir with a pinned clock."""
    monkeypatch.setattr(intervals_cache, "_today", lambda: TODAY.isoformat())
    monkeypatch.setattr(
        intervals_cache,
        "_fresh_boundary",
        lambda: (TODAY - timedelta(days=2)).isoformat(),
    )

    def _build(activities: list[dict]) -> tuple[CachedIntervalsClient, _StubClient]:
        c = CachedIntervalsClient.__new__(CachedIntervalsClient)
        stub = _StubClient(activities)
        c._client = stub
        c.athlete_id = "i0"
        c._cache = intervals_cache.IntervalsFileCache("i0", tmp_path)
        return c, stub

    return _build


def test_cold_gap_is_refetched_and_watermark_advances(client) -> None:
    oldest = (TODAY - timedelta(days=28)).isoformat()
    gap_day = TODAY - timedelta(days=7)  # cold, never cached
    acts = [_activity(gap_day, "a1")]

    c, stub = client(acts)

    # First call: no watermark → the whole requested range is queried once,
    # which is what heals a pre-existing gap.
    first = asyncio.run(c.get_activities(oldest, TODAY.isoformat()))
    assert [a["id"] for a in first] == ["a1"]
    assert stub.calls[0] == (oldest, TODAY.isoformat())

    # Watermark now covers through today, so the next call only asks for the
    # hot range — but the cold day still comes back, from cache.
    second = asyncio.run(c.get_activities(oldest, TODAY.isoformat()))
    assert [a["id"] for a in second] == ["a1"]
    assert stub.calls[1] == ((TODAY - timedelta(days=2)).isoformat(), TODAY.isoformat())


def test_gap_after_stale_watermark_is_closed(client) -> None:
    oldest = (TODAY - timedelta(days=28)).isoformat()
    stale = TODAY - timedelta(days=10)
    gap_day = TODAY - timedelta(days=6)  # inside the never-fetched stretch
    acts = [_activity(gap_day, "a2")]

    c, stub = client(acts)
    c._cache.set_coverage_through("activities", stale.isoformat())
    c._cache.save_index()

    result = asyncio.run(c.get_activities(oldest, TODAY.isoformat()))

    # The query starts the day after the watermark, not at the fresh
    # boundary — otherwise the 10..2-days-ago stretch stays invisible.
    assert stub.calls[0][0] == (stale + timedelta(days=1)).isoformat()
    assert [a["id"] for a in result] == ["a2"]


def test_watermark_never_moves_backwards(client) -> None:
    c, _ = client([])
    c._cache.set_coverage_through("activities", TODAY.isoformat())
    c._cache.set_coverage_through("activities", (TODAY - timedelta(days=5)).isoformat())
    assert c._cache.coverage_through("activities") == TODAY.isoformat()


def test_coverage_is_tracked_per_subdir(client) -> None:
    c, _ = client([])
    c._cache.set_coverage_through("activities", TODAY.isoformat())
    assert c._cache.coverage_through("events") is None
    assert c._cache.coverage_through("notes") is None
