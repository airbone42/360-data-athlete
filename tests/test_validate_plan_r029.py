"""Tests for validate_plan.py R029 — feedback question must name a prescribed load.

The sibling of R026. R026 asks whether the session requests the executed load
at all; R029 asks whether it requests the *right* one. The incident behind the
rule: a carry was reset from 35 kg to 33 kg before the push and the feedback
line of the same description kept asking about "die 35 kg", so the athlete's
bare "rpe 6" could have been booked as the reading of a step that never ran.
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
    check_feedback_load_matches_prescription,
)


def _ctx() -> Context:
    return Context(target_date="2026-09-16")


def _strength(description: str, name: str = "Griff-Block") -> dict:
    return {
        "type": "WeightTraining",
        "name": name,
        "tags": ["ninja", "grip"],
        "description": description,
    }


STALE_FEEDBACK = """MAIN

Farmer's Hold KH einarmig: 3x40s/Seite @ 33kg | RPE 6-7 | Anker bestaetigen
Wrist Curls: 3x10/Seite @ 11,5kg | RPE 5-6 erwartet

FEEDBACK: RPE je Uebung, die gefahrene Last, und ob sich die 35 kg links/rechts unterschiedlich angefuehlt haben."""

CONSISTENT_FEEDBACK = """MAIN

Farmer's Hold KH einarmig: 3x40s/Seite @ 33kg | RPE 6-7 | Anker bestaetigen
Wrist Curls: 3x10/Seite @ 11,5kg | RPE 5-6 erwartet

FEEDBACK: RPE je Uebung, die gefahrene Last, und ob sich die 33 kg links/rechts unterschiedlich angefuehlt haben."""

NO_LOAD_IN_FEEDBACK = """MAIN

Farmer's Hold KH einarmig: 3x40s/Seite @ 33kg | RPE 6-7

FEEDBACK: RPE je Uebung und die tatsaechlich gefahrene Last."""

NO_FEEDBACK_BLOCK = """MAIN

Farmer's Hold KH einarmig: 3x40s/Seite @ 33kg | RPE 6-7
"""


def test_stale_load_in_feedback_is_flagged() -> None:
    findings = check_feedback_load_matches_prescription(
        [_strength(STALE_FEEDBACK)], _ctx()
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R029"
    assert f.severity == "WARNING"
    assert "35 kg" in f.message
    # The prescribed loads are named so the coach sees both sides at once.
    assert "33 kg" in f.message
    assert "11.5 kg" in f.message


def test_matching_load_passes() -> None:
    assert (
        check_feedback_load_matches_prescription(
            [_strength(CONSISTENT_FEEDBACK)], _ctx()
        )
        == []
    )


def test_feedback_without_kg_figure_passes() -> None:
    """Asking for "die gefahrene Last" names no figure — nothing to compare."""
    assert (
        check_feedback_load_matches_prescription(
            [_strength(NO_LOAD_IN_FEEDBACK)], _ctx()
        )
        == []
    )


def test_missing_feedback_block_is_r026s_finding_not_r029s() -> None:
    assert (
        check_feedback_load_matches_prescription(
            [_strength(NO_FEEDBACK_BLOCK)], _ctx()
        )
        == []
    )


def test_decimal_comma_and_missing_space_are_the_same_load() -> None:
    """`11,5 kg`, `11.5kg` and `11,50 kg` are one load written three ways.

    Comparing raw strings would report a mismatch that does not exist, which
    is the fastest way to teach a coach to ignore a rule.
    """
    desc = """MAIN

Wrist Curls: 3x10/Seite @ 11,5kg | RPE 5-6

FEEDBACK: RPE, und ob die 11.50 kg links wie rechts lagen."""
    assert check_feedback_load_matches_prescription([_strength(desc)], _ctx()) == []


def test_multiline_feedback_block_is_read_whole() -> None:
    """A question written as a list keeps going after the first line."""
    desc = """MAIN

Farmer's Hold: 3x40s/Seite @ 33kg | RPE 6-7

FEEDBACK
- RPE je Uebung
- ob die 35 kg links/rechts unterschiedlich lagen"""
    findings = check_feedback_load_matches_prescription([_strength(desc)], _ctx())
    assert len(findings) == 1
    assert "35 kg" in findings[0].message


def test_blank_line_closes_the_feedback_block() -> None:
    """A load below a blank line is a prescription again, not part of the question.

    Without this the rule would read the whole tail of a description as one
    question and stop distinguishing the two halves it exists to compare.
    """
    desc = """MAIN

Farmer's Hold: 3x40s/Seite @ 33kg | RPE 6-7

FEEDBACK: RPE je Uebung.

Suitcase-Aufbausatz: 1x20s/Seite @ 20kg"""
    assert check_feedback_load_matches_prescription([_strength(desc)], _ctx()) == []


def test_endurance_and_sauna_are_out_of_scope() -> None:
    run = {
        "type": "Run",
        "name": "Renntempo",
        "tags": ["run", "intervals"],
        "description": "FEEDBACK: lief die Weste mit 5 kg gut?",
    }
    sauna = {
        "type": "Workout",
        "name": "Sauna",
        "tags": ["sauna"],
        "description": "FEEDBACK: wie waren die 90 kg auf der Waage danach?",
    }
    assert check_feedback_load_matches_prescription([run, sauna], _ctx()) == []


def test_no_prescribed_load_at_all_is_reported_explicitly() -> None:
    """The worse shape: the question invents a load the session never carried."""
    desc = """MAIN

Dead Hang: 3x20s, 2 passiv + 1 aktiv | RPE 6-7

FEEDBACK: RPE, und wie lagen die 12,5 kg?"""
    findings = check_feedback_load_matches_prescription([_strength(desc)], _ctx())
    assert len(findings) == 1
    assert "12.5 kg" in findings[0].message
    assert "no load on any exercise line" in findings[0].message


def test_rule_is_registered() -> None:
    from scripts.validate_plan import RULES  # type: ignore

    assert ("R029", check_feedback_load_matches_prescription) in RULES
