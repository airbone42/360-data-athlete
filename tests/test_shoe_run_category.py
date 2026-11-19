"""Run category and shoe category are hard inputs to the shoe choice.

Regression for a treadmill Z2 run with strides that carried only the `run`
tag: no workout_type, no intensity, so no pace bucket and no category. Every
asphalt shoe was eligible and the rotation bonus alone decided — the plated
race/tempo shoe idle for weeks beat the easy trainers worn two and three days
earlier. Now an unmarked run is `easy`, tempo / race / carbon shoes never
carry an easy or recovery run, carbon never runs on a belt, and days unused
only break ties inside the fitting category.

All fixture data is synthetic.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.graphs import shoe_advisor
from app.graphs.shoe_advisor import (
    _category_tier,
    build_shoe_context,
    load_shoe_profiles,
    run_category,
    shoe_category,
)

_TODAY = "2025-03-15"

_EQUIP_MD = """# Equipment

## Running shoes

- icu_gear_id: gEASY_A
  name: "Easy A"
  type: easy
  role: daily
  terrain: asphalt
  pace_range_min_km: [4.8, 7.0]
  recommended_tags: [easy, recovery, long]
  threshold_km: 900

- icu_gear_id: gEASY_B
  name: "Easy B"
  type: easy
  role: daily
  terrain: asphalt
  pace_range_min_km: [5.0, 7.5]
  recommended_tags: [easy, recovery]
  excluded_workout_types: [long]
  threshold_km: 900

- icu_gear_id: gEASY_C
  name: "Easy C"
  type: easy
  role: daily
  terrain: asphalt
  pace_range_min_km: [4.5, 6.5]
  recommended_tags: [easy]
  excluded_workout_types: [long]
  threshold_km: 800

- icu_gear_id: gTEMPO
  name: "Tempo Trainer"
  type: tempo
  role: daily
  terrain: asphalt
  pace_range_min_km: [3.5, 5.0]
  recommended_tags: [intervals, tempo]
  threshold_km: 700

- icu_gear_id: gCARBON
  name: "Plated Racer"
  type: tempo
  role: daily
  primary_race: true
  terrain: asphalt
  pace_range_min_km: [3.0, 4.3]
  recommended_tags: [intervals, tempo]
  threshold_km: 500
  race_prep_days: 25

- icu_gear_id: gTRAIL
  name: "Trail Shoe"
  type: trail
  role: daily
  terrain: trail
  pace_range_min_km: [4.5, 7.5]
  recommended_tags: [trail, easy]
  threshold_km: 800
