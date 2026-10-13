"""Tests for validate_plan.py R031 — treadmill main steps dosed by pace (opt-in).

`treadmill_dosing: pace` in athlete_status.md switches belt sessions from HR
dosing to pace dosing; main steps without a pace target are then blocked.
Absent key or `hr` → rule silent.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    RULES,
    Context,
    check_treadmill_pace_dosing,
)

PACE_CTX = Context(target_date="2026-10-13", athlete_status="- **treadmill_dosing:** pace\n")
HR_CTX = Context(target_date="2026-10-13", athlete_status="- **treadmill_dosing:** hr\n")
NO_KEY_CTX = Context(target_date="2026-10-13")

HR_ONLY = (
    "Warmup\n- Easy 8m press lap\n\n"
    "Main\n- Z2 29m 76-83% LTHR — breathing binds\n\n"
    "Cool-down\n- Cool-down 5m press lap"
)
PACE_MAIN = (
    "Warmup\n- Easy 8m press lap\n"
    "- A-Skips 1m — beside the belt\n\n"
    "Main\n- Z2 29m 5:05/km Pace — HR only a guard, cap 139\n\n"
    "Strides 6x\n- Easy 90s\n- Stride 20s\n\n"
    "Cool-down\n- Cool-down 5m press lap"
)


def _w(icu: str, surface: str | None = "treadmill", indoor: bool = False, wtype: str = "Run") -> dict:
    w = {"type": wtype, "name": "Belt", "intervals_icu": icu, "indoor": indoor}
    if surface:
        w["surface"] = surface
    return w


def test_r031_registered():
    assert ("R031", check_treadmill_pace_dosing) in RULES


def test_r031_silent_without_opt_in():
    assert check_treadmill_pace_dosing([_w(HR_ONLY)], NO_KEY_CTX) == []
    assert check_treadmill_pace_dosing([_w(HR_ONLY)], HR_CTX) == []


def test_r031_errors_on_hr_only_main_step():
    f = check_treadmill_pace_dosing([_w(HR_ONLY)], PACE_CTX)
    assert len(f) == 1
    assert f[0].rule_id == "R031" and f[0].severity == "ERROR"
    assert "Z2 29m" in f[0].message


def test_r031_errors_on_target_less_main_step_and_indoor_flag():
    icu = "Main\n- Tempo 20m — steady"
    f = check_treadmill_pace_dosing([_w(icu, surface=None, indoor=True)], PACE_CTX)
    assert len(f) == 1 and f[0].severity == "ERROR"


def test_r031_clean_with_pace_main_step():
    assert check_treadmill_pace_dosing([_w(PACE_MAIN)], PACE_CTX) == []


def test_r031_accepts_pace_range_and_percent_pace():
    icu = "Main 4x\n- 5m 4:00-4:05/km Pace\n- Easy 2m 70-75% LTHR\n\nMain\n- 10m 80-85% Pace"
    assert check_treadmill_pace_dosing([_w(icu)], PACE_CTX) == []


def test_r031_silent_on_outdoor_run_with_hr():
    assert check_treadmill_pace_dosing([_w(HR_ONLY, surface="asphalt")], PACE_CTX) == []


def test_r031_ignores_drills_and_strides_without_target():
    icu = (
        "Warmup\n- Easy 10m press lap\n- Leg swings 1m\n\n"
        "Drills\n- A-Skips 2m — beside the belt\n\n"
        "Main\n- 30m 5:05/km Pace\n\n"
        "Strides 4x\n- Easy 90s 72% LTHR\n- Stride 20s\n\n"
        "Cool-down\n- 5m 70% LTHR"
    )
    assert check_treadmill_pace_dosing([_w(icu)], PACE_CTX) == []


def test_r031_pace_in_cue_does_not_count():
    icu = "Main\n- Z2 30m 76-83% LTHR — belt at 5:05/km Pace"
    assert len(check_treadmill_pace_dosing([_w(icu)], PACE_CTX)) == 1
