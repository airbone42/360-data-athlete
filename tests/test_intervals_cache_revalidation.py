"""Cold cache entries follow upstream changes (coach audit 2026-11-08).

Before: activity day-files older than 48 h and every stream file were cached
forever, so an activity re-tagged, re-analysed or deleted after two days kept
its first snapshot. Now cold days are re-checked once per REVALIDATE_HOURS
and streams / details carry the activity's change marker
(``analyzed`` | ``icu_sync_date``).

Synthetic fixtures use 2025 dates (public-repo athlete-agnostic rule).
"""
from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from app.api import intervals_cache

TODAY = date(2025, 6, 30)
OLDEST = (TODAY - timedelta(days=28)).isoformat()
COLD_DAY = TODAY - timedelta(days=10)


class _Stub:
    def __init__(self) -> None:
        self.athlete_id = "i0"
        self.activities: list[dict] = []
        self.calls: list[tuple[str, str]] = []
        self.stream_calls = 0
        self.detail_calls = 0

    async def get_activities(self, oldest: str, newest: str) -> list[dict]:
        self.calls.append((oldest, newest))
        return [dict(a) for a in self.activities
                if oldest <= a["start_date_local"][:10] <= newest]

    async def get_streams(self, activity_id: str, types: str) -> dict:
        self.stream_calls += 1
        return {"time": [0, 1], "heartrate": [100 + self.stream_calls, 120]}

    async def get_activity(self, activity_id: str) -> dict:
        self.detail_calls += 1
        return next(dict(a) for a in self.activities if a["id"] == activity_id)


def _act(act_id: str, day: date, *, analyzed: str = "2025-06-20T10:00:00", **extra) -> dict:
    return {"id": act_id, "start_date_local": f"{day.isoformat()}T07:00:00",
            "type": "Run", "name": f"run-{act_id}", "tags": ["run"],
            "analyzed": analyzed, **extra}


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(intervals_cache, "_today", lambda: TODAY.isoformat())
    monkeypatch.setattr(intervals_cache, "_fresh_boundary",
                        lambda: (TODAY - timedelta(days=2)).isoformat())
    c = intervals_cache.CachedIntervalsClient.__new__(intervals_cache.CachedIntervalsClient)
    stub = _Stub()
    c._client = stub
    c.athlete_id = "i0"
    c._cache = intervals_cache.IntervalsFileCache("i0", tmp_path)
    return c, stub, tmp_path


def _age_revalidation(c, hours: float) -> None:
    mark = c._cache.load_index()["_revalidated"]["activities"]
    mark["at"] = (datetime.now() - timedelta(hours=hours)).isoformat(timespec="seconds")


def _get(c) -> list[dict]:
    return asyncio.run(c.get_activities(OLDEST, TODAY.isoformat()))


def test_cold_day_is_served_from_cache_within_the_revalidation_window(env) -> None:
    c, stub, _ = env
    stub.activities = [_act("a1", COLD_DAY)]
    _get(c)  # first call fetches the full range and marks it revalidated
    stub.activities = [_act("a1", COLD_DAY, tags=["run", "intervals"])]
    result = _get(c)
    assert stub.calls[-1][0] == (TODAY - timedelta(days=2)).isoformat()
    assert result[0]["tags"] == ["run"]  # still the snapshot — window not over


def test_changed_cold_activity_is_reloaded_after_the_window(env) -> None:
    c, stub, root = env
    stub.activities = [_act("a1", COLD_DAY)]
    _get(c)
    stub.activities = [_act("a1", COLD_DAY, tags=["run", "intervals"],
                            analyzed="2025-06-29T09:00:00")]
    _age_revalidation(c, intervals_cache.REVALIDATE_HOURS + 1)
    result = _get(c)
    assert stub.calls[-1][0] == OLDEST
    assert result[0]["tags"] == ["run", "intervals"]
    day_file = json.loads((root / "activities" / f"{COLD_DAY.isoformat()}.json").read_text())
    assert day_file[0]["tags"] == ["run", "intervals"]
    assert c._cache.activity_version("a1").startswith("2025-06-29")


def test_wider_range_than_last_check_revalidates(env) -> None:
    c, stub, _ = env
    stub.activities = [_act("a1", COLD_DAY)]
    asyncio.run(c.get_activities((TODAY - timedelta(days=14)).isoformat(), TODAY.isoformat()))
    _get(c)  # 28 days > 14 days checked
    assert stub.calls[-1][0] == OLDEST


def test_deleted_cold_activity_disappears(env) -> None:
    c, stub, root = env
    stub.activities = [_act("a1", COLD_DAY)]
    _get(c)
    stub.activities = []
    _age_revalidation(c, intervals_cache.REVALIDATE_HOURS + 1)
    assert _get(c) == []
    assert not (root / "activities" / f"{COLD_DAY.isoformat()}.json").exists()


def test_streams_follow_the_activity_version(env) -> None:
    c, stub, _ = env
    stub.activities = [_act("a1", COLD_DAY)]
    _get(c)
    first = asyncio.run(c.get_streams("a1"))
    again = asyncio.run(c.get_streams("a1"))
    assert stub.stream_calls == 1 and again == first
    assert not any(k.startswith("_meta_") for k in again)

    # Re-sync upstream → new change marker → streams are fetched again.
    stub.activities = [_act("a1", COLD_DAY, icu_sync_date="2025-06-29T12:00:00")]
    _age_revalidation(c, intervals_cache.REVALIDATE_HOURS + 1)
    _get(c)
    fresh = asyncio.run(c.get_streams("a1"))
    assert stub.stream_calls == 2 and fresh != first


def test_legacy_stream_cache_without_version_is_refetched_once(env) -> None:
    c, stub, _ = env
    stub.activities = [_act("a1", COLD_DAY)]
    _get(c)
    c._cache.write_by_id("streams", "a1", {
        "time": [0], "heartrate": [99],
        "_meta_requested_types": "time,heartrate,latlng,velocity_smooth,cadence,"
                                 "altitude,distance,watts,torque,temp",
    })
    asyncio.run(c.get_streams("a1"))
    asyncio.run(c.get_streams("a1"))
    assert stub.stream_calls == 1


def test_activity_detail_is_refetched_when_version_changes(env) -> None:
    c, stub, _ = env
    stub.activities = [_act("a1", COLD_DAY)]
    _get(c)
    asyncio.run(c.get_activity("a1"))
    asyncio.run(c.get_activity("a1"))
    assert stub.detail_calls == 1

    stub.activities = [_act("a1", COLD_DAY, analyzed="2025-06-29T09:00:00", name="renamed")]
    _age_revalidation(c, intervals_cache.REVALIDATE_HOURS + 1)
    _get(c)
    detail = asyncio.run(c.get_activity("a1"))
    assert stub.detail_calls == 2 and detail["name"] == "renamed"


def test_unknown_version_keeps_the_old_permanent_cache(env) -> None:
    """Activities without analyzed / icu_sync_date behave as before."""
    c, stub, _ = env
    stub.activities = [{"id": "a1", "start_date_local": f"{COLD_DAY}T07:00:00", "type": "Run"}]
    _get(c)
    asyncio.run(c.get_streams("a1"))
    asyncio.run(c.get_streams("a1"))
    assert stub.stream_calls == 1
