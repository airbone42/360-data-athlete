"""Tests for analyse_video.py anti-seeding guard + grounding-block prompt.

Motivating case: a strength form-check was called with ``--context`` that
described the *execution* ("KB Goblet frontal gehalten"). The model
confirmed that hold instead of reading it from the video (confirmation
bias), reporting a frontal hold when the athlete actually held the
kettlebell at the side. Two defenses are tested here:

1. ``_warn_on_seeded_context`` flags execution-describing context (so the
   operator does not seed the analysis) while leaving legitimate
   injury/restriction/sport-profile context alone.
2. ``_build_user_prompt`` forces a "Was ich sehe" grounding block and the
   explicit "nicht sicher erkennbar" rule into both strength and run
   response templates.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.analyse_video import (  # type: ignore  # noqa: E402
    _build_user_prompt,
    _warn_on_seeded_context,
)


def test_seeding_guard_flags_execution_terms() -> None:
    assert _warn_on_seeded_context("KB Goblet 12 kg frontal gehalten")
    assert _warn_on_seeded_context("vorderes Bein rechts, Tempo 3-0-X")
    assert _warn_on_seeded_context("Gewicht kontralateral zum Standbein")


def test_seeding_guard_ignores_injury_and_profile_context() -> None:
    # Restrictions / injuries / sport profile are legitimate context.
    assert (
        _warn_on_seeded_context(
            "Masters-Laeufer, rechtes Sprunggelenk anterolaterales Impingement, "
            "LWS leicht gereizt"
        )
        == []
    )
    assert _warn_on_seeded_context("") == []


def test_strength_prompt_has_grounding_block() -> None:
    p = _build_user_prompt("Bulgarian Split Squat", "", "", "", run_mode=False)
    assert "Was ich sehe" in p
    assert "nicht sicher erkennbar" in p


def test_run_prompt_has_grounding_block() -> None:
    p = _build_user_prompt("Laufen Sagittal", "", "", "", run_mode=True)
    assert "Was ich sehe" in p
    assert "nicht sicher erkennbar" in p
