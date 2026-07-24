"""Tests for the rotation ranking in shoe_advisor.

All fixtures are synthetic (made-up gear ids / dates), never real athlete
data. Regression guard for the rotation-score quirk where a shoe rested longer
than the activity look-back window (last_used absent) was awarded a flat bonus
that ranked *below* a shoe worn a few days ago (in window), inverting the
"reward longest rest" intent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.graphs import shoe_advisor
from app.graphs.shoe_advisor import build_shoe_context, load_shoe_profiles

# Two easy asphalt dailies with identical mileage → only rotation differs.
_EQUIP_MD = """# Equipment

## Laufschuhe

- icu_gear_id: gIDLE
  name: "Idle Trainer"
  type: easy
  role: daily
  terrain: asphalt
  threshold_km: 800
  recommended_tags: [easy, recovery]

- icu_gear_id: gRECENT
  name: "Recent Trainer"
  type: easy
  role: daily
  terrain: asphalt
  threshold_km: 800
  recommended_tags: [easy, recovery]
"""

# Tie-break fleet: two long-idle shoes, different mileage.
_EQUIP_MD_TIE = """# Equipment

## Laufschuhe

- icu_gear_id: gFRESH
  name: "Fresh Trainer"
  type: easy
  role: daily
  terrain: asphalt
  threshold_km: 800
  recommended_tags: [easy, recovery]

- icu_gear_id: gWORN
  name: "Worn Trainer"
  type: easy
  role: daily
  terrain: asphalt
  threshold_km: 800
  recommended_tags: [easy, recovery]
"""


@pytest.fixture()
def _isolate_shoe_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure the local recommendation log never fills in a last_used value.
    monkeypatch.setattr(shoe_advisor, "_SHOE_LOG", tmp_path / "no_shoe_log.json")


def _equip(md: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "equipment.md"
    p.write_text(md, encoding="utf-8")
    monkeypatch.setattr(shoe_advisor, "_equipment_md_path", lambda: p)


_RUN = {"type": "Run", "tags": ["run"], "workout_type": "EASY", "surface": "asphalt"}


def test_long_idle_shoe_outranks_recently_worn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _isolate_shoe_log: None
) -> None:
    """A shoe not seen in the window must beat one worn ~12 days ago."""
    _equip(_EQUIP_MD, tmp_path, monkeypatch)
    today = "2025-08-15"
    shoes = [
        {"gear_key": "gIDLE", "name": "Idle Trainer", "distance_km": 300},
        {"gear_key": "gRECENT", "name": "Recent Trainer", "distance_km": 300},
    ]
    # Only the recent shoe appears in the activity window (worn 12 days ago).
    activities = [
        {"gear": {"id": "gRECENT"}, "start_date_local": "2025-08-03T08:00:00"},
    ]
    ctx = build_shoe_context(
        shoes=[dict(s) for s in shoes],
        profiles=load_shoe_profiles(),
        activities=activities,
        planned_workouts=[dict(_RUN)],
        weather_info="",
        race_in_days=None,
        today_str=today,
        backend="intervals",
    )
    rec = ctx["shoeRecommendation"]
    assert rec["primary"]["name"] == "Idle Trainer"
    assert rec["alternative"]["name"] == "Recent Trainer"


def test_tie_break_prefers_less_worn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _isolate_shoe_log: None
) -> None:
    """Two equally-rested (both idle) shoes → the less-worn one wins."""
    _equip(_EQUIP_MD_TIE, tmp_path, monkeypatch)
    shoes = [
        {"gear_key": "gWORN", "name": "Worn Trainer", "distance_km": 600},
        {"gear_key": "gFRESH", "name": "Fresh Trainer", "distance_km": 150},
    ]
    ctx = build_shoe_context(
        shoes=[dict(s) for s in shoes],
        profiles=load_shoe_profiles(),
        activities=[],  # neither worn in window → rotation tie
        planned_workouts=[dict(_RUN)],
        weather_info="",
        race_in_days=None,
        today_str="2025-08-15",
        backend="intervals",
    )
    # Order in the shoes list puts the worn shoe first — the tie-break, not
    # list order, must decide.
    assert ctx["shoeRecommendation"]["primary"]["name"] == "Fresh Trainer"
