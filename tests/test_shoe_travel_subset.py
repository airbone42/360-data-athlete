"""Tests for the travel/vacation shoe-subset mechanism in shoe_advisor.

All fixtures are synthetic (made-up gear ids / dates), never real athlete
data — the travel window and gear ids below are invented for the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.graphs import shoe_advisor
from app.graphs.shoe_advisor import (
    build_shoe_context,
    load_shoe_profiles,
    load_travel_subset,
)

_EQUIP_MD = """# Equipment

## Laufschuhe

- icu_gear_id: g111
  name: "Demo Easy Trainer"
  type: easy
  role: daily
  terrain: asphalt
  threshold_km: 800
  recommended_tags: [easy, long]

- icu_gear_id: g222
  name: "Demo Race Shoe"
  type: tempo
  role: race
  terrain: asphalt
  threshold_km: 500
  recommended_tags: [race, intervals]

- icu_gear_id: g333
  name: "Demo Home Trainer"
  type: easy
  role: daily
  terrain: asphalt
  threshold_km: 800
  recommended_tags: [easy, long]

## Reise-Schuh-Subset

Nur die mitgenommenen Schuhe sind verfügbar bis zum Datum unten.

travel_subset_until: 2025-08-31
travel_subset_gear:
  - g111   # Demo Easy Trainer
  - g222   # Demo Race Shoe
"""


@pytest.fixture()
def equip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    p = tmp_path / "equipment.md"
    p.write_text(_EQUIP_MD, encoding="utf-8")
    monkeypatch.setattr(shoe_advisor, "_equipment_md_path", lambda: p)
    return p


def _shoes() -> list[dict]:
    return [
        {"gear_key": "g111", "name": "Demo Easy Trainer", "distance_km": 120},
        {"gear_key": "g222", "name": "Demo Race Shoe", "distance_km": 60},
        {"gear_key": "g333", "name": "Demo Home Trainer", "distance_km": 400},
    ]


def _fleet_names(today: str) -> list[str]:
    ctx = build_shoe_context(
        shoes=[dict(s) for s in _shoes()],
        profiles=load_shoe_profiles(),
        activities=[],
        planned_workouts=[{"type": "Run", "tags": ["run"], "intensity": "Z2"}],
        weather_info="",
        race_in_days=None,
        today_str=today,
        backend="intervals",
    )
    return [s.get("name") for s in ctx.get("shoes", [])]


def test_travel_subset_parses(equip: Path) -> None:
    ts = load_travel_subset()
    assert ts == {"until": "2025-08-31", "gear_ids": {"g111", "g222"}}


def test_home_shoe_excluded_inside_window(equip: Path) -> None:
    names = _fleet_names("2025-08-15")  # inside window
    assert "Demo Home Trainer" not in names
    assert set(names) == {"Demo Easy Trainer", "Demo Race Shoe"}


def test_full_fleet_after_window_expires(equip: Path) -> None:
    names = _fleet_names("2025-09-15")  # after until → auto-expired
    assert "Demo Home Trainer" in names
    assert len(names) == 3


def test_no_block_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "equipment.md"
    p.write_text("# Equipment\n\n## Laufschuhe\n\n- icu_gear_id: g111\n  name: \"X\"\n", encoding="utf-8")
    monkeypatch.setattr(shoe_advisor, "_equipment_md_path", lambda: p)
    assert load_travel_subset() is None


def test_empty_match_ignored_not_zeroed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A subset that matches no active shoe (typo'd ids) must be ignored,
    # never zero out the recommendation.
    md = _EQUIP_MD.replace("g111", "g999").replace("g222", "g998")
    p = tmp_path / "equipment.md"
    p.write_text(md, encoding="utf-8")
    monkeypatch.setattr(shoe_advisor, "_equipment_md_path", lambda: p)
    names = _fleet_names("2025-08-15")
    # profiles now reference g999/g998 for two shoes; the third (g333) stays.
    # The subset gear (g999/g998) matches no *active shoe* object (our shoe
    # objects are g111/g222/g333) → subset ignored, full fleet kept.
    assert "Demo Home Trainer" in names
