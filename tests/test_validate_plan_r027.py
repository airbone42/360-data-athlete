"""Tests for validate_plan.py R027 — the %LTHR ceiling must match the intensity.

A threshold rep is prescribed AT LT2; an HM-/race-pace block is prescribed
below it, with a ceiling derived downward from race HR. Reusing one table for
the other is silent and wrong in both directions.
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
    check_hr_band_matches_intensity,
)


def _ctx() -> Context:
    return Context(target_date="2026-09-09")


def _run(intervals_icu: str) -> dict:
    return {
        "type": "Run",
        "name": "Quality",
        "workout_type": "INTERVALS",
        "tags": ["run", "intervals"],
        "intervals_icu": intervals_icu,
    }


def test_r027_threshold_rep_capped_below_lt2_warns():
    """The real incident: T-pace reps carrying the 4-8 km HM-pace band."""
    findings = check_hr_band_matches_intensity(
        [_run("Main 4x\n- T-Pace 6m 4:06/km Pace 92-97% LTHR\n- Easy 2m 75-88% LTHR")],
        _ctx(),
    )
    assert len(findings) == 1
    assert findings[0].rule_id == "R027"
    assert "92" not in findings[0].message  # the low bound is not the complaint
    assert "97% LTHR" in findings[0].message


def test_r027_threshold_rep_at_lt2_is_clean():
    findings = check_hr_band_matches_intensity(
        [_run("Main 4x\n- T-Pace 6m 4:06/km Pace 95-100% LTHR\n- Easy 2m 75-88% LTHR")],
        _ctx(),
    )
    assert findings == []


def test_r027_race_pace_block_at_lt2_warns():
    """The mirror error — a race-pace block invited to chase race HR."""
    findings = check_hr_band_matches_intensity(
        [_run("Main\n- HM-Pace 10m 4:13/km Pace 95-100% LTHR")], _ctx()
    )
    assert len(findings) == 1
    assert findings[0].rule_id == "R027"
    assert "above race pace" in findings[0].message


def test_r027_race_pace_block_inside_its_duration_band_is_clean():
    findings = check_hr_band_matches_intensity(
        [_run("Main\n- HM-Pace 10m 4:13/km Pace 88-93% LTHR")], _ctx()
    )
    assert findings == []


def test_r027_ignores_steps_it_cannot_classify():
    """Recovery jogs and warm-ups carry %LTHR bands too and are none of R027's
    business — the rule only speaks about steps that name their intensity."""
    findings = check_hr_band_matches_intensity(
        [_run("Warmup\n- Easy 13m 72-84% LTHR\n- Build 2m 4:20/km Pace 75-88% LTHR")],
        _ctx(),
    )
    assert findings == []
