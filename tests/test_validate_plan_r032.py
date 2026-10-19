"""Tests for validate_plan.py R032 — run-free day names why it has no easy block.

Incident behind the rule: a gym-hall day was planned without the easy bike
block on the sentence "the hall is the day's load"; a semantic review let it
through as INFO and the athlete had to ask why the impact-free volume was gone.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    check_cross_training_decision,
)


def _ctx() -> Context:
    return Context(target_date="2026-10-19")


def _hall(focus: str = "") -> dict:
    return {"type": "Workout", "name": "Gym hall", "tags": ["ninja"], "focus": focus}


def test_empty_plan_is_rest_day():
    assert check_cross_training_decision([], _ctx()) == []


def test_day_with_ride_passes():
    ride = {"type": "VirtualRide", "name": "Easy ride", "tags": ["ride"]}
    assert check_cross_training_decision([_hall(), ride], _ctx()) == []


def test_day_with_run_passes():
    run = {"type": "Run", "name": "Easy run", "tags": ["run"]}
    assert check_cross_training_decision([run], _ctx()) == []


def test_run_free_day_without_marker_warns():
    out = check_cross_training_decision([_hall("No bike: the hall is the day's load.")], _ctx())
    assert len(out) == 1
    assert out[0].rule_id == "R032"
    assert out[0].severity == "WARNING"


def test_valid_marker_passes():
    w = _hall("[cross-training: legs-reserved] long run tomorrow 09:00")
    assert check_cross_training_decision([w], _ctx()) == []


def test_marker_in_coaching_notes_counts():
    w = _hall()
    w["coaching_notes"] = "[cross-training: time-budget] only 60 min available"
    assert check_cross_training_decision([w], _ctx()) == []


def test_unknown_class_warns():
    out = check_cross_training_decision([_hall("[cross-training: day-load]")], _ctx())
    assert len(out) == 1
    assert "day-load" in out[0].message
