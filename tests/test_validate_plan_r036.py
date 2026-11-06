"""Tests for validate_plan.py R036 — easy ride main step below the Z2 watt floor.

Incident behind the rule: an indoor easy ride was prescribed at 180 W while the
athlete's lowest Z2 step was 200 W. The watt figure had drifted into the
briefing from an earlier session; no decision stood behind it.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import Context, check_ride_easy_watt_floor  # type: ignore  # noqa: E402

STATUS = "ride_z2_floor_w: 200\n"

ICU_LOW = (
    "Warmup\n- Warmup 5m 140W 85-90rpm\n\nMain\n- Locker 15m 180W 85-90rpm\n\n"
    "Cool-down\n- Cool-down 5m 130W"
)
ICU_OK = ICU_LOW.replace("180W", "200W")


def _ctx(status: str = STATUS) -> Context:
    return Context(target_date="2026-11-06", athlete_status=status)


def _ride(icu: str, tags=("ride",)) -> dict:
    return {"type": "Ride", "name": "Rad locker", "tags": list(tags), "intervals_icu": icu}


def test_main_step_below_floor_errors():
    f = check_ride_easy_watt_floor([_ride(ICU_LOW)], _ctx())
    assert [x.rule_id for x in f] == ["R036"]
    assert f[0].severity == "ERROR"


def test_warmup_and_cooldown_below_floor_are_fine():
    assert check_ride_easy_watt_floor([_ride(ICU_OK)], _ctx()) == []


def test_off_without_key():
    assert check_ride_easy_watt_floor([_ride(ICU_LOW)], _ctx("")) == []


def test_interval_rides_are_skipped():
    assert check_ride_easy_watt_floor([_ride(ICU_LOW, ("ride", "intervals"))], _ctx()) == []


def test_severity_configurable():
    f = check_ride_easy_watt_floor(
        [_ride(ICU_LOW)], _ctx(STATUS + "ride_z2_floor_severity: warning\n")
    )
    assert f[0].severity == "WARNING"
