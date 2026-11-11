"""Tests for validate_plan.py R007 (upperbody exemption) and R038–R041."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    RULES,
    Context,
    check_kg_line_without_rpe,
    check_pap_lock_trigger,
    check_pillar_rotation,
    check_same_day_hard_double,
    check_short_step_hr_target,
)


def _ctx(**kw) -> Context:
    return Context(target_date="2026-11-11", **kw)


def test_new_rules_registered():
    ids = [rid for rid, _ in RULES]
    for rid in ("R038", "R039", "R040", "R041"):
        assert ids.count(rid) == 1


# ── R007 ──────────────────────────────────────────────────────────────

def _ninja(desc: str, *tags: str, name: str = "Ninja") -> dict:
    return {"type": "WeightTraining", "name": name, "tags": ["ninja", *tags], "description": desc}


def test_r007_pull_and_push_in_one_session_warns():
    f = check_pillar_rotation([_ninja("TRX Row 3x10\nPush-up 3x8")], _ctx())
    assert [x.rule_id for x in f] == ["R007"]


def test_r007_upperbody_session_is_exempt():
    f = check_pillar_rotation([_ninja("TRX Row 3x10\nPush-up 3x8", "upperbody")], _ctx())
    assert f == []


def test_r007_upperbody_does_not_cover_a_second_session():
    w1 = _ninja("TRX Row 3x10\nPush-up 3x8", "upperbody", name="Oberkörper")
    w2 = _ninja("Dip 3x6", name="Abend")
    f = check_pillar_rotation([w1, w2], _ctx())
    assert len(f) == 1 and "Abend" in f[0].workout


def test_r007_pull_and_push_in_two_sessions_still_warns():
    f = check_pillar_rotation([_ninja("TRX Row 3x10", name="A"), _ninja("Push-up 3x8", name="B")], _ctx())
    assert len(f) == 1 and f[0].workout == "A + B"


# ── R038 ──────────────────────────────────────────────────────────────

RUN_INT = {"type": "Run", "name": "Run 5x3", "tags": ["run", "intervals"],
           "intervals_icu": "Main 5x\n- 3m 98-102% LTHR\n- 2m 70-75% LTHR"}
RIDE_INT = {"type": "VirtualRide", "name": "Ride VO2", "tags": ["ride"],
            "intervals_icu": "Main 4x\n- 3m Z5 HR\n- 3m 55%"}
RIDE_Z2 = {"type": "VirtualRide", "name": "Ride Z2", "tags": ["ride"],
           "intervals_icu": "Main\n- 50m 200w"}


def test_r038_two_hard_sessions_warn():
    f = check_same_day_hard_double([RUN_INT, RIDE_INT], _ctx())
    assert [x.rule_id for x in f] == ["R038"] and f[0].severity == "WARNING"


def test_r038_one_hard_session_passes():
    assert check_same_day_hard_double([RUN_INT, RIDE_Z2], _ctx()) == []


def test_r038_documented_double_is_info():
    ride = {**RIDE_INT, "coaching_notes": "[double-ok: race simulation]"}
    f = check_same_day_hard_double([RUN_INT, ride], _ctx())
    assert f[0].severity == "INFO"


# ── R039 ──────────────────────────────────────────────────────────────

def _strength(desc: str) -> dict:
    return {"type": "WeightTraining", "name": "Kraft", "tags": ["legs"], "description": desc}


def test_r039_kg_line_without_rpe_warns():
    desc = "MAIN\n\nGoblet Squat: 3x10 @ 16 kg | slow down\n\nRow: 3x8 @ 20 kg | RPE 7"
    f = check_kg_line_without_rpe([_strength(desc)], _ctx())
    assert len(f) == 1 and "Goblet Squat" in f[0].message and "Row" not in f[0].message


def test_r039_warmup_and_feedback_are_skipped():
    desc = (
        "WARM-UP (5 min)\nGoblet Squat ramp: 2x5 @ 8 kg\n\n"
        "MAIN\nGoblet Squat: 3x10 @ 16 kg | RPE 7\n\n"
        "FEEDBACK: RPE and the actual load (16 kg?)"
    )
    assert check_kg_line_without_rpe([_strength(desc)], _ctx()) == []


def test_r039_unloaded_and_endurance_pass():
    assert check_kg_line_without_rpe([_strength("Plank: 3x40s | quiet hips")], _ctx()) == []
    run = {"type": "Run", "name": "Run", "description": "Carry 5 kg vest"}
    assert check_kg_line_without_rpe([run], _ctx()) == []


# ── R040 ──────────────────────────────────────────────────────────────

def _run(icu: str) -> dict:
    return {"type": "Run", "name": "Easy + Strides", "tags": ["run"], "intervals_icu": icu}


def test_r040_hr_target_on_stride_warns():
    f = check_short_step_hr_target([_run("Strides 4x\n- Stride 20s 95-100% LTHR\n- Easy 90s 70% LTHR")], _ctx())
    assert [x.rule_id for x in f] == ["R040"] and "Stride 20s" in f[0].message
    assert "Easy 90s" not in f[0].message


def test_r040_hr_target_on_short_step_warns():
    f = check_short_step_hr_target([_run("Main 6x\n- 45s Z5 HR\n- 75s 70% LTHR")], _ctx())
    assert len(f) == 1 and "45s" in f[0].message


def test_r040_clean_strides_and_long_steps_pass():
    icu = ("Main\n- 40m 78-82% LTHR\n\nStrides 4x\n"
           "- Stride 20s — 1 km race pace, Z5 HR feel\n- Easy 90s 70% LTHR")
    assert check_short_step_hr_target([_run(icu)], _ctx()) == []


# ── R041 ──────────────────────────────────────────────────────────────

LEGS_PAP = {"type": "WeightTraining", "name": "Beine", "tags": ["legs"],
            "focus": "Calf raises locked today (PAP).", "description": "MAIN\nSquat: 3x5 @ 60 kg | RPE 7"}
LEDGER = "| Tag | Vormerkung |\n|---|---|\n| Do 12.11. | {row} |\n"


def test_r041_pap_lock_without_quality_warns():
    ctx = _ctx(tomorrow_workouts=[RIDE_Z2], competition_plan=LEDGER.format(row="Rolle Z2 50 min"))
    f = check_pap_lock_trigger([LEGS_PAP], ctx)
    assert [x.rule_id for x in f] == ["R041"] and f[0].severity == "WARNING"


def test_r041_quality_today_clears():
    assert check_pap_lock_trigger([LEGS_PAP, RUN_INT], _ctx(tomorrow_workouts=[])) == []


def test_r041_quality_tomorrow_on_calendar_clears():
    assert check_pap_lock_trigger([LEGS_PAP], _ctx(tomorrow_workouts=[RIDE_INT])) == []


def test_r041_quality_tomorrow_in_ledger_clears():
    ctx = _ctx(competition_plan=LEDGER.format(row="Q-B 4×3 min @ 340 W morgens"))
    assert check_pap_lock_trigger([LEGS_PAP], ctx) == []


def test_r041_no_pap_mention_passes():
    w = {**LEGS_PAP, "focus": "Strides are PAP-compatible."}
    assert check_pap_lock_trigger([w], _ctx(tomorrow_workouts=[])) == []
