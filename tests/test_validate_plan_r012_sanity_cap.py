"""R012 — explicit HR sanity cap next to a real target is not a BPM target."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pytest  # noqa: E402

from scripts.validate_plan import Context, check_intervals_step_targets  # type: ignore  # noqa: E402


def _r012(wtype: str, step: str) -> list:
    w = {"type": wtype, "name": "t", "intervals_icu": f"Main\n{step}"}
    return [f for f in check_intervals_step_targets([w], Context(target_date="2026-01-01"))
            if f.rule_id == "R012"]


@pytest.mark.parametrize(
    "step",
    [
        "- Endurance 20m 160W 90rpm — HF-Deckel 131 bpm",
        "- Endurance 20m 160W — HR cap 131 bpm",
        "- Endurance 20m 160W max 131 bpm",
        "- Endurance 20m 160W <131 bpm",
    ],
)
def test_sanity_cap_on_power_step_passes(step: str) -> None:
    assert _r012("VirtualRide", step) == []


def test_sanity_cap_on_run_with_hr_target_passes() -> None:
    assert _r012("Run", "- Easy 30m Z2 HR — max 140 bpm") == []


def test_cap_without_real_target_still_errors() -> None:
    findings = _r012("Run", "- Easy 30m — max 140 bpm")
    assert [f.severity for f in findings] == ["ERROR"]


def test_bpm_range_is_never_a_cap() -> None:
    findings = _r012("VirtualRide", "- Endurance 20m 160W — 126-135 bpm")
    assert [f.severity for f in findings] == ["ERROR"]
