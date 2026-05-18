"""Snapshot test: build_context() must return all expected top-level keys.

This test protects the camelCase contract consumed by prompts and fetch_context.py.
Any key removal or rename will fail this test, preventing silent regressions.
"""
from __future__ import annotations

from app.graphs.sub_athlete_context.context_builder import build_context
from app.graphs.sub_athlete_context.state import AthleteContextState

# Canonical set of required top-level keys (from context_builder.py:133-175).
# Add new keys here when they're intentionally added — never silently remove.
REQUIRED_CONTEXT_KEYS = {
    "hrvContext",
    "hrv",
    "rhr",
    "sleep",
    "sleepHours",
    "activities",
    "ctl",
    "atl",
    "tsb",
    "ctlDisplay",
    "hrvBaseline",
    "hrvDeviation",
    "sleepTrend",
    "rhrTrend",
    "ctlTrend",
    "cycleHint",
    "zoneDistribution",
    "weeklyZoneBalance",
    "mesoLoadTrend",
    "weatherInfo",
    "intensityReadiness",
    "daysSinceIntense",
    "lastRestDay",
    "athleteFeedback",
    "eventList",
    "raceInDays",
    "dateStr",
    "hrZones",
    "hrvReviewPending",
    "skippedWorkouts",
    "dataWarnings",
}


def _minimal_state() -> AthleteContextState:
    return AthleteContextState(
        athlete_id="i12345",
        date="2025-04-19",
        wellness={},
        rhr_retry_count=0,
        activities=[],
        workouts=[],
        events=[],
        wellness_history=[],
        weather={},
        weather_warning=False,
        athlete_settings={},
        context_summary={},
    )


def test_context_keys_superset_of_required() -> None:
    """build_context() output must contain at least all required keys."""
    result = build_context(_minimal_state())
    missing = REQUIRED_CONTEXT_KEYS - set(result.keys())
    assert not missing, f"build_context() missing keys: {sorted(missing)}"


def test_context_returns_dict() -> None:
    result = build_context(_minimal_state())
    assert isinstance(result, dict)


def test_context_date_str_contains_date() -> None:
    result = build_context(_minimal_state())
    # dateStr is a formatted string like "Saturday, 19. April 2025"
    assert "2025" in result["dateStr"]
    assert isinstance(result["dateStr"], str)
