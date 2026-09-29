"""The recovery-week status block parses in both spellings.

fetch_context read the block only under the German heading with German keys,
while config.example/athlete_status.md ships the English one, so a recovery
week set in an English config never reached the context. The context and the
audit check now share app.utils.recovery_week.
"""
from __future__ import annotations

from pathlib import Path

from app.utils.recovery_week import parse_recovery_week
from scripts import audit_consistency as ac
from scripts import fetch_context as fc

GERMAN = (
    "# Athlete Status\n\n"
    "## Erholungswoche-Status\n"
    "- **aktiv:** ja\n"
    "- **start:** 2025-04-14\n"
    "- **ende_geplant:** 20.04.2025\n"
    "- **begründung:** Drei Belastungswochen\n\n"
    "## Zonen\n- Z2\n"
)

ENGLISH = (
    "# Athlete Status\n\n"
    "## Recovery week status\n"
    "- **active:** yes\n"
    "- **start:** 2025-04-14\n"
    "- **planned end:** 2025-04-20\n"
    "- **reason:** three load weeks\n\n"
    "## Zones\n- Z2\n"
)


def test_german_block() -> None:
    assert parse_recovery_week(GERMAN) == {
        "aktiv": "ja",
        "start": "2025-04-14",
        "ende_geplant": "20.04.2025",
        "begründung": "Drei Belastungswochen",
    }


def test_english_block_uses_the_context_builder_keys() -> None:
    assert parse_recovery_week(ENGLISH) == {
        "active": "yes",
        "start": "2025-04-14",
        "planned_end": "2025-04-20",
        "rationale": "three load weeks",
    }


def test_no_block() -> None:
    assert parse_recovery_week("# Athlete Status\n\n## Zones\n- Z2\n") == {}


def test_demo_config_block_is_read() -> None:
    demo = Path(__file__).resolve().parents[1] / "config.example" / "athlete_status.md"
    assert parse_recovery_week(demo.read_text(encoding="utf-8")).get("active") == "no"


def test_fetch_context_reads_the_english_block(monkeypatch, tmp_path: Path) -> None:
    status = tmp_path / "athlete_status.md"
    status.write_text(ENGLISH, encoding="utf-8")
    monkeypatch.setattr(fc, "_athlete_status_path", lambda: str(status))
    assert fc._parse_deload_state()["active"] == "yes"


def test_audit_flags_an_expired_english_block(monkeypatch, tmp_path: Path) -> None:
    status = tmp_path / "athlete_status.md"
    status.write_text(ENGLISH, encoding="utf-8")
    monkeypatch.setattr(ac, "resolve_config", lambda name: status)
    findings = ac.check_deload_consistency()
    assert [f["category"] for f in findings] == ["deload_expired"]
    assert "2025-04-20" in findings[0]["evidence"]
