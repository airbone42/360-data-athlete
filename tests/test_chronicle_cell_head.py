"""Tests for check_chronicle_cell_bloat in audit_consistency.

CONFIG_DIR is redirected to a tmp dir, so these never read the real
config/ or config.example/ contents.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import audit_consistency as ac


@pytest.fixture()
def config_dir(monkeypatch, tmp_path: Path) -> Path:
    cd = tmp_path / "config"
    cd.mkdir()
    monkeypatch.setattr(ac, "CONFIG_DIR", cd)
    return cd


def _row(zone: str, chars: int) -> str:
    return f"| **{zone}** | monitoring | {'x' * chars} |"


def _table(*rows: str) -> str:
    header = "| Zone | Status | Notes |\n|------|--------|-------|\n"
    return header + "\n".join(rows) + "\n"


def test_short_cells_are_not_flagged(config_dir):
    (config_dir / "athlete_static.md").write_text(
        _table(_row("Achilles", 40), _row("Shoulder", 120)), encoding="utf-8"
    )
    assert ac.check_chronicle_cell_bloat() == []


def test_long_cell_without_head_is_flagged(config_dir):
    (config_dir / "athlete_static.md").write_text(
        _table(_row("Achilles", ac.CHRONICLE_CELL_MAX_CHARS + 1)), encoding="utf-8"
    )
    findings = ac.check_chronicle_cell_bloat()
    assert len(findings) == 1
    assert findings[0]["category"] == "chronicle_cell_without_head"
    assert findings[0]["severity"] == ac.MEDIUM
    assert findings[0]["source_file"] == "config/athlete_static.md"
    assert findings[0]["source_line"] == 3


def test_cell_exactly_at_threshold_passes(config_dir):
    (config_dir / "athlete_static.md").write_text(
        _table(_row("Achilles", ac.CHRONICLE_CELL_MAX_CHARS)), encoding="utf-8"
    )
    assert ac.check_chronicle_cell_bloat() == []


def test_declared_lever_head_suppresses_the_finding(config_dir):
    body = (
        "<!-- lever-head: Achilles -->\n\n"
        + _table(_row("Achilles", ac.CHRONICLE_CELL_MAX_CHARS + 500))
    )
    (config_dir / "athlete_static.md").write_text(body, encoding="utf-8")
    assert ac.check_chronicle_cell_bloat() == []


def test_head_for_a_different_row_does_not_suppress(config_dir):
    body = (
        "<!-- lever-head: Shoulder -->\n\n"
        + _table(_row("Achilles", ac.CHRONICLE_CELL_MAX_CHARS + 500))
    )
    (config_dir / "athlete_static.md").write_text(body, encoding="utf-8")
    findings = ac.check_chronicle_cell_bloat()
    assert len(findings) == 1
    assert "Achilles" in findings[0]["evidence"]


def test_head_key_matching_ignores_emphasis_case_and_spacing(config_dir):
    body = (
        "<!--   lever-head:  **hip / TFL   right**  -->\n\n"
        + _table(_row("Hip / TFL right", ac.CHRONICLE_CELL_MAX_CHARS + 500))
    )
    (config_dir / "athlete_static.md").write_text(body, encoding="utf-8")
    assert ac.check_chronicle_cell_bloat() == []


def test_row_that_swallowed_its_closing_pipe_is_still_caught(config_dir):
    """The worst cells are exactly the ones that break the table syntax."""
    broken = f"| **Ankle** | monitoring | {'x' * (ac.CHRONICLE_CELL_MAX_CHARS + 1)}"
    (config_dir / "athlete_static.md").write_text(
        "| Zone | Status | Notes |\n|------|--------|-------|\n" + broken + "\n",
        encoding="utf-8",
    )
    findings = ac.check_chronicle_cell_bloat()
    assert len(findings) == 1
    assert "Ankle" in findings[0]["evidence"]


def test_separator_and_non_table_lines_are_ignored(config_dir):
    (config_dir / "athlete_static.md").write_text(
        "Prose line that is very long " + "y" * 3000 + "\n\n"
        "|--------------------|\n",
        encoding="utf-8",
    )
    assert ac.check_chronicle_cell_bloat() == []


def test_every_config_markdown_file_is_scanned(config_dir):
    (config_dir / "athlete_status.md").write_text(
        _table(_row("Zone A", ac.CHRONICLE_CELL_MAX_CHARS + 10)), encoding="utf-8"
    )
    (config_dir / "notes.txt").write_text("|" + "z" * 5000, encoding="utf-8")
    findings = ac.check_chronicle_cell_bloat()
    assert [f["source_file"] for f in findings] == ["config/athlete_status.md"]


def test_check_is_registered_offline(config_dir):
    assert ac.CHECK_MAP["CHRONICLE_HEAD"] == ("check_chronicle_cell_bloat", False)
