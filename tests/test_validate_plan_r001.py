"""Tests for validate_plan.py R001 — reps ceiling (15) with rehab whitelist.

Focus: rotator-cuff internal-rotation band work is a low-load
endurance/fatigue protocol (high reps by design, e.g. a physio-prescribed
3x25) and must NOT be flagged, while genuine hypertrophy lifts above 15
reps still are.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    check_reps_ceiling,
)


def _ctx() -> Context:
    return Context(target_date="2025-06-17")


def _workout(line: str) -> dict:
    return {"type": "Workout", "name": "Block", "description": f"MAIN\n{line}"}


def test_r001_internal_rotation_high_reps_allowed():
    """Physio IR fatigue protocol (3x25) is whitelisted — no finding."""
    assert check_reps_ceiling(
        [_workout("Internal Rotation Band (Innenrotation): 3x25 Theraband | RPE 4-5")],
        _ctx(),
    ) == []


def test_r001_hypertrophy_lift_high_reps_still_flagged():
    """A normal curl above 15 reps stays a WARNING (not whitelisted)."""
    findings = check_reps_ceiling([_workout("Bizeps-Curl: 3x20 8kg")], _ctx())
    assert len(findings) == 1
    assert findings[0].rule_id == "R001"
    assert findings[0].severity == "WARNING"


def test_r001_within_ceiling_silent():
    assert check_reps_ceiling([_workout("Internal Rotation Band: 3x15")], _ctx()) == []
