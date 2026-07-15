"""Regression tests for push_workouts._dedup_existing_events.

The dedup sweep must partition its match key on balance-ness so the daily
balance auto-push (a separate call, type="Workout") does not delete the
freshly-created main sessions on a ninja/mobility day (also type="Workout"),
and vice versa — while still replacing same-type events within each partition
on a full re-push.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import push_workouts as pw  # noqa: E402


class _StubClient:
    """Minimal async stub of IntervalsClient recording deletions."""

    def __init__(self, existing):
        self._existing = existing
        self.deleted: list[int] = []

    async def get_events(self, start, end):
        return self._existing

    async def delete_event(self, event_id):
        self.deleted.append(event_id)


def _events(existing, monkeypatch):
    stub = _StubClient(existing)
    monkeypatch.setattr(pw, "IntervalsClient", lambda athlete_id=None: stub)
    # backup writes to disk — no-op it for the unit test
    monkeypatch.setattr(pw, "backup_events_before_delete", lambda *a, **k: 0)
    return stub


_NINJA = {"id": 1, "category": "WORKOUT", "type": "Workout", "tags": ["ninja", "grip"]}
_LWS = {"id": 2, "category": "WORKOUT", "type": "Workout", "tags": ["mobility"]}
_BALANCE = {"id": 3, "category": "WORKOUT", "type": "Workout", "tags": ["balance"]}


async def test_balance_push_does_not_delete_workout_type_mains(monkeypatch):
    stub = _events([_NINJA, _LWS, _BALANCE], monkeypatch)
    # Auto-balance pushes a single balance-tagged Workout.
    n = await pw._dedup_existing_events("i1", "2026-07-15", [{"type": "Workout", "tags": ["balance"]}])
    assert stub.deleted == [3]  # only the existing balance event
    assert n == 1


async def test_main_push_does_not_delete_balance(monkeypatch):
    stub = _events([_NINJA, _LWS, _BALANCE], monkeypatch)
    # Main push: two non-balance Workout-type sessions.
    await pw._dedup_existing_events(
        "i1", "2026-07-15",
        [{"type": "Workout", "tags": ["ninja", "grip"]}, {"type": "Workout", "tags": ["mobility"]}],
    )
    assert sorted(stub.deleted) == [1, 2]  # mains replaced, balance (3) untouched


async def test_combined_push_replaces_both_partitions(monkeypatch):
    stub = _events([_NINJA, _LWS, _BALANCE], monkeypatch)
    await pw._dedup_existing_events(
        "i1", "2026-07-15",
        [
            {"type": "Workout", "tags": ["ninja"]},
            {"type": "Workout", "tags": ["mobility"]},
            {"type": "Workout", "tags": ["balance"]},
        ],
    )
    assert sorted(stub.deleted) == [1, 2, 3]


async def test_renamed_main_still_replaced_within_partition(monkeypatch):
    # Existing non-balance Workout under an old name; re-push under a new name.
    old = {"id": 9, "category": "WORKOUT", "type": "Workout", "tags": ["ninja"], "name": "Alt-Name"}
    stub = _events([old, _BALANCE], monkeypatch)
    await pw._dedup_existing_events("i1", "2026-07-15", [{"type": "Workout", "tags": ["ninja"], "name": "Neu-Name"}])
    assert stub.deleted == [9]  # renamed main replaced; balance untouched


async def test_paired_activity_never_deleted(monkeypatch):
    done = {"id": 7, "category": "WORKOUT", "type": "Workout", "tags": ["balance"], "paired_activity_id": 555}
    stub = _events([done], monkeypatch)
    await pw._dedup_existing_events("i1", "2026-07-15", [{"type": "Workout", "tags": ["balance"]}])
    assert stub.deleted == []  # completed/paired event is protected
