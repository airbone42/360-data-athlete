"""Tests for validate_plan.py R015 — Interval-recovery may not be press_lap."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    check_intervals_repeat_press_lap,
)


def _wo(intervals_icu: str, name: str = "Test") -> dict:
    return {
        "type": "Run",
        "name": name,
        "tags": ["run"],
        "intervals_icu": intervals_icu,
    }


CTX = Context(target_date="2026-05-23")


# ─── Triggering cases ────────────────────────────────────────────────────

def test_r015_fires_on_press_lap_in_repeat_recovery():
    icu = "\n".join([
        "Warmup",
        "- Easy 10m press lap",
        "",
        "Steigerungen 4x",
        "- Stride 20s 90%",
        "- Easy 75s press lap",
        "",
        "Cool-down",
        "- Cool-down 10m press lap",
    ])
    findings = check_intervals_repeat_press_lap([_wo(icu)], CTX)
    assert len(findings) == 1
    assert findings[0].rule_id == "R015"
    assert findings[0].severity == "ERROR"
    assert "Steigerungen 4x" in findings[0].message
    assert "press_lap" in findings[0].message.lower() or "press lap" in findings[0].message.lower()


def test_r015_fires_on_press_lap_in_main_block():
    icu = "\n".join([
        "Main 5x",
        "- 5m Z4 HR",
        "- 2m30s press lap",
    ])
    findings = check_intervals_repeat_press_lap([_wo(icu)], CTX)
    assert len(findings) == 1
    assert findings[0].rule_id == "R015"


def test_r015_reports_multiple_violations_in_one_block():
    icu = "\n".join([
        "Main 3x",
        "- 5m Z4 HR press lap",
        "- 2m press lap",
    ])
    findings = check_intervals_repeat_press_lap([_wo(icu)], CTX)
    assert len(findings) == 2


# ─── Non-triggering cases ────────────────────────────────────────────────

def test_r015_silent_when_recovery_uses_zone_target():
    icu = "\n".join([
        "Warmup",
        "- Easy 10m press lap",
        "",
        "Steigerungen 4x",
        "- Stride 20s 90%",
        "- Easy 75s Z1 HR",
        "",
        "Cool-down",
        "- Cool-down 10m press lap",
    ])
    findings = check_intervals_repeat_press_lap([_wo(icu)], CTX)
    assert findings == []


def test_r015_silent_when_only_warmup_cooldown_use_press_lap():
    """Press_lap is correct for WU/CD outside any repeat block."""
    icu = "\n".join([
        "Warmup",
        "- Hip Flexor 60s",
        "- Easy 10m press lap",
        "",
        "Main",
        "- 65m Z2 HR",
        "",
        "Cool-down",
        "- Cool-down 10m press lap",
    ])
    findings = check_intervals_repeat_press_lap([_wo(icu)], CTX)
    assert findings == []


def test_r015_silent_when_no_intervals_icu():
    findings = check_intervals_repeat_press_lap(
        [{"type": "Run", "name": "Z2", "intervals_icu": ""}], CTX
    )
    assert findings == []


def test_r015_detects_press_lap_after_blank_line_between_header_and_body():
    """R013 catches the blank-line-after-header bug; R015 still inspects items
    if they exist, so a press_lap below ALSO surfaces."""
    icu = "\n".join([
        "Steigerungen 4x",
        "",
        "- Stride 20s 90%",
        "- Easy 75s press lap",
    ])
    findings = check_intervals_repeat_press_lap([_wo(icu)], CTX)
    assert len(findings) == 1
    assert findings[0].rule_id == "R015"
