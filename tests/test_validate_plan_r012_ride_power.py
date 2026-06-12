"""Tests for validate_plan.py R012 — Ride steps need a POWER target.

A Ride step whose only target is HR/pace (`Z1 HR`, `% LTHR`, `% HR`)
passes intervals.icu but Wahoo's smart-trainer plan upload rejects it
with `422: each interval that is not of type 'repeat' must have a valid
'targets' array`. The validator must flag HR-only Ride steps as ERROR so
the 422 cannot recur. Details in
`framework/research/intervals-icu-workout-syntax.md` Trap B.
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


def _ride(intervals_icu: str, name: str = "Rad-VO2max") -> dict:
    return {
        "type": "Ride",
        "name": name,
        "tags": ["ride", "intervals"],
        "intervals_icu": intervals_icu,
    }


CTX = Context(target_date="2026-06-12")


# ─── Triggering cases (HR-only Ride steps → ERROR) ───────────────────────

def test_r012_fires_on_hr_only_warmup_on_ride():
    icu = "\n".join([
        "Warmup",
        "- Warmup 9m Z1 HR 90-100rpm",
        "",
        "Set 1 8x",
        "- On 30s 360W",
        "- Off 15s 185W",
    ])
    findings = check_intervals_step_targets([_ride(icu)], CTX)
    r012 = [f for f in findings if f.rule_id == "R012"]
    assert len(r012) == 1
    assert r012[0].severity == "ERROR"
    assert "HR" in r012[0].message and "Wahoo" in r012[0].message


def test_r012_fires_on_each_hr_only_step():
    icu = "\n".join([
        "Warmup",
        "- Warmup 9m Z1 HR 90-100rpm",
        "",
        "Set 1 8x",
        "- On 30s 360W",
        "- Off 15s 185W",
        "",
        "Set rest",
        "- Recovery 3m Z1 HR",
        "",
        "Cool-down",
        "- Cool-down 8m Z1 HR 85-90rpm",
    ])
    findings = check_intervals_step_targets([_ride(icu)], CTX)
    r012 = [f for f in findings if f.rule_id == "R012"]
    assert len(r012) == 3  # warmup, recovery, cooldown


def test_r012_fires_on_percent_lthr_only_on_ride():
    icu = "\n".join([
        "Warmup",
        "- Warmup 10m 60-70% LTHR",
        "",
        "Main 4x",
        "- On 30s 360W",
        "- Off 15s 185W",
    ])
    findings = check_intervals_step_targets([_ride(icu)], CTX)
    r012 = [f for f in findings if f.rule_id == "R012"]
    assert len(r012) == 1
    assert r012[0].severity == "ERROR"


# ─── Non-triggering cases (power target present → clean) ─────────────────

def test_r012_silent_on_all_watt_ride():
    icu = "\n".join([
        "Warmup",
        "- Warmup 9m 150W 90-100rpm",
        "- Surge 20s 340W",
        "- Easy 40s 150W",
        "",
        "Set 1 8x",
        "- On 30s 360W",
        "- Off 15s 185W",
        "",
        "Set rest",
        "- Recovery 3m 150W",
        "",
        "Cool-down",
        "- Cool-down 8m 130W 85-90rpm",
    ])
    findings = check_intervals_step_targets([_ride(icu)], CTX)
    assert [f for f in findings if f.rule_id == "R012"] == []


def test_r012_silent_on_bare_power_zone_ride():
    # bare `Zn` on a Ride = power zone — Wahoo-valid
    icu = "\n".join([
        "Warmup",
        "- Warmup 10m Z1",
        "",
        "Main 4x",
        "- On 4m Z5",
        "- Off 4m Z1",
    ])
    findings = check_intervals_step_targets([_ride(icu)], CTX)
    assert [f for f in findings if f.rule_id == "R012"] == []


def test_r012_silent_on_percent_ftp_ride():
    icu = "\n".join([
        "Warmup",
        "- Warmup 10m 55% FTP",
        "",
        "Main 3x",
        "- On 8m 88-94% FTP",
        "- Off 4m 50% FTP",
    ])
    findings = check_intervals_step_targets([_ride(icu)], CTX)
    assert [f for f in findings if f.rule_id == "R012"] == []


def test_r012_ride_hr_check_does_not_apply_to_run():
    # `Z1 HR` is correct on a Run — must NOT trigger the Ride power rule
    run = {
        "type": "Run",
        "name": "Easy",
        "tags": ["run"],
        "intervals_icu": "\n".join([
            "Warmup",
            "- Warmup 10m press lap",
            "",
            "Main",
            "- Easy 30m Z2 HR",
        ]),
    }
    findings = check_intervals_step_targets([run], CTX)
    assert [f for f in findings if f.rule_id == "R012"] == []
