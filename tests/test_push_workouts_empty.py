"""An empty workouts array must not hit `events/bulk` (HTTP 422).

Balance-only days push `[]` as the main program; the auto-balance rotation
afterwards is the actual push. `_push` has to return cleanly in that case.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import push_workouts as pw  # noqa: E402


class _ExplodingClient:
    """Any intervals.icu call fails the test — an empty push must do none."""

    def __init__(self, *a, **k):
        pass

    async def get_events(self, *a, **k):
        raise AssertionError("get_events called for an empty push")

    async def post_events_bulk(self, *a, **k):
        raise AssertionError("post_events_bulk called for an empty push")

    async def delete_event(self, *a, **k):
        raise AssertionError("delete_event called for an empty push")


def test_push_empty_events_skips_bulk_and_dedup(monkeypatch):
    monkeypatch.setattr(pw, "CachedIntervalsClient", _ExplodingClient)
    assert asyncio.run(pw._push("athlete1", [], False, "2026-11-18")) == []


def test_push_empty_events_dry_run(monkeypatch):
    monkeypatch.setattr(pw, "CachedIntervalsClient", _ExplodingClient)
    assert asyncio.run(pw._push("athlete1", [], True, "2026-11-18")) == []


def test_push_nonempty_still_posts(monkeypatch):
    posted: list = []

    class _Client(_ExplodingClient):
        async def get_events(self, *a, **k):
            return []

        async def post_events_bulk(self, events):
            posted.extend(events)
            return [{"uid": e["uid"]} for e in events]

    monkeypatch.setattr(pw, "CachedIntervalsClient", _Client)
    ev = [{"uid": "u1", "type": "Workout", "name": "x"}]
    assert asyncio.run(pw._push("athlete1", ev, False, "2026-11-18")) == [{"uid": "u1"}]
    assert posted == ev
