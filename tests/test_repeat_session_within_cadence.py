"""Tests for validator rule R028 — catch-up blocks must not re-run yesterday.

The pattern under test is a notation failure, not a dosing failure. A single
exercise drops out of a session; the replacement slot gets written as a
*session* ("the missing item runs in the <session> on <date>"), because a
session name is the only thing the slot notation can express. The next
planning cycle reads that as "a <session> runs on <date>" and rebuilds the
whole roster — so a block whose cadence is every second day runs on
consecutive days at full volume, and no single decision caused it.

Nothing else in the rule set can see this: the tag-level due-warnings answer
"did a <tag> session happen", not "which roster items are still owed", and
R024 only asks whether a tagged pillar is *covered* — a full repeat covers it
perfectly. R016 compares numeric anchors, not occurrence.

All dates are synthetic 2025 values on purpose — real training dates in a
public test suite would leak the maintainer's block schedule.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_plan import (  # noqa: E402
    Context,
    check_repeat_session_within_cadence,
)

TODAY = "2025-03-12"
YESTERDAY = "2025-03-11"


def _executed(description: str, day: str = YESTERDAY, type_: str = "WeightTraining") -> dict:
    return {
        "date": day,
        "type": type_,
        "name": "Core block",
        "duration_min": 40,
        "training_load": None,
        "description": description,
    }


def _planned(description: str, type_: str = "WeightTraining", **kw) -> dict:
    w = {"type": type_, "name": "Core block", "description": description}
    w.update(kw)
    return w


def _ctx(activities: list[dict]) -> Context:
    return Context(target_date=TODAY, recent_activities=activities)


# A HAUPTTEIL marker is required — _extract_exercises_seen deliberately ignores
# warm-up content so a drill that legitimately repeats daily is not an overlap.
FULL_SESSION = """WARM-UP
Beckenkippen 10x

HAUPTTEIL
Side Plank mit Hueft-Abduktion: 3x45 s/Seite
Dead Bug kontralateral: 3x12/Seite
Pallof Hold: 3x20 s/Seite
"""

CATCH_UP_ONLY = """WARM-UP
Beckenkippen 10x

HAUPTTEIL
Stir-the-Pot: 3x9/Richtung
McGill Curl-up: 6/4/2 je Seite
"""

REPEAT_PLUS_CATCH_UP = """WARM-UP
Beckenkippen 10x

HAUPTTEIL
Stir-the-Pot: 3x9/Richtung
Side Plank mit Hueft-Abduktion: 3x45 s/Seite
Pallof Hold: 3x20 s/Seite
"""


def test_catch_up_without_overlap_is_silent():
    """The legitimate case: only the items that did NOT run yesterday."""
    ctx = _ctx([_executed(FULL_SESSION)])
    assert check_repeat_session_within_cadence([_planned(CATCH_UP_ONLY)], ctx) == []


def test_overlap_with_yesterday_is_flagged():
    """The defect: a 'catch-up' that re-runs roster items from yesterday."""
    ctx = _ctx([_executed(FULL_SESSION)])
    findings = check_repeat_session_within_cadence([_planned(REPEAT_PLUS_CATCH_UP)], ctx)
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R028"
    assert f.severity == "WARNING"
    assert YESTERDAY in f.message
    # The overlapping exercises are named, so the reason for a deliberate
    # repeat can be checked against them rather than taken on trust.
    assert "Side Plank" in f.message
    assert "Stir-the-Pot" not in f.message


def test_prose_cannot_clear_the_finding():
    """No keyword exemption — that is the failure mode, not the fix.

    The canonical incident was a coach explaining the repeat away in the
    coaching note ('catch-up booking, cadence is deliberate'). A keyword
    escape hatch would reproduce it exactly, so the only way to clear R028
    is to remove the overlap.
    """
    ctx = _ctx([_executed(FULL_SESSION)])
    w = _planned(
        REPEAT_PLUS_CATCH_UP,
        coaching_notes=(
            "Nachzieh-Buchung, keine Kadenz-Verletzung — deliberate catch-up, "
            "cadence is intentional, deload, taper, recovery week"
        ),
    )
    assert len(check_repeat_session_within_cadence([w], ctx)) == 1


def test_two_days_back_is_not_an_overlap():
    """Only the immediately preceding day counts — cadence, not history."""
    ctx = _ctx([_executed(FULL_SESSION, day="2025-03-10")])
    assert check_repeat_session_within_cadence([_planned(REPEAT_PLUS_CATCH_UP)], ctx) == []


def test_warm_up_repetition_is_not_an_overlap():
    """A drill in the warm-up may repeat daily by design."""
    executed = _executed(
        """WARM-UP
Side Plank mit Hueft-Abduktion: 2x20 s/Seite

HAUPTTEIL
Dead Bug kontralateral: 3x12/Seite
"""
    )
    planned = _planned(
        """WARM-UP
Side Plank mit Hueft-Abduktion: 2x20 s/Seite

HAUPTTEIL
Stir-the-Pot: 3x9/Richtung
"""
    )
    assert check_repeat_session_within_cadence([planned], _ctx([executed])) == []


def test_endurance_workout_is_out_of_scope():
    ctx = _ctx([_executed(FULL_SESSION)])
    w = _planned(REPEAT_PLUS_CATCH_UP, type_="Run")
    assert check_repeat_session_within_cadence([w], ctx) == []


def test_tag_removal_does_not_dodge_the_rule():
    """Keyed on content, not tags.

    R024 can be satisfied by dropping the pillar tag; R028 must not be, or the
    same plan slips through by relabelling instead of by changing.
    """
    ctx = _ctx([_executed(FULL_SESSION)])
    w = _planned(REPEAT_PLUS_CATCH_UP, tags=[])
    assert len(check_repeat_session_within_cadence([w], ctx)) == 1


def test_no_history_is_silent():
    assert check_repeat_session_within_cadence([_planned(FULL_SESSION)], _ctx([])) == []


def test_yesterday_without_extractable_exercises_is_silent():
    ctx = _ctx([_executed("WARM-UP\nnothing recognisable here\n")])
    assert check_repeat_session_within_cadence([_planned(FULL_SESSION)], ctx) == []


@pytest.mark.parametrize("bad_date", ["not-a-date", ""])
def test_unparseable_target_date_is_silent(bad_date: str):
    ctx = Context(target_date=bad_date, recent_activities=[_executed(FULL_SESSION)])
    assert check_repeat_session_within_cadence([_planned(FULL_SESSION)], ctx) == []
