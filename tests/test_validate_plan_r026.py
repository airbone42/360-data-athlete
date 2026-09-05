"""Tests for validate_plan.py R026 — executed load must be asked for.

The bug this guards is a closed loop rather than a typo. The plan writes the
target load into the description; that same description is what gets parsed
back after the session; and the athlete answers with a bare RPE. Nothing in
the loop ever establishes what was actually lifted, so the planned figure is
booked as the result — indistinguishable from a real measurement in the
record.

Anchor cases: a unilateral squat planned at 14 kg and executed at 23 kg was
filed as "14 kg @ RPE 8"; separately an auto-sync filed 38 kg for a carry that
had run at ~33 kg. Both were corrected by the athlete days later, not by the
system.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pytest  # noqa: E402

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    check_load_report_requested,
)

CTX = Context(target_date="2026-09-05")

_LOADED_RPE_ONLY = """HAUPTTEIL

Back Squat: 3x5 @ 38kg | RPE 6 | Rippen unten

Bulgarian Split Squat: 3x6 @ 14kg | RPE 7-8 | bei RPE 8 beenden

FEEDBACK: Bitte RPE je Übung melden."""


def test_loaded_session_asking_only_for_rpe_is_flagged() -> None:
    findings = check_load_report_requested(
        [{"type": "WeightTraining", "name": "Bein-Block", "description": _LOADED_RPE_ONLY}],
        CTX,
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R026"
    assert f.severity == "WARNING"
    # Both loaded exercises are named so the coach knows where to add the ask.
    assert "Back Squat" in f.message
    assert "Bulgarian Split Squat" in f.message


@pytest.mark.parametrize(
    "request_line",
    [
        "FEEDBACK: RPE je Übung und die gefahrene Last melden.",
        "FEEDBACK: RPE plus tatsächliche Last.",
        "FEEDBACK: Welche Last lag auf? Dazu RPE je Satz.",
        "FEEDBACK: RPE melden, dazu mit welchem Gewicht gefahren wurde.",
        "FEEDBACK: report RPE and the actual load",
        "FEEDBACK: RPE + weight used",
    ],
)
def test_load_request_in_any_documented_phrasing_clears_the_rule(request_line: str) -> None:
    desc = _LOADED_RPE_ONLY.replace("FEEDBACK: Bitte RPE je Übung melden.", request_line)
    findings = check_load_report_requested(
        [{"type": "WeightTraining", "name": "Bein-Block", "description": desc}], CTX
    )
    assert findings == []


def test_session_that_asks_for_nothing_is_also_flagged() -> None:
    """The no-feedback case is the worse half of the pair, not a separate one.

    The carry incident (38 kg filed for a set run at ~33 kg) had exactly this
    shape: loads in the description, nothing asked back, planned figure booked
    unopposed. Scoping the rule to sessions that already request an RPE would
    have let it through.
    """
    desc = "HAUPTTEIL\n\nFarmer Hold KB: 3x40s @ 33kg | RPE 7"
    findings = check_load_report_requested(
        [{"type": "WeightTraining", "name": "Grip-Block", "description": desc}], CTX
    )
    assert len(findings) == 1
    assert "Farmer Hold KB" in findings[0].message


def test_unloaded_session_is_not_flagged() -> None:
    desc = "Side Plank mit Hüft-Abduktion: 3x45s | RPE 7\n\nFEEDBACK: RPE melden."
    findings = check_load_report_requested(
        [{"type": "Workout", "name": "Schicht D", "description": desc}], CTX
    )
    assert findings == []


@pytest.mark.parametrize("wtype", ["Run", "Ride", "VirtualRun", "VirtualRide"])
def test_endurance_workouts_are_out_of_scope(wtype: str) -> None:
    """Endurance sessions carry kg only incidentally (body weight, gear) and
    their anchor is pace/power, not a load on a bar."""
    findings = check_load_report_requested(
        [{
            "type": wtype,
            "name": "Cruise",
            "description": "Cruise 40m 200W | FEEDBACK: Kadenz und RPE melden",
        }],
        CTX,
    )
    assert findings == []


def test_multiple_workouts_are_reported_separately() -> None:
    workouts = [
        {"type": "WeightTraining", "name": "Bein-Block", "description": _LOADED_RPE_ONLY},
        {"type": "Workout", "name": "Grip-Block",
         "description": "Farmer Hold KB: 3x40s @ 33kg | RPE 7\n\nFEEDBACK: RPE melden."},
    ]
    findings = check_load_report_requested(workouts, CTX)
    assert {f.workout for f in findings} == {"Bein-Block", "Grip-Block"}


def test_rule_is_registered() -> None:
    from scripts.validate_plan import RULES  # type: ignore

    assert ("R026", check_load_report_requested) in RULES


def test_balance_work_is_out_of_scope_even_when_loaded() -> None:
    """Balance sessions carry a load as a perturbation tool, not as the anchor.

    The progression signal there is the S-rating, and the pool's own rule runs
    the other way round ("at S4+ go back to 8 kg"). A load the athlete picked
    differently surfaces in the S-value he reports, so the mis-booking loop
    this rule guards does not exist — firing would put a warning on every
    balance push.
    """
    desc = (
        "Star Reach + KB Last kontralateral: 3x3 Richtungen/Seite | KB 8kg | Ziel: S2-S3\n\n"
        "FEEDBACK: S-Wert je Übung."
    )
    findings = check_load_report_requested(
        [{"type": "Workout", "name": "Balance", "tags": ["balance"], "description": desc}],
        CTX,
    )
    assert findings == []
