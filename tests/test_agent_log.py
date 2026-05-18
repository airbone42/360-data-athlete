"""Smoketests for app.utils.agent_log — structured JSONLines logging."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture()
def patched_log_file(tmp_path, monkeypatch):
    """Redirect the module-level LOG_FILE into a tmp dir so we can read it back."""
    target = tmp_path / "logs" / "agents.jsonl"
    monkeypatch.setattr("app.utils.agent_log.LOG_FILE", target)
    monkeypatch.setenv("AICOACH_AGENT_LOG_ENABLED", "1")
    return target


def _read_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_start_and_end_round_trip(patched_log_file):
    from app.utils.agent_log import log_agent_end, log_agent_start

    started = log_agent_start(
        "planner",
        input_summary={"date": "2025-05-12", "hrv": 62},
        session_id="abc",
    )
    log_agent_end(
        "planner",
        started_at=started,
        output_summary={"workouts": 2, "rest_day": False},
        session_id="abc",
    )

    lines = _read_lines(patched_log_file)
    assert len(lines) == 2
    assert lines[0]["event"] == "start"
    assert lines[0]["agent"] == "planner"
    assert lines[0]["input"] == {"date": "2025-05-12", "hrv": 62}
    assert lines[0]["session_id"] == "abc"
    assert lines[1]["event"] == "end"
    assert lines[1]["output"] == {"workouts": 2, "rest_day": False}
    assert isinstance(lines[1]["duration_ms"], int)
    assert lines[1]["duration_ms"] >= 0


def test_error_event(patched_log_file):
    from app.utils.agent_log import log_agent_error, log_agent_start

    started = log_agent_start("specialist-endurance")
    log_agent_error("specialist-endurance", "intervals.icu 503", started_at=started)

    lines = _read_lines(patched_log_file)
    assert lines[-1]["event"] == "error"
    assert "503" in lines[-1]["error"]
    assert isinstance(lines[-1]["duration_ms"], int)


def test_disabled_via_env_var(patched_log_file, monkeypatch):
    monkeypatch.setenv("AICOACH_AGENT_LOG_ENABLED", "0")
    from app.utils.agent_log import log_agent_end, log_agent_start

    log_agent_start("planner")
    log_agent_end("planner")

    assert not patched_log_file.exists(), "no file should be created when disabled"


def test_write_failure_does_not_raise(monkeypatch, tmp_path):
    """If the log dir can't be created or written, we swallow the error."""
    # Point at a path whose parent we can't create (an existing file used as dir).
    blocker = tmp_path / "block"
    blocker.write_text("not-a-dir")
    fake_log = blocker / "logs" / "agents.jsonl"
    monkeypatch.setattr("app.utils.agent_log.LOG_FILE", fake_log)
    monkeypatch.setenv("AICOACH_AGENT_LOG_ENABLED", "1")

    from app.utils.agent_log import log_agent_start

    # Must not raise.
    log_agent_start("planner")


def test_unicode_safe(patched_log_file):
    from app.utils.agent_log import log_agent_end

    log_agent_end(
        "coach-analyst",
        output_summary={"comment": "stark — solider Z2-Block 👟"},
    )
    lines = _read_lines(patched_log_file)
    assert lines[0]["output"]["comment"] == "stark — solider Z2-Block 👟"
