"""Tests for the daily-digest context field (`dailyDigest`)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.graphs.sub_athlete_context.context_builder import (
    _format_daily_digest,
    _format_notes,
)


@pytest.fixture(autouse=True)
def _digest_settings(monkeypatch):
    monkeypatch.setattr(settings, "daily_digest_section", "Daily digest")
    monkeypatch.setattr(settings, "daily_digest_days", 3)


def _note(day: str, description: str, name: str = "Coach-Log") -> dict:
    return {
        "category": "NOTE",
        "start_date_local": f"{day}T08:00:00",
        "name": name,
        "description": description,
    }


LONG_DIGEST = "Decisions of the day. " + "x" * 900


def test_digest_is_surfaced_untruncated():
    notes = [_note("2026-10-08", f"## Athlete feedback\nfelt good\n\n## Daily digest\n{LONG_DIGEST}")]
    out = _format_daily_digest(notes, date(2026, 10, 9))
    assert out.startswith("2026-10-08:\n")
    assert "x" * 900 in out


def test_digest_is_stripped_from_athlete_feedback():
    notes = [_note("2026-10-08", f"## Athlete feedback\nfelt good\n\n## Daily digest\n{LONG_DIGEST}")]
    feedback = _format_notes(notes)
    assert "felt good" in feedback
    assert "Decisions of the day" not in feedback


def test_note_without_digest_is_unchanged_in_feedback():
    notes = [_note("2026-10-08", "plain legacy note", name="Athlete feedback")]
    assert "plain legacy note" in _format_notes(notes)
    assert _format_daily_digest(notes, date(2026, 10, 9)) == "No daily digest"


def test_window_and_order():
    notes = [
        _note("2026-10-09", "## Daily digest\ntoday"),
        _note("2026-10-05", "## Daily digest\ntoo old"),
        _note("2026-10-07", "## Daily digest\nolder"),
    ]
    out = _format_daily_digest(notes, date(2026, 10, 9))
    assert "too old" not in out
    assert out.index("2026-10-07") < out.index("2026-10-09")


def test_section_heading_is_configurable(monkeypatch):
    monkeypatch.setattr(settings, "daily_digest_section", "Tagesabschluss")
    notes = [_note("2026-10-08", "## Tagesabschluss\nsummary")]
    assert "summary" in _format_daily_digest(notes, date(2026, 10, 9))


def test_disabled_with_zero_days(monkeypatch):
    monkeypatch.setattr(settings, "daily_digest_days", 0)
    notes = [_note("2026-10-08", "## Daily digest\nsummary")]
    assert _format_daily_digest(notes, date(2026, 10, 9)) == "No daily digest"
