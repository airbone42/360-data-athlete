"""Tests for the day-NOTE `--section` wiring in `scripts/post_message.py`.

`app.utils.note_upsert` merges per `## <Section>` block: an existing section is
replaced, a new one appended. The section name is therefore the identity of the
block, and the CLI must be able to name it — otherwise every day-NOTE write
lands in the same block and silently overwrites the previous one.

Regression guarded here: when the section name is fixed in the script rather
than passed in, a later write about a different topic replaces the earlier
block. The upsert reports a successful update either way, so nothing at the
call site distinguishes "merged alongside" from "overwrote". These tests pin
the CLI contract instead of relying on the caller to remember.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.note_upsert import merge_section

_SCRIPT = Path(__file__).parent.parent / "scripts" / "post_message.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("post_message_under_test", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_parser_args(argv: list[str]):
    """Rebuild the script's parser exactly as `main()` does, then parse argv."""
    import argparse
    from datetime import date

    parser = argparse.ArgumentParser(description="Post message to intervals.icu")
    parser.add_argument("--activity-id")
    parser.add_argument("--message")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--note")
    parser.add_argument("--section", default="Athleten-Feedback")
    return parser.parse_args(argv)


def test_cli_exposes_section_with_backwards_compatible_default() -> None:
    """The flag exists and defaults to the historical section name."""
    module = _load_module()
    source = _SCRIPT.read_text(encoding="utf-8")
    assert '"--section"' in source, "post_message.py must expose a --section flag"
    assert 'default="Athleten-Feedback"' in source, (
        "the default must stay Athleten-Feedback so existing callers are unaffected"
    )
    assert "section=args.section" in source, (
        "the parsed --section must reach upsert_day_note; a hardcoded section "
        "makes every day-NOTE write overwrite the previous one"
    )
    assert module is not None


def test_section_flag_is_passed_through_to_upsert(monkeypatch) -> None:
    """`_run` hands the parsed section to `upsert_day_note` verbatim."""
    module = _load_module()
    seen: dict[str, object] = {}

    async def _fake_upsert(client, date_str, section, text):
        seen.update(date=date_str, section=section, text=text)
        return {"action": "updated", "event": {"id": 1}}

    monkeypatch.setattr(module, "upsert_day_note", _fake_upsert)
    monkeypatch.setattr(module, "CachedIntervalsClient", lambda *_a, **_k: object())

    args = _build_parser_args(
        ["--date", "2026-01-15", "--note", "day-close text", "--section", "Day-Close"]
    )
    asyncio.run(module._run(args))

    assert seen["section"] == "Day-Close"
    assert seen["date"] == "2026-01-15"
    assert seen["text"] == "day-close text"


def test_default_section_reaches_upsert_when_flag_omitted(monkeypatch) -> None:
    module = _load_module()
    seen: dict[str, object] = {}

    async def _fake_upsert(client, date_str, section, text):
        seen["section"] = section
        return {"action": "created", "event": {"id": 2}}

    monkeypatch.setattr(module, "upsert_day_note", _fake_upsert)
    monkeypatch.setattr(module, "CachedIntervalsClient", lambda *_a, **_k: object())

    args = _build_parser_args(["--date", "2026-01-15", "--note", "morning report"])
    asyncio.run(module._run(args))

    assert seen["section"] == "Athleten-Feedback"


def test_distinct_sections_coexist_same_section_replaces() -> None:
    """The behaviour the flag exists for, pinned end-to-end on the merger.

    Same section twice = the first text is gone. Different sections = both
    survive. This is why a second day-NOTE about a different topic must name
    its own section.
    """
    first, _ = merge_section("", "Athleten-Feedback", "Athleten-Feedback", "first topic text")

    overwritten, names = merge_section(
        first, "Athleten-Feedback", "Athleten-Feedback", "second topic text"
    )
    assert "first topic text" not in overwritten, (
        "same section must replace — this is the documented footgun"
    )
    assert names == ["Athleten-Feedback"]

    coexisting, names = merge_section(
        first, "Athleten-Feedback", "Day-Close", "second topic text"
    )
    assert "first topic text" in coexisting
    assert "second topic text" in coexisting
    assert names == ["Athleten-Feedback", "Day-Close"]
