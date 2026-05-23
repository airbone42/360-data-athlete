"""Tests for validate_plan.py R009 — Weekly Hard-Reize cap."""
from __future__ import annotations

import sys
from pathlib import Path

# Make the scripts/ directory importable.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    check_weekly_hardreize_cap,
)


BALANCE_RUN_DONE_RIDE_OPEN = (
    "Hard-stimuli balance (rolling 7d 2026-05-17–2026-05-23, "
    "2-stimuli strategy per training_paradigms.md §93–96):\n"
    "✓ Run threshold/VO2max: 2026-05-19 \"Threshold 5×6 Z4\" (Z4+Z5 21 min)\n"
    "⚠️ Bike VO2max: open"
)

BALANCE_BOTH_OPEN = (
    "Hard-stimuli balance (rolling 7d):\n"
    "⚠️ Run threshold/VO2max: open\n"
    "⚠️ Bike VO2max: open"
)

BALANCE_RIDE_DONE_RUN_OPEN = (
    "Hard-stimuli balance (rolling 7d):\n"
    "⚠️ Run threshold/VO2max: open\n"
    "✓ Bike VO2max: 2026-05-21 \"Rønnestad 30/15\" (Z4+Z5 18 min)"
)


def _ctx(balance: str = "", athlete_status: str = "", training_paradigms: str = "") -> Context:
    return Context(
        target_date="2026-05-23",
        athlete_status=athlete_status,
        training_paradigms=training_paradigms,
        weekly_hard_reize_balance=balance,
    )


def _run_z4_workout() -> dict:
    return {
        "type": "Run",
        "name": "Race-Quality Z4",
        "tags": ["run", "intervals"],
        "duration_min": 62,
        "intervals_icu": "Warmup\nMain 5x\n- 5m Z4 HR\n- 2m30s Z2 HR\nCool-down",
        "coaching_notes": "",
    }


def _run_z2_workout() -> dict:
    return {
        "type": "Run",
        "name": "Easy Z2",
        "tags": ["run"],
        "duration_min": 60,
        "intervals_icu": "Warmup\n- 50m Z2 HR\nCool-down",
        "coaching_notes": "",
    }


def _ride_z4_workout() -> dict:
    return {
        "type": "Ride",
        "name": "VO2max Indoor",
        "tags": ["ride", "intervals"],
        "duration_min": 50,
        "intervals_icu": "Warmup\nMain 5x\n- 5m Z4 HR\n- 2m30s Z2 HR\nCool-down",
        "coaching_notes": "",
    }


# ─── Triggering cases ────────────────────────────────────────────────────

def test_r009_fires_for_second_run_hardreiz_in_week():
    """Run-Threshold already done this week + planned Z4 Run → ERROR."""
    findings = check_weekly_hardreize_cap(
        [_run_z4_workout()], _ctx(BALANCE_RUN_DONE_RIDE_OPEN)
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R009"
    assert f.severity == "ERROR"
    assert "Second Run Hard-Reiz" in f.message


def test_r009_fires_for_second_ride_hardreiz_in_week():
    """Bike-VO2max done + planned Z4 Ride → ERROR."""
    findings = check_weekly_hardreize_cap(
        [_ride_z4_workout()], _ctx(BALANCE_RIDE_DONE_RUN_OPEN)
    )
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"
    assert "Second Ride Hard-Reiz" in findings[0].message


# ─── Non-triggering cases ────────────────────────────────────────────────

def test_r009_silent_on_easy_z2_run():
    """Run-Threshold done, but today is Z2 Easy — no finding."""
    findings = check_weekly_hardreize_cap(
        [_run_z2_workout()], _ctx(BALANCE_RUN_DONE_RIDE_OPEN)
    )
    assert findings == []


def test_r009_silent_when_balance_empty():
    """Athletes without Hard-Reize strategy → balance empty → rule opt-in."""
    findings = check_weekly_hardreize_cap(
        [_run_z4_workout()], _ctx("")
    )
    assert findings == []


def test_r009_silent_when_slot_still_open():
    """Both Hard-Reize-Slots open → planned Z4 is the first slot, not the second."""
    findings = check_weekly_hardreize_cap(
        [_run_z4_workout()], _ctx(BALANCE_BOTH_OPEN)
    )
    assert findings == []


def test_r009_silent_on_cross_system_no_double():
    """Run-Threshold done, planned Z4 Ride → cross-training, no conflict."""
    findings = check_weekly_hardreize_cap(
        [_ride_z4_workout()], _ctx(BALANCE_RUN_DONE_RIDE_OPEN)
    )
    assert findings == []


# ─── Taper override ──────────────────────────────────────────────────────

def test_r009_silent_when_taper_active_in_athlete_status():
    """Active taper window in athlete_status → race-spec work waived."""
    findings = check_weekly_hardreize_cap(
        [_run_z4_workout()],
        _ctx(BALANCE_RUN_DONE_RIDE_OPEN, athlete_status="Taper active until race day."),
    )
    assert findings == []


def test_r009_silent_when_race_week_active_in_coaching_notes():
    """Per-workout taper acknowledgment in coaching_notes → no finding."""
    w = _run_z4_workout()
    w["coaching_notes"] = "Race-week active — D-3 sharpening."
    findings = check_weekly_hardreize_cap([w], _ctx(BALANCE_RUN_DONE_RIDE_OPEN))
    assert findings == []
