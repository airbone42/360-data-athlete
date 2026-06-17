"""Tests for validate_plan.py R014 — easy-run conservatism guard.

Primary anchor: the per-phase easy-run band in competition_plan.md keyed by
current CTL. An easy run below the phase-band floor with no documented
recovery trigger is an ERROR. Fallback (no phase table / CTL offline): the
rolling easy-run median heuristic (WARNING).

Motivating case (dates synthetic): an easy run was set to 45 min on a
green-physiology day while the Aufbau-II phase floor is 60 min; the
median-only guard computed 86 % of the recent median and stayed silent, so
a sub-phase-floor run passed unflagged.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    check_easy_run_conservatism,
    _easy_run_phase_floor,
)

# Minimal phase-band table mirroring competition_plan.md "Lauf-Dauer-Logik".
PLAN = (
    "| Phase | Easy/Z2-Lauf | Long Run | Wochen-Volumen-Korridor |\n"
    "| Aufbau I (CTL 17–28) | 55–70 min | progressiv 90 → 110 min | ~45–60 km |\n"
    "| Aufbau II (CTL 28–38) | 60–75 min | 110 → 130 min | ~55–70 km |\n"
    "| Wettkampfphase (CTL 38–45) | 60–75 min | 110–130 min | ~65–80 km |\n"
)


def _ctx(ctl: float | None = 28.9, plan: str = PLAN, activities=None) -> Context:
    return Context(
        target_date="2025-06-17",
        competition_plan=plan,
        ctl=ctl,
        recent_activities=activities or [],
    )


def _easy_run(duration_min: int, **kw) -> dict:
    w = {
        "type": "Run",
        "name": "Easy-Z2 Waldweg",
        "tags": ["run"],
        "workout_type": "EASY",
        "duration_min": duration_min,
    }
    w.update(kw)
    return w


# ── Phase-floor parser ───────────────────────────────────────────────────

def test_phase_floor_maps_ctl_to_band():
    assert _easy_run_phase_floor(_ctx(ctl=28.9)) == 60   # Aufbau II
    assert _easy_run_phase_floor(_ctx(ctl=20.0)) == 55   # Aufbau I
    assert _easy_run_phase_floor(_ctx(ctl=40.0)) == 60   # Wettkampf
    assert _easy_run_phase_floor(_ctx(ctl=28.0)) == 60   # boundary → upper phase


def test_phase_floor_none_without_ctl_or_plan():
    assert _easy_run_phase_floor(_ctx(ctl=None)) is None
    assert _easy_run_phase_floor(_ctx(plan="")) is None


# ── Primary anchor (ERROR) ───────────────────────────────────────────────

def test_r014_errors_below_phase_floor():
    findings = check_easy_run_conservatism([_easy_run(45)], _ctx(ctl=28.9))
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R014"
    assert f.severity == "ERROR"
    assert "phase floor" in f.message


def test_r014_silent_at_or_above_phase_floor():
    assert check_easy_run_conservatism([_easy_run(60)], _ctx(ctl=28.9)) == []
    assert check_easy_run_conservatism([_easy_run(70)], _ctx(ctl=28.9)) == []


def test_r014_phase_floor_exempt_with_documented_trigger():
    w = _easy_run(45, description="Recovery week active — Volumen reduziert.")
    assert check_easy_run_conservatism([w], _ctx(ctl=28.9)) == []


def test_r014_phase_floor_exempt_for_indoor_and_brick():
    assert check_easy_run_conservatism([_easy_run(40, indoor=True)], _ctx(ctl=28.9)) == []
    brick = _easy_run(40, name="Brick Bike→Run")
    assert check_easy_run_conservatism([brick], _ctx(ctl=28.9)) == []


def test_r014_phase_floor_exempt_on_achilles_morning_stiffness():
    w = _easy_run(40, description="Achilles-Morgensteifigkeit → kurz halten, Weichboden.")
    assert check_easy_run_conservatism([w], _ctx(ctl=28.9)) == []


# ── Fallback anchor (WARNING) when no phase band / CTL ──────────────────────

def test_r014_falls_back_to_median_without_ctl():
    acts = [
        {"type": "Run", "duration_min": 60, "training_load": 40},
        {"type": "Run", "duration_min": 60, "training_load": 40},
        {"type": "Run", "duration_min": 60, "training_load": 40},
    ]
    findings = check_easy_run_conservatism(
        [_easy_run(35)], _ctx(ctl=None, activities=acts)
    )
    assert len(findings) == 1
    assert findings[0].severity == "WARNING"
    assert "median" in findings[0].message


def test_r014_silent_when_no_easy_run():
    quality = {"type": "Run", "name": "Threshold", "workout_type": "INTERVALS",
               "duration_min": 20}
    assert check_easy_run_conservatism([quality], _ctx(ctl=28.9)) == []
