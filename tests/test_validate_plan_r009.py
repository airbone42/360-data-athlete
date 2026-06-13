"""Tests for validate_plan.py R009 — HR range consistency (description vs intervals_icu).

The Weekly-Hard-Reize cap formerly shared the R009 id; it is now R017
(see test_validate_plan_r017.py).
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
    check_hr_range_consistency,
)


def _ctx() -> Context:
    return Context(target_date="2025-05-23")


def _run(description: str, intervals_icu: str) -> dict:
    return {
        "type": "Run",
        "name": "Recovery Run",
        "workout_type": "RECOVERY",
        "description": description,
        "intervals_icu": intervals_icu,
    }


def test_r009_zone_code_with_bpm_description_warns():
    """Description names a BPM range, code pushes the full zone → WARNING."""
    findings = check_hr_range_consistency(
        [_run("Recovery 50 min, HR 120-130", "- 50m Z1 HR")], _ctx()
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R009"
    assert f.severity == "WARNING"
    assert "120-130" in f.message


def test_r009_suggestion_uses_allowed_grammar():
    """F5-02: the suggestion must point to the allowed %LTHR grammar — not
    to the `XXm HR lo-hi` format that intervals.icu silently drops (R012)."""
    findings = check_hr_range_consistency(
        [_run("Recovery 50 min, HR 120-130", "- 50m Z1 HR")], _ctx()
    )
    sugg = findings[0].suggestion
    assert "% LTHR" in sugg
    assert "HR 120-130" not in sugg


def test_r009_silent_when_code_carries_explicit_range():
    """Code repeats the BPM range explicitly → consistent, no finding."""
    findings = check_hr_range_consistency(
        [_run("Recovery 50 min, HR 120-130", "- 50m 72-78% LTHR\n- HR 120-130 cap")],
        _ctx(),
    )
    assert findings == []


def test_r009_silent_without_bpm_in_description():
    """No BPM range in the description → nothing to cross-check."""
    findings = check_hr_range_consistency(
        [_run("Recovery 50 min locker", "- 50m Z1 HR")], _ctx()
    )
    assert findings == []
