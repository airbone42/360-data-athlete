"""Tests for validate_plan.py R010 — easy-run HR ceiling (%LTHR + zone notation).

Covers review finding F2-07: R010 used to detect easy-run ceiling
violations only via `lo-hi bpm` ranges, while R012 bans bpm and mandates
`Zn HR` / `XX-YY% LTHR` / `XX-YY% HR` — making R010 blind to exactly the
notations a compliant plan uses.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the scripts/ directory importable.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    check_easy_hr_ceiling,
)


# Synthetic zone model: LTHR 170, Z2 upper bound 142.
STATUS_WITH_LTHR = (
    "LTHR current: 170 bpm\n"
    "Zones: Z1 1–115 | Z2 116–142 | Z3 143–155 | Z4 156–170 | Z5 171–185\n"
)
STATUS_WITHOUT_LTHR = (
    "Zones: Z1 1–115 | Z2 116–142 | Z3 143–155 | Z4 156–170 | Z5 171–185\n"
)


def _ctx(athlete_status: str = STATUS_WITH_LTHR) -> Context:
    return Context(target_date="2025-05-23", athlete_status=athlete_status)


def _easy_run(intervals_icu: str = "", description: str = "", workout_type: str = "EASY") -> dict:
    return {
        "type": "Run",
        "name": "Easy Z2",
        "workout_type": workout_type,
        "intervals_icu": intervals_icu,
        "description": description,
    }


# ─── %LTHR ranges ────────────────────────────────────────────────────────

def test_r010_pct_lthr_ceiling_above_z2_errors():
    """84-90% LTHR with LTHR 170 → ceiling ≈153 bpm > Z2 upper 142 → ERROR."""
    findings = check_easy_hr_ceiling([_easy_run("- 40m 84-90% LTHR")], _ctx())
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R010"
    assert f.severity == "ERROR"
    assert "90% LTHR" in f.message


def test_r010_pct_lthr_within_z2_silent():
    """70-80% LTHR → ceiling 136 bpm ≤ 142 → no finding."""
    assert check_easy_hr_ceiling([_easy_run("- 40m 70-80% LTHR")], _ctx()) == []


def test_r010_pct_range_without_lthr_warns_instead_of_silence():
    """No LTHR in athlete_status → %LTHR ceiling unverifiable → WARNING, not silence."""
    findings = check_easy_hr_ceiling(
        [_easy_run("- 40m 84-90% LTHR")], _ctx(STATUS_WITHOUT_LTHR)
    )
    assert len(findings) == 1
    assert findings[0].rule_id == "R010"
    assert findings[0].severity == "WARNING"
    assert "LTHR" in findings[0].message


# ─── Zone targets on easy/recovery steps ─────────────────────────────────

def test_r010_zone3_hr_step_errors():
    findings = check_easy_hr_ceiling([_easy_run("- 40m Z3 HR")], _ctx())
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"
    assert "Z3 HR" in findings[0].message


def test_r010_cross_zone_range_ending_z3_errors():
    findings = check_easy_hr_ceiling([_easy_run("- 40m Z2-Z3 HR")], _ctx())
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"


def test_r010_zone2_hr_step_silent():
    assert check_easy_hr_ceiling([_easy_run("- 40m Z2 HR")], _ctx()) == []


def test_r010_zone_mention_in_description_prose_ignored():
    """Prose like 'stay below Z3 HR' in the description is no step target."""
    findings = check_easy_hr_ceiling(
        [_easy_run("- 40m Z2 HR", description="Locker bleiben — stay below Z3 HR.")],
        _ctx(),
    )
    assert findings == []


# ─── BPM ranges (legacy + HR-without-bpm-literal) ────────────────────────

def test_r010_bpm_range_above_z2_still_errors():
    findings = check_easy_hr_ceiling(
        [_easy_run("", description="HF-Deckel: 120-150 bpm")], _ctx()
    )
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"


def test_r010_hr_range_without_bpm_literal_errors():
    """`HR 120-150` (no 'bpm') must be caught as a ceiling notation too."""
    findings = check_easy_hr_ceiling(
        [_easy_run("", description="Ceiling: HR 120-150")], _ctx()
    )
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"
    assert "150" in findings[0].message


# ─── Scope guards ────────────────────────────────────────────────────────

def test_r010_quality_workout_not_in_scope():
    """Z3+ targets are legitimate on WORKOUT-type runs — rule is easy/recovery only."""
    findings = check_easy_hr_ceiling(
        [_easy_run("- 5m Z4 HR", workout_type="WORKOUT")], _ctx()
    )
    assert findings == []


def test_r010_silent_without_zone_model():
    """No Z2 upper bound in athlete_status → rule cannot anchor, stays silent."""
    findings = check_easy_hr_ceiling(
        [_easy_run("- 40m 84-90% LTHR")], _ctx(athlete_status="")
    )
    assert findings == []
