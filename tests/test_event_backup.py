"""Tests for app.utils.event_backup — capture-before-delete safety net."""
from __future__ import annotations

import json

from app.utils import event_backup


def test_backup_writes_full_event_json(tmp_path):
    target = tmp_path / "deleted_events.jsonl"
    events = [
        {"id": 1, "name": "Core Schicht D", "description": "full block text", "type": "WeightTraining"},
        {"id": 2, "name": "Balance", "type": "Workout"},
    ]
    n = event_backup.backup_events_before_delete(events, reason="push-dedup 2026-07-05", backup_path=target)
    assert n == 2
    lines = target.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert rec["reason"] == "push-dedup 2026-07-05"
    assert rec["event"]["name"] == "Core Schicht D"
    assert rec["event"]["description"] == "full block text"  # full content preserved
    assert "backed_up_at" in rec


def test_backup_appends_not_overwrites(tmp_path):
    target = tmp_path / "deleted_events.jsonl"
    event_backup.backup_events_before_delete([{"id": 1}], reason="a", backup_path=target)
    event_backup.backup_events_before_delete([{"id": 2}], reason="b", backup_path=target)
    lines = target.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2  # second call appended, did not clobber the first


def test_backup_empty_is_noop(tmp_path):
    target = tmp_path / "deleted_events.jsonl"
    assert event_backup.backup_events_before_delete([], reason="x", backup_path=target) == 0
    assert event_backup.backup_events_before_delete(None, reason="x", backup_path=target) == 0
    assert event_backup.backup_events_before_delete([None, {}], reason="x", backup_path=target) == 0
    assert not target.exists()


def test_backup_fail_soft_on_unwritable_path(tmp_path, caplog):
    """A broken backup path must NOT raise — it logs and returns 0 so the
    delete path is never wedged by a backup failure."""
    bad = tmp_path / "a_file_not_a_dir"
    bad.write_text("x", encoding="utf-8")
    unwritable = bad / "deleted.jsonl"  # parent is a file → mkdir/open fails
    result = event_backup.backup_events_before_delete([{"id": 1}], reason="x", backup_path=unwritable)
    assert result == 0  # no raise
