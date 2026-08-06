"""Tests for the one-NOTE-per-day upsert (`app.utils.note_upsert`)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.note_upsert import (
    DAY_NOTE_PREFIX,
    merge_section,
    split_sections,
    upsert_day_note,
)


class _FakeClient:
    """Minimal client double: get_notes / post_events_bulk / update_event."""

    def __init__(self, notes: list[dict] | None = None) -> None:
        self.notes = notes or []
        self.posted: list[list[dict]] = []
        self.updated: list[tuple[int, dict]] = []

    async def get_notes(self, oldest: str, newest: str) -> list[dict]:
        return [
            n for n in self.notes
            if oldest <= (n.get("start_date_local") or "")[:10] <= newest
        ]

    async def post_events_bulk(self, events: list[dict]) -> list[dict]:
        self.posted.append(events)
        return [{**e, "id": 100 + i} for i, e in enumerate(events)]

    async def update_event(self, event_id: int, payload: dict) -> dict:
        self.updated.append((event_id, payload))
        return {**payload, "id": event_id}


def _run(coro):
    return asyncio.run(coro)


# ── split/merge unit behaviour ────────────────────────────────────────────────

def test_split_sections_legacy_plain_text_uses_fallback_name() -> None:
    assert split_sections("HRV 72ms, alles gut", "HRV-Review") == [
        ("HRV-Review", "HRV 72ms, alles gut")
    ]


def test_split_sections_parses_headings_in_order() -> None:
    desc = "## HRV-Review\nHRV gut.\n\n## Mental\nFokus da."
    assert split_sections(desc, "x") == [
        ("HRV-Review", "HRV gut."),
        ("Mental", "Fokus da."),
    ]


def test_merge_section_replaces_same_section_case_insensitive() -> None:
    desc = "## HRV-Review\nalt.\n\n## Mental\nbleibt."
    merged, names = merge_section(desc, "x", "hrv-review", "neu.")
    assert "alt." not in merged
    assert "neu." in merged and "bleibt." in merged
    assert names == ["HRV-Review", "Mental"]


def test_merge_section_appends_new_section() -> None:
    merged, names = merge_section("## Mental\nok.", "x", "Athleten-Feedback", "Beine müde.")
    assert merged.endswith("## Athleten-Feedback\nBeine müde.")
    assert names == ["Mental", "Athleten-Feedback"]


# ── upsert flow ───────────────────────────────────────────────────────────────

def test_upsert_creates_when_no_day_note_exists() -> None:
    client = _FakeClient()
    result = _run(upsert_day_note(client, "2025-05-20", "Athleten-Feedback", "Beine müde"))
    assert result["action"] == "created"
    assert client.posted[0][0]["name"] == "Athleten-Feedback"
    assert client.posted[0][0]["description"] == "Beine müde"
    assert not client.updated


def test_upsert_updates_existing_same_section_keeps_name() -> None:
    client = _FakeClient([{
        "id": 7, "category": "NOTE", "start_date_local": "2025-05-20T08:00:00",
        "name": "Athleten-Feedback", "description": "Beine müde",
    }])
    result = _run(upsert_day_note(client, "2025-05-20", "Athleten-Feedback", "Beine wieder ok"))
    assert result["action"] == "updated"
    event_id, payload = client.updated[0]
    assert event_id == 7
    assert payload["name"] == "Athleten-Feedback"
    assert "Beine wieder ok" in payload["description"]
    assert "Beine müde" not in payload["description"]
    assert not client.posted


def test_upsert_second_category_merges_and_renames_to_coach_log() -> None:
    client = _FakeClient([{
        "id": 7, "category": "NOTE", "start_date_local": "2025-05-20T08:00:00",
        "name": "HRV-Review", "description": "HRV 72ms, grün",
    }])
    result = _run(upsert_day_note(client, "2025-05-20", "Mental-Coach", "Fokus Grip-Session"))
    assert result["action"] == "updated"
    _, payload = client.updated[0]
    assert payload["name"] == f"{DAY_NOTE_PREFIX} 2025-05-20"
    # Both topics survive as sections; HRV-Review substring detection keeps working.
    assert "## HRV-Review\nHRV 72ms, grün" in payload["description"]
    assert "## Mental-Coach\nFokus Grip-Session" in payload["description"]


def test_upsert_targets_oldest_note_when_duplicates_exist() -> None:
    client = _FakeClient([
        {"id": 12, "category": "NOTE", "start_date_local": "2025-05-20T09:00:00",
         "name": "Athleten-Feedback", "description": "später"},
        {"id": 5, "category": "NOTE", "start_date_local": "2025-05-20T08:00:00",
         "name": "Athleten-Feedback", "description": "früher"},
    ])
    _run(upsert_day_note(client, "2025-05-20", "Athleten-Feedback", "neu"))
    event_id, _ = client.updated[0]
    assert event_id == 5


def test_upsert_ignores_notes_of_other_days() -> None:
    client = _FakeClient([{
        "id": 3, "category": "NOTE", "start_date_local": "2025-05-19T08:00:00",
        "name": "Athleten-Feedback", "description": "gestern",
    }])
    result = _run(upsert_day_note(client, "2025-05-20", "Athleten-Feedback", "heute"))
    assert result["action"] == "created"
