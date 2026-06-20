"""Tests for validate_plan.py R012 — bare percent on a Run step is %FTP junk.

A Run/VirtualRun step with a unit-less percent (`- Stride 20s 95%`) is
silently parsed by intervals.icu as a %FTP POWER target. Runs have no
power zone, so it lands as a meaningless watt goal on the watch. The
validator must flag it as ERROR. Strides take NO target — the effort cue
(Mile-/1km race pace) belongs in the workout description. The explicit
percent forms (`% LTHR`, `% HR`, `% Pace`, `% FTP`) stay valid; bare `%`
is valid only on a Ride (= %FTP power). Convention:
`framework/agents/specialist-endurance.md` ("Stride/surge ≠ race-pace").
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    check_intervals_step_targets,
)


def _run(intervals_icu: str, name: str = "Test") -> dict:
    return {
        "type": "Run",
        "name": name,
        "tags": ["run"],
        "intervals_icu": intervals_icu,
    }


def _ride(intervals_icu: str, name: str = "Test") -> dict:
    return {
        "type": "Ride",
        "name": name,
        "tags": ["ride"],
        "intervals_icu": intervals_icu,
    }


CTX = Context(target_date="2026-06-20")


def _r012(findings):
    return [f for f in findings if f.rule_id == "R012"]


# ─── Triggering cases (bare percent on Run → ERROR) ──────────────────────

def test_r012_fires_on_bare_percent_stride():
    icu = "\n".join(["Strides 4x", "- Stride 20s 95%", "- Easy 90s Z1 HR"])
    findings = _r012(check_intervals_step_targets([_run(icu)], CTX))
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"
    assert "bare percent" in findings[0].message.lower()


def test_r012_fires_on_bare_percent_range():
    icu = "\n".join(["Strides 4x", "- Stride 20s 80-90%", "- Easy 90s Z1 HR"])
    findings = _r012(check_intervals_step_targets([_run(icu)], CTX))
    assert any(f.severity == "ERROR" for f in findings)


# ─── Non-triggering cases ────────────────────────────────────────────────

def test_r012_silent_on_plain_timed_stride():
    icu = "\n".join(["Strides 4x", "- Stride 20s", "- Easy 90s Z1 HR"])
    findings = _r012(check_intervals_step_targets([_run(icu)], CTX))
    assert findings == []


def test_r012_silent_on_explicit_lthr_percent():
    icu = "\n".join(["Main", "- HM-Pace 10m 4:10/km Pace 90-94% LTHR"])
    findings = _r012(check_intervals_step_targets([_run(icu)], CTX))
    assert findings == []


def test_r012_silent_on_threshold_lthr_range():
    icu = "\n".join(["Main 3x", "- Threshold 8m 95-99% LTHR", "- Easy 3m Z1 HR"])
    findings = _r012(check_intervals_step_targets([_run(icu)], CTX))
    assert findings == []


def test_r012_bare_percent_valid_on_ride():
    """Bare percent = %FTP power, which IS valid on a Ride — must not fire
    the Run bare-percent catch."""
    icu = "\n".join(["Main 3x", "- Spike 60s 90%", "- Easy 2m 50%"])
    findings = _r012(check_intervals_step_targets([_ride(icu)], CTX))
    # No bare-percent-on-Run finding; any Ride findings would be about power,
    # not this rule. Assert none mention the Run bare-percent message.
    assert not any("bare percent" in f.message.lower() for f in findings)
