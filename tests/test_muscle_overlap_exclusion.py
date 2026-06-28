"""Tests for the keyword false-positive guards in the muscle-overlap recovery blocks.

The `grip_support` / `wrist_flexors` / `plyometrics` rules in
`_compute_muscle_overlap_blocks` scan activity description text for exercise
keywords. A keyword can appear in text that does NOT describe a performed
exercise:

1. a STOP / pain-criterion line ("⛔ STOP … pain on Dead Hang …"), or
2. a progression-origin note on a *different* exercise's line
   ("Scapular Pullups: 3×8 … from passive Dead Hang →").

Both must be ignored — otherwise a recovery block fires with no real load
behind it. Guards: `_line_is_exclusion` (⛔/STOP/skip markers) and
`_exercise_name_portion` (match only the name segment before the first ':').

All fixture dates are synthetic 2025 dates (Lehre 7 — no real athlete
training-diary dates in the public test suite).
"""
from __future__ import annotations

from datetime import date

from app.graphs.sub_athlete_context import context_builder as cb

_TODAY = date(2025, 3, 10)
_YESTERDAY = "2025-03-09"

_GRIP_LABEL = "Grip support"


def _act(description: str, d: str = _YESTERDAY) -> dict:
    return {"description": description, "start_date_local": f"{d}T09:00:00"}


def _has_grip_block(blocks: list[str]) -> bool:
    return any(_GRIP_LABEL in b for b in blocks)


# ── _exercise_name_portion ──────────────────────────────────────────


def test_name_portion_splits_on_colon() -> None:
    assert cb._exercise_name_portion("Dead Hang: 3x15s | RPE 6").strip() == "Dead Hang"


def test_name_portion_keyword_after_colon_excluded() -> None:
    line = "1) Scapular Pullups (haengend): 3x8 BW | from passive Dead Hang -> scap"
    assert "dead hang" not in cb._exercise_name_portion(line).lower()


def test_name_portion_no_separator_returns_whole_line() -> None:
    assert cb._exercise_name_portion("Dead Hang passive set") == "Dead Hang passive set"


# ── _line_is_exclusion ──────────────────────────────────────────────


def test_stop_criterion_line_is_excluded() -> None:
    assert cb._line_is_exclusion("⛔ STOP (shoulder): pain on Dead Hang -> abort set")


def test_real_exercise_line_is_not_excluded() -> None:
    assert not cb._line_is_exclusion("Dead Hang: 3x15s | RPE 6")


# ── false positives must NOT trigger a grip block ────────────────────


def test_stop_criterion_keyword_does_not_trigger_block() -> None:
    desc = (
        "SHOULDER HOME BLOCK A\n"
        "⛔ STOP (shoulder/tendon): warmth right, pain on Dead Hang, abort + NOTE.\n"
        "1) Scapular Pullups: 3x8 BW | 1-2s Hold\n"
    )
    blocks = cb._compute_muscle_overlap_blocks([_act(desc)], _TODAY)
    assert not _has_grip_block(blocks), blocks


def test_progression_origin_note_does_not_trigger_block() -> None:
    desc = (
        "1) Scapular Pullups (haengend, bar): 3x8 BW, 1-2s Hold | "
        "Reps-Step 3x7->3x8. From passive Dead Hang -> scapula-pullup transition.\n"
    )
    blocks = cb._compute_muscle_overlap_blocks([_act(desc)], _TODAY)
    assert not _has_grip_block(blocks), blocks


# ── true positives MUST still trigger a grip block ───────────────────


def test_real_dead_hang_line_triggers_block() -> None:
    desc = "GRIP\nDead Hang: 3x15s | RPE 6 | scapula depression only\n"
    blocks = cb._compute_muscle_overlap_blocks([_act(desc)], _TODAY)
    assert _has_grip_block(blocks), blocks


def test_real_farmer_hold_line_triggers_block() -> None:
    desc = "GRIP\nFarmer's Hold KB: 3x35s/side 38kg | RPE 7\n"
    blocks = cb._compute_muscle_overlap_blocks([_act(desc)], _TODAY)
    assert _has_grip_block(blocks), blocks
