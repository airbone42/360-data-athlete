"""Tests for validate_plan.py R002 — shoulder lock (hang gap + heavy-overhead format).

Covers two review findings:
- F2-02: dead-hang/hang patterns missing from the lock list, and the
  hold-time exception matching trailing digits ("15s"/"45s" passed as
  allowed 2-5 s holds).
- F2-03: heavy-overhead patterns with typos and a weight-right-after-name
  assumption that never matched the canonical specialist inline format
  `Name: SxR Wkg | RPE`.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the scripts/ directory importable.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    HYPERTROPHY_REPS_CAP_OVERRIDES,
    Context,
    _matches_any,
    check_injury_locks_shoulder,
)


def _ctx(athlete_static: str = "Shoulder: overhead restriction active — rehab tier only.") -> Context:
    return Context(
        target_date="2025-05-23",
        athlete_static=athlete_static,
        injury_locks={"shoulder": ["overhead restriction"]},
    )


def _workout(line: str) -> dict:
    return {
        "type": "WeightTraining",
        "name": "Strength Block",
        "description": f"HAUPTTEIL (30 min)\n{line}",
    }


def _findings(line: str, ctx: Context | None = None):
    return check_injury_locks_shoulder([_workout(line)], ctx or _ctx())


# ─── Dead-hang exception: numeric hold parsing ───────────────────────────

def test_r002_dead_hang_short_hold_allowed():
    """Dead Hang 3s is the rehab-tier exception — no finding."""
    assert _findings("Dead Hang 3s") == []


def test_r002_dead_hang_15s_blocked():
    """15s must not pass via its trailing '5s' substring."""
    findings = _findings("Dead Hang 15s")
    assert len(findings) == 1
    assert findings[0].rule_id == "R002"
    assert findings[0].severity == "ERROR"


def test_r002_dead_hang_45s_blocked():
    findings = _findings("Dead Hang 45s")
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"


# ─── Bare hang lock + negative list ──────────────────────────────────────

def test_r002_bare_hang_blocked():
    findings = _findings("Bar Hang 30s")
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"


def test_r002_hanging_leg_raise_blocked():
    findings = _findings("Hanging Leg Raise: 3x8")
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"


def test_r002_hang_power_clean_not_a_hang():
    """Hang-position lift variants start from a hang position — no bar hang."""
    assert _findings("Hang Power Clean: 3x5 40kg") == []


def test_r002_overhang_word_not_matched():
    assert _findings("Overhang stretch 2x30s") == []


# ─── Heavy overhead: canonical specialist inline format ──────────────────

def test_r002_overhead_press_canonical_inline_format_blocked():
    """`Name: SxR Wkg | RPE` — the weight sits after sets/reps, not after the name."""
    findings = _findings("Overhead Press: 3x8 20kg | RPE 7")
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"
    assert "overhead" in findings[0].message.lower()


def test_r002_military_press_blocked():
    findings = _findings("Military Press: 4x6 30kg")
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"


def test_r002_kb_ohp_rehab_load_allowed():
    """Light KB OHP stays rehab-tier — below the heavy threshold."""
    assert _findings("KB Overhead Press: 3x8 4kg | RPE 5") == []


def test_r002_overhead_press_typo_fixed_in_override_list():
    """F2-03: the old override pattern (`overmlyhead`) could never match."""
    assert _matches_any("Overhead Press: 3x18", HYPERTROPHY_REPS_CAP_OVERRIDES)


# ─── Lock activation gate ────────────────────────────────────────────────

def test_r002_silent_when_lock_inactive():
    """No activation keyword in athlete_static → lock off, nothing fires."""
    ctx = _ctx(athlete_static="All clear, no restrictions.")
    assert check_injury_locks_shoulder([_workout("Dead Hang 45s")], ctx) == []
