"""Structured JSONLines logging for sub-agent calls.

A lightweight, dependency-free local audit trail of which sub-agent
was invoked when, with what high-level input summary and what
high-level output summary. Writes one JSON object per line to
`$DATA_DIR/logs/agents.jsonl` (gitignored by convention).

Design choices:

- **Best-effort, non-blocking.** Every error is swallowed and logged
  to stderr — never raises into the caller. A failing log write must
  not break a real coaching session.
- **Token-free.** We do not capture full prompts or full LLM outputs
  (that's LangSmith / OTel territory and gets noisy fast). We capture
  *summaries* the caller picks: a few keys, a few field lengths,
  enough to debug "what did the planner see and what did it return".
- **No PII control.** This is a local file under the wrapper's
  `data/` dir; it inherits whatever privacy posture the operator has.
  Don't ship it anywhere external.
- **Schema-stable.** Adding new keys is fine. Renaming or removing
  is a breaking change for log consumers — keep the field list
  append-only.

Schema per line:
    {
        "ts":           ISO-8601 UTC timestamp (e.g. "2026-05-12T19:23:04Z")
        "agent":        plugin-namespaced or unqualified agent name
        "event":        "start" | "end" | "error"
        "input":        small dict with caller-chosen summary fields
        "output":       small dict with caller-chosen summary fields (end only)
        "error":        string (error event only)
        "duration_ms":  int (end / error event only)
        "session_id":   optional caller-supplied correlation key
    }
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.utils.paths import DATA_DIR

LOG_FILE: Path = DATA_DIR / "logs" / "agents.jsonl"

# Toggle: set to "0" to silently disable all writes (tests, CI).
_ENABLED_ENV = "AICOACH_AGENT_LOG_ENABLED"


def _enabled() -> bool:
    return os.environ.get(_ENABLED_ENV, "1") != "0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_line(record: Mapping[str, Any]) -> None:
    if not _enabled():
        return
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str))
            fh.write("\n")
    except OSError as exc:
        # Best-effort: complain to stderr but never raise.
        print(
            f"[agent_log] failed to write {LOG_FILE}: {exc}",
            file=sys.stderr,
        )


def log_agent_start(
    agent: str,
    input_summary: Mapping[str, Any] | None = None,
    *,
    session_id: str | None = None,
) -> float:
    """Record a sub-agent invocation start. Returns a monotonic ts for end-pairing."""
    _write_line(
        {
            "ts": _now_iso(),
            "agent": agent,
            "event": "start",
            "input": dict(input_summary or {}),
            "session_id": session_id,
        }
    )
    return time.monotonic()


def log_agent_end(
    agent: str,
    started_at: float | None = None,
    output_summary: Mapping[str, Any] | None = None,
    *,
    session_id: str | None = None,
) -> None:
    """Record a sub-agent invocation end."""
    duration_ms: int | None = None
    if started_at is not None:
        duration_ms = int((time.monotonic() - started_at) * 1000)
    _write_line(
        {
            "ts": _now_iso(),
            "agent": agent,
            "event": "end",
            "output": dict(output_summary or {}),
            "duration_ms": duration_ms,
            "session_id": session_id,
        }
    )


def log_agent_error(
    agent: str,
    error: str | BaseException,
    started_at: float | None = None,
    *,
    session_id: str | None = None,
) -> None:
    """Record that a sub-agent call failed."""
    duration_ms: int | None = None
    if started_at is not None:
        duration_ms = int((time.monotonic() - started_at) * 1000)
    _write_line(
        {
            "ts": _now_iso(),
            "agent": agent,
            "event": "error",
            "error": str(error),
            "duration_ms": duration_ms,
            "session_id": session_id,
        }
    )


__all__ = [
    "log_agent_start",
    "log_agent_end",
    "log_agent_error",
    "LOG_FILE",
]
