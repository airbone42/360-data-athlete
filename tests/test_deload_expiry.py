"""Tests for deload-expiry date handling in audit_consistency.

The expiry check previously re.matched ISO dates only: a recovery-week
block with a German `DD.MM.YYYY` end date silently produced no finding,
so the expiry could never trigger. The check now parses both formats via
`app.utils.date_parse.parse_config_date` and emits an explicit
`deload_end_unparseable` finding when the block is active but the end
date cannot be parsed.

All fixture dates are synthetic 2025 dates.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from app.utils.date_parse import parse_config_date
from scripts import audit_consistency as ac

# ── parse_config_date ────────────────────────────────────────────────


def test_parse_config_date_iso() -> None:
    assert parse_config_date("2025-04-19") == date(2025, 4, 19)


def test_parse_config_date_german() -> None:
    assert parse_config_date("19.04.2025") == date(2025, 4, 19)


def test_parse_config_date_german_single_digit() -> None:
    assert parse_config_date("1.4.2025") == date(2025, 4, 1)


@pytest.mark.parametrize("placeholder", ["—", "-", "–", "", "   ", None])
def test_parse_config_date_placeholder_returns_none(placeholder) -> None:
    assert parse_config_date(placeholder) is None


@pytest.mark.parametrize("garbage", ["soon", "2025/04/19", "19-04-2025", "next week"])
def test_parse_config_date_garbage_returns_none(garbage: str) -> None:
    assert parse_config_date(garbage) is None


@pytest.mark.parametrize("invalid", ["2025-02-30", "31.02.2025", "2025-13-01"])
def test_parse_config_date_invalid_calendar_date_returns_none(invalid: str) -> None:
    assert parse_config_date(invalid) is None


# ── check_deload_consistency ─────────────────────────────────────────


def _status_with_deload(monkeypatch, tmp_path: Path, aktiv: str, ende: str) -> None:
    """Write a minimal athlete_status.md and point resolve_config at it."""
    status = tmp_path / "athlete_status.md"
    status.write_text(
        "# Athlete Status\n\n"
        "## Erholungswoche-Status\n"
        f"- **aktiv:** {aktiv}\n"
        "- **start:** 2025-04-14\n"
        f"- **ende_geplant:** {ende}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ac, "resolve_config", lambda name: status)


def _categories(findings: list[dict]) -> list[str]:
    return [f["category"] for f in findings]


def test_deload_expired_iso_end_date(monkeypatch, tmp_path: Path) -> None:
    _status_with_deload(monkeypatch, tmp_path, "ja", "2025-04-20")
    findings = ac.check_deload_consistency()
    assert _categories(findings) == ["deload_expired"]
    assert "2025-04-20" in findings[0]["evidence"]


def test_deload_expired_german_end_date(monkeypatch, tmp_path: Path) -> None:
    """DD.MM.YYYY end dates previously slipped through silently."""
    _status_with_deload(monkeypatch, tmp_path, "ja", "20.04.2025")
    findings = ac.check_deload_consistency()
    assert _categories(findings) == ["deload_expired"]
    assert "20.04.2025" in findings[0]["evidence"]


def test_deload_active_with_garbage_end_is_flagged(monkeypatch, tmp_path: Path) -> None:
    """Active block + unparseable end date → MEDIUM finding, not silence."""
    _status_with_deload(monkeypatch, tmp_path, "ja", "sometime")
    findings = ac.check_deload_consistency()
    assert _categories(findings) == ["deload_end_unparseable"]
    assert findings[0]["severity"] == "MEDIUM"
    assert "sometime" in findings[0]["evidence"]


def test_deload_active_future_end_no_finding(monkeypatch, tmp_path: Path) -> None:
    future = (date.today() + timedelta(days=5)).isoformat()
    _status_with_deload(monkeypatch, tmp_path, "ja", future)
    assert ac.check_deload_consistency() == []


def test_deload_inactive_past_end_no_finding(monkeypatch, tmp_path: Path) -> None:
    _status_with_deload(monkeypatch, tmp_path, "nein", "2025-04-20")
    assert ac.check_deload_consistency() == []


def test_deload_no_section_no_finding(monkeypatch, tmp_path: Path) -> None:
    status = tmp_path / "athlete_status.md"
    status.write_text("# Athlete Status\n\n## Zonen\n- Z2\n", encoding="utf-8")
    monkeypatch.setattr(ac, "resolve_config", lambda name: status)
    assert ac.check_deload_consistency() == []