"""

_SHOES = [
    {"gear_key": "gEASY_A", "name": "Easy A", "distance_km": 300},
    {"gear_key": "gEASY_B", "name": "Easy B", "distance_km": 250},
    {"gear_key": "gEASY_C", "name": "Easy C", "distance_km": 400},
    {"gear_key": "gTEMPO", "name": "Tempo Trainer", "distance_km": 200},
    {"gear_key": "gCARBON", "name": "Plated Racer", "distance_km": 150},
    {"gear_key": "gTRAIL", "name": "Trail Shoe", "distance_km": 350},
]

# Easy A worn 2 days ago, Easy B 3 days, Easy C 6 days; the tempo and the
# plated shoe sit idle for weeks — the configuration that used to flip it.
_ACTIVITIES = [
    {"gear": {"id": "gTEMPO"}, "start_date_local": "2025-01-10T08:00:00"},
    {"gear": {"id": "gCARBON"}, "start_date_local": "2025-01-20T08:00:00"},
    {"gear": {"id": "gEASY_C"}, "start_date_local": "2025-03-09T08:00:00"},
    {"gear": {"id": "gEASY_B"}, "start_date_local": "2025-03-12T08:00:00"},
    {"gear": {"id": "gEASY_A"}, "start_date_local": "2025-03-13T08:00:00"},
]


@pytest.fixture()
def _equipment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "equipment.md"
    p.write_text(_EQUIP_MD, encoding="utf-8")
    monkeypatch.setattr(shoe_advisor, "_equipment_md_path", lambda: p)


def _recommend(workout: dict, *, race_in_days: int | None = None) -> dict:
    ctx = build_shoe_context(
        shoes=[dict(s) for s in _SHOES],
        profiles=load_shoe_profiles(),
        activities=_ACTIVITIES,
        planned_workouts=[workout],
        weather_info="",
        race_in_days=race_in_days,
        today_str=_TODAY,
        backend="intervals",
    )
    return ctx["shoeRecommendation"]


# ── run_category ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("workout", "expected"),
    [
        ({"tags": ["run"]}, "easy"),
        ({"tags": ["run"], "intensity": "medium"}, "easy"),
        ({"tags": ["run"], "intensity": "low", "workout_type": "EASY"}, "easy"),
        ({"tags": ["run", "intervals"], "workout_type": "EASY"}, "easy"),  # strides
        ({"tags": ["run", "intervals"]}, "intervals"),
        ({"tags": ["run"], "intensity": "high"}, "intervals"),
        ({"tags": ["run", "tempo"]}, "tempo"),
        ({"workout_type": "LONG", "tags": ["run", "intervals"]}, "long"),
        ({"workout_type": "RECOVERY"}, "recovery"),
        ({"workout_type": "RACE"}, "race"),
        ({"tags": ["run", "race"]}, "race"),
    ],
)
def test_run_category(workout: dict, expected: str) -> None:
    assert run_category(workout) == expected


def test_shoe_category_reads_role_race_first() -> None:
    assert shoe_category({"role": "race", "type": "tempo"}) == "race"
    assert shoe_category({"role": "daily", "type": "Easy"}) == "easy"
    assert shoe_category({}) == ""


def test_fast_shoes_never_fit_easy_or_recovery() -> None:
    for profile in (
        {"type": "tempo"},
        {"role": "race"},
        {"type": "easy", "carbon": True},
        {"type": "easy", "primary_race": True},
        # an opt-in tag must not cross the hard rule
        {"type": "tempo", "recommended_tags": ["easy"]},
    ):
        assert _category_tier(profile, "easy") is None, profile
        assert _category_tier(profile, "recovery") is None, profile


def test_long_run_tempo_shoe_only_by_opt_in() -> None:
    assert _category_tier({"type": "tempo"}, "long") is None
    assert _category_tier({"type": "tempo", "recommended_tags": ["long"]}, "long") == 1
    assert _category_tier({"type": "easy"}, "long") == 0


# ── build_shoe_context: the treadmill easy-run case ───────────────────────


def test_unmarked_treadmill_easy_run_gets_an_easy_shoe(_equipment: None) -> None:
    rec = _recommend({"type": "Run", "tags": ["run"], "surface": "treadmill"})
    assert rec["category"] == "easy"
    picks = {rec["primary"]["gear_id"], rec["alternative"]["gear_id"]}
    assert picks <= {"gEASY_A", "gEASY_B", "gEASY_C"}
    assert not {"gTEMPO", "gCARBON"} & set(rec["eligible"])
    # Inside the category, rotation decides: Easy C rested longest.
    assert rec["primary"]["gear_id"] == "gEASY_C"
    assert rec["primary"]["reason"].startswith("easy run")


def test_unmarked_outdoor_easy_run_also_excludes_fast_shoes(_equipment: None) -> None:
    rec = _recommend({"type": "Run", "tags": ["run"], "surface": "asphalt"}, race_in_days=10)
    assert not {"gTEMPO", "gCARBON"} & set(rec["eligible"])


def test_treadmill_intervals_take_the_tempo_trainer_not_the_plate(_equipment: None) -> None:
    rec = _recommend(
        {"type": "Run", "tags": ["run", "intervals"], "workout_type": "INTERVALS",
         "surface": "treadmill"},
        race_in_days=10,
    )
    assert rec["primary"]["gear_id"] == "gTEMPO"
    assert "gCARBON" not in rec["eligible"]


def test_race_window_bonus_only_on_the_race_surface(_equipment: None) -> None:
    asphalt = _recommend(
        {"type": "Run", "tags": ["run", "intervals"], "workout_type": "INTERVALS",
         "surface": "asphalt"},
        race_in_days=10,
    )
    assert asphalt["primary"]["gear_id"] == "gCARBON"
    # Outside the window the plated shoe is just another tempo shoe; the
    # longer-rested tempo trainer takes the slot.
    outside = _recommend(
        {"type": "Run", "tags": ["run", "intervals"], "workout_type": "INTERVALS",
         "surface": "asphalt"},
        race_in_days=60,
    )
    assert outside["primary"]["gear_id"] == "gTEMPO"
    forest = _recommend(
        {"type": "Run", "tags": ["run", "intervals"], "workout_type": "INTERVALS",
         "surface": "forest-path"},
        race_in_days=10,
    )
    assert forest["primary"]["gear_id"] == "gTEMPO"


def test_long_run_keeps_the_long_capable_easy_shoe(_equipment: None) -> None:
    rec = _recommend({"type": "Run", "tags": ["run"], "workout_type": "LONG",
                      "surface": "asphalt"})
    assert rec["primary"]["gear_id"] == "gEASY_A"
    assert set(rec["eligible"]) == {"gEASY_A"}
