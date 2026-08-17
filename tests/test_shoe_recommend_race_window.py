"""Regression test — push-time shoe advisor must know the race distance.

`shoe_recommend.recommend()` historically passed a hardcoded
``race_in_days=None`` to `build_shoe_context`, which made `_score_shoe`'s
race-day lock disqualify the designated race shoe on every push except
RACE-typed workouts — race-pace habituation sessions inside the prep
window got a daily trainer recommended instead. The fix derives
``race_in_days`` from upcoming RACE_A/B/C calendar events using the same
helper as fetch_context's ``raceInDays``.

All fixtures are synthetic (invented gear ids, no real athlete data).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import shoe_recommend  # noqa: E402


class _FakeClient:
    """Stub for IntervalsClient covering the calls recommend() makes."""

    def __init__(self) -> None:
        self.events_query: tuple[str, str] | None = None

    async def list_gear(self) -> list[dict]:
        return [
            {"id": "gRACE1", "name": "Race Day Shoe", "type": "Shoes", "distance": 50_000},
            {"id": "gDAILY1", "name": "Fresh Daily Trainer", "type": "Shoes", "distance": 50_000},
        ]

    async def get_activities(self, oldest: str, newest: str) -> list[dict]:
        return []

    async def get_events(self, oldest: str, newest: str) -> list[dict]:
        self.events_query = (oldest, newest)
        return [
            {"category": "RACE_A", "start_date_local": "2025-03-28T09:00:00"},
            {"category": "NOTE", "start_date_local": "2025-03-16T09:00:00"},
        ]


@pytest.fixture()
def _profiles(monkeypatch):
    profiles = [
        {
            "icu_gear_id": "gRACE1",
            "name": "Race Day Shoe",
            "role": "race",
            "primary_race": True,
            "race_prep_days": 21,
            "terrain": "asphalt",
            "threshold_km": 400.0,
            "recommended_tags": ["race", "intervals"],
        },
        {
            "icu_gear_id": "gDAILY1",
            "name": "Fresh Daily Trainer",
            "role": "daily",
            "terrain": "asphalt",
            "threshold_km": 500.0,
            "recommended_tags": ["intervals", "tempo"],
        },
    ]
    monkeypatch.setattr(shoe_recommend, "load_shoe_profiles", lambda: profiles)
    monkeypatch.setattr(shoe_recommend, "load_travel_subset", lambda: None, raising=False)
    return profiles


def test_recommend_derives_race_window_and_picks_race_shoe(monkeypatch, _profiles):
    fake = _FakeClient()
    monkeypatch.setattr(shoe_recommend, "IntervalsClient", lambda: fake)

    workouts = [
        {
            "type": "Run",
            "workout_type": "INTERVALS",
            "intensity": "high",
            "tags": ["run", "intervals"],
            "surface": "forest-path",
        }
    ]
    # 2025-03-15 → race on 2025-03-28 = 13 days out, inside race_prep_days=21.
    ctx = asyncio.run(shoe_recommend.recommend(workouts, "", "2025-03-15"))

    assert fake.events_query is not None, "recommend() must scan upcoming events"
    primary = (ctx.get("shoeRecommendation") or {}).get("primary") or {}
    assert primary.get("gear_id") == "gRACE1", (
        "race shoe must win a race-pace slot inside its prep window, got "
        f"{primary.get('name')!r}"
    )


def test_set_activity_gear_fallback_derives_race_window(monkeypatch, _profiles):
    """The analysis-time fallback pick (unpaired activity) must apply the
    same race-window logic as the push path — it previously hardcoded
    race_in_days=None and assigned a daily trainer to a race-pace run."""
    import set_activity_gear

    monkeypatch.setattr(set_activity_gear, "load_shoe_profiles", lambda: _profiles)
    fake = _FakeClient()

    activity = {
        "type": "Run",
        "start_date_local": "2025-03-15T10:00:00",
        "tags": ["run", "intervals"],
    }
    plan = {
        "surface": "forest-path",
        "tags": ["run", "intervals"],
        "workout_type": "INTERVALS",
        "intensity": "high",
        "description": "",
    }
    gear_list = asyncio.run(fake.list_gear())
    rec = asyncio.run(
        set_activity_gear._recommend_gear_for_activity(fake, activity, plan, gear_list)
    )
    assert rec is not None
    assert rec.get("gear_id") == "gRACE1"


def test_recommend_survives_events_fetch_failure(monkeypatch, _profiles):
    fake = _FakeClient()

    async def _boom(oldest: str, newest: str) -> list[dict]:
        raise RuntimeError("events endpoint down")

    fake.get_events = _boom  # type: ignore[method-assign]
    monkeypatch.setattr(shoe_recommend, "IntervalsClient", lambda: fake)

    workouts = [{"type": "Run", "workout_type": "INTERVALS", "tags": ["run"]}]
    ctx = asyncio.run(shoe_recommend.recommend(workouts, "", "2025-03-15"))

    # Degrades to race_in_days=None: no crash, a recommendation still exists
    # (the race shoe is locked out again, as before the fix).
    primary = (ctx.get("shoeRecommendation") or {}).get("primary") or {}
    assert primary.get("gear_id") == "gDAILY1"
