"""Tests for validate_plan.py R030 — no target tokens in intervals_icu cue text.

intervals.icu parses the whole step line; a watt / percent / rpm figure in
the free-text cue after `—` overrides the target in the step syntax.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    check_cue_target_leak,
)

CTX = Context(target_date="2026-06-12")


def _w(icu: str, wtype: str = "Ride") -> dict:
    return {"type": wtype, "name": "Test", "intervals_icu": icu}


def test_r030_fires_on_watts_in_cue():
    icu = "Main\n- 48m 200W 86rpm — if the groin reacts, back off to 150 W"
    f = check_cue_target_leak([_w(icu)], CTX)
    assert len(f) == 1 and f[0].rule_id == "R030" and f[0].severity == "ERROR"


def test_r030_fires_on_rpm_range_in_cue():
    icu = "Warmup\n- 8m ramp 150W-195W 85rpm — cadence 85-88 rpm"
    assert len(check_cue_target_leak([_w(icu)], CTX)) == 1


def test_r030_ignores_percent_in_cue():
    # Percent figures in cues were verified not to leak into workout_doc.
    icu = "Main\n- Z2 20m 76-83% LTHR — treadmill incline 1 %, ceiling 83 %"
    assert check_cue_target_leak([_w(icu, "Run")], CTX) == []


def test_r030_warns_on_bare_zone_in_cue():
    icu = "Main\n- Easy 30m 76-83% LTHR — never Z3"
    f = check_cue_target_leak([_w(icu, "Run")], CTX)
    assert len(f) == 1 and f[0].severity == "WARNING"


def test_r030_quiet_on_explicit_hr_zone_in_cue():
    icu = "Main\n- Easy 30m 76-83% LTHR — stay below Z3 HR"
    assert check_cue_target_leak([_w(icu, "Run")], CTX) == []


def test_r030_quiet_when_targets_only_in_step_syntax():
    icu = "\n".join([
        "Warmup",
        "- 8m ramp 150W-195W 85rpm — easy spin-up",
        "Main",
        "- 48m 200W 86rpm — stay seated, ease off clearly if the groin reacts",
        "- Z2 22m 76-83% LTHR — ceiling 139, never above zone 2",
        "- Stride 20s — mile pace, quick feet",
    ])
    assert check_cue_target_leak([_w(icu)], CTX) == []


def test_r030_ignores_lines_without_cue_separator():
    icu = "Main\n- 20m 200W 90rpm"
    assert check_cue_target_leak([_w(icu)], CTX) == []
