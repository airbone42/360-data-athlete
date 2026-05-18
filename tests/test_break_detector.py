"""Tests for break/vacation detection in _compute_planning_constraints.

Validates that the break-keyword regex correctly identifies genuine
training breaks in NOTEs while ignoring exercise instructions that
happen to contain words like "Pause", "Ruhe", or "rest".
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.graphs.sub_athlete_context.context_builder import (
    _compute_planning_constraints,
)

TODAY = date(2025, 6, 1)
TOMORROW_ISO = (TODAY + timedelta(days=1)).isoformat()


def _make_note(description: str, days_ahead: int = 1) -> dict:
    """Create a minimal NOTE event *days_ahead* days from TODAY."""
    d = TODAY + timedelta(days=days_ahead)
    return {
        "category": "NOTE",
        "start_date_local": d.isoformat(),
        "description": description,
        "name": "",
    }


class TestBreakDetectorTruePositives:
    """NOTEs that describe genuine breaks — must trigger the detector."""

    @pytest.mark.parametrize(
        "desc",
        [
            "Urlaub 03.06.–10.06.",
            "Trainingspause ab Montag",
            "Kein Training diese Woche",
            "Ruhe bis Donnerstag",
            "Reise nach Berlin",
            "Bin verreist",
            "Auszeit geplant",
            "Vacation next week",
            "No training until Friday",
            "Rest day planned",
            "Travel for work",
            "Away until Monday",
            "Time off this week",
            "Break until Wednesday",
        ],
    )
    def test_genuine_break_triggers(self, desc: str) -> None:
        result = _compute_planning_constraints(
            [_make_note(desc)], [], TODAY, None
        )
        assert "Break/vacation" in result, (
            f"Expected break detection for: {desc!r}"
        )


class TestBreakDetectorFalsePositives:
    """NOTEs that contain break keywords in exercise context — must NOT trigger."""

    @pytest.mark.parametrize(
        "desc",
        [
            "Scapular Pullups: 3x8, 2s Pause am Bar vor jeder Rep",
            "Dead Hang: 3x30s, 60s Pause zwischen Sätzen",
            "45s Pause nach jedem Satz",
            "Pause zwischen Übungen: 90s",
            "Ruheposition halten für 10s",
            "Ruhephase: 5s am tiefsten Punkt",
            "rest between sets: 60s",
            "rest period: 90 seconds",
            "rest position: full hang",
        ],
    )
    def test_exercise_instruction_ignored(self, desc: str) -> None:
        result = _compute_planning_constraints(
            [_make_note(desc)], [], TODAY, None
        )
        assert "Break/vacation" not in result, (
            f"False positive break detection for: {desc!r}"
        )


class TestBreakDetectorCompoundWords:
    """Compound words containing break keywords — must NOT trigger."""

    @pytest.mark.parametrize(
        "desc",
        [
            "Ruheposition einnehmen",
            "Ruhephase im Tempo 3-1-3",
        ],
    )
    def test_compound_word_ignored(self, desc: str) -> None:
        result = _compute_planning_constraints(
            [_make_note(desc)], [], TODAY, None
        )
        assert "Break/vacation" not in result, (
            f"False positive for compound word: {desc!r}"
        )


class TestBreakDetectorEdgeCases:
    """Edge cases: past events, non-NOTE categories."""

    def test_past_note_ignored(self) -> None:
        result = _compute_planning_constraints(
            [_make_note("Urlaub", days_ahead=-1)], [], TODAY, None
        )
        assert "Break/vacation" not in result

    def test_non_note_event_ignored(self) -> None:
        event = _make_note("Urlaub nächste Woche")
        event["category"] = "WORKOUT"
        result = _compute_planning_constraints([event], [], TODAY, None)
        assert "Break/vacation" not in result
