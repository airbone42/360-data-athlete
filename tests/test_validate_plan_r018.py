"""Tests for validate_plan.py R018 — non-endurance duration plausibility.

R018 estimates a strength/core/reha session's realistic duration from its
structure (sets × reps × tempo/hold seconds, ×2 for per-Seite/Richtung,
plus inter-set rest) and WARNs when the declared ``duration_min`` is below
60 % of that estimate. It is the non-endurance counterpart to R011, which
only covers ``intervals_icu`` endurance sessions.

Motivating case: a bilateral core block (all exercises per-side, with long
isometric holds) declared at 15 min while the real session runs ~30 min —
the per-side doubling and hold-time were not summed.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    check_duration_plausibility,
    _estimate_session_seconds,
)


def _ctx() -> Context:
    return Context(target_date="2025-06-14")


# The real 2026-06-14 core block that triggered the rule (dates synthetic).
CORE_DESC = (
    "MAIN — Core leicht (14 min)\n"
    "Side Plank mit Hueft-Abduktion: 3x35s/Seite | halten.\n"
    "Side Plank T-Reach: 3x8/Seite | halten.\n"
    "Stir-the-Pot: 3x7/Richtung Tempo 3-0-3, 5-10s Pause.\n"
    "McGill Curl-up: 3x10/Seite 9s Hold | halten.\n"
)

# An atomic shoulder block whose declared 22 min is within tolerance.
SHOULDER_DESC = (
    "Scapular Pullups: 3x6 BW, 1-2s Hold | RPE 6.\n"
    "Row (Gummiband): 3x15 20kg | RPE 6.\n"
    "KB Overhead Press: 3x7 8kg | RPE 7.\n"
    "Diagonalzug hoch->tief: 2x8/Seite Gummiband oben.\n"
    "Diagonalzug tief->hoch: 3x8/Seite Gummiband unten.\n"
    "Scapular Depression Lift: 3x8/rechts 5,5kg.\n"
)


def _core_workout(duration_min: int) -> dict:
    return {
        "type": "Workout",
        "name": "Core leicht (Schicht D)",
        "tags": ["core"],
        "duration_min": duration_min,
        "description": CORE_DESC,
    }


# ─── Triggering ──────────────────────────────────────────────────────────

def test_r018_fires_on_bilateral_core_underestimate():
    findings = check_duration_plausibility([_core_workout(15)], _ctx())
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R018"
    assert f.severity == "WARNING"
    assert "implausibly short" in f.message


def test_r018_estimate_doubles_per_side_and_sums_holds():
    """The bilateral core estimate must land well above the declared 15 min."""
    est = _estimate_session_seconds(CORE_DESC)
    assert est is not None
    est_s, n_ex = est
    assert n_ex == 4
    # ~27 min: per-side doubling + the McGill 9 s holds dominate.
    assert est_s / 60 > 24


# ─── Non-triggering ──────────────────────────────────────────────────────

def test_r018_silent_when_duration_matches():
    findings = check_duration_plausibility([_core_workout(30)], _ctx())
    assert findings == []


def test_r018_silent_on_shoulder_block_within_tolerance():
    """22 min declared vs ~27 min estimate (ratio 0.81 > 0.6) → no finding."""
    w = {
        "type": "WeightTraining",
        "name": "Schulter-Reha Block A",
        "tags": ["upperbody", "mobility"],
        "duration_min": 22,
        "description": SHOULDER_DESC,
    }
    findings = check_duration_plausibility([w], _ctx())
    assert findings == []


def test_r018_silent_on_endurance():
    """Run/Ride are covered by R011 — R018 must skip them."""
    w = {
        "type": "Run",
        "name": "Easy Z2",
        "tags": ["run"],
        "duration_min": 5,  # absurdly short, but R018 must not touch endurance
        "description": "Steady Z2.",
    }
    findings = check_duration_plausibility([w], _ctx())
    assert findings == []


def test_r018_silent_on_rest_day():
    w = {"type": "Workout", "name": "Rest", "duration_min": 0, "description": ""}
    assert check_duration_plausibility([w], _ctx()) == []
