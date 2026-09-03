"""Tests for check_slot_authority in audit_consistency.

The failure this guards against: a scheduling decision is recorded next to the
exercise entry whose placement it justifies, the slot ledger is never updated,
and the next planning cycle contradicts the decision while every file involved
looks correct. Nothing is missing — the entry is simply in a file the planner
does not read for dates.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts import audit_consistency as ac

TODAY = date(2026, 9, 3)


@pytest.fixture()
def config_dir(monkeypatch, tmp_path: Path) -> Path:
    cd = tmp_path / "config"
    cd.mkdir()
    monkeypatch.setattr(ac, "CONFIG_DIR", cd)
    return cd


def _write(config_dir: Path, **files: str) -> None:
    for name, text in files.items():
        (config_dir / f"{name}.md").write_text(text, encoding="utf-8")


def _categories(findings: list[dict]) -> list[str]:
    return [f["category"] for f in findings]


class TestSlotAuthority:
    def test_dated_slot_missing_from_ledger_is_high(self, config_dir):
        _write(
            config_dir,
            competition_plan="## Slot-Buchführung\nNichts terminiert.",
            exercise_progressions="- **Erste Ausführung: Do 04.09.2026** im Bein-Block.",
        )
        findings = ac.check_slot_authority(TODAY)

        assert _categories(findings) == ["slot_not_in_ledger"]
        assert findings[0]["severity"] == ac.HIGH
        assert findings[0]["source_file"] == "config/exercise_progressions.md"
        assert findings[0]["canonical_source"] == "config/competition_plan.md"

    def test_date_mirrored_in_ledger_is_medium(self, config_dir):
        """Not lost, but two dates in two files drift apart eventually."""
        _write(
            config_dir,
            competition_plan="| Fr 04.09. | Grip-Block | geplant |",
            exercise_progressions="- **Erste Ausführung: Do 04.09.2026** im Bein-Block.",
        )
        findings = ac.check_slot_authority(TODAY)

        assert _categories(findings) == ["slot_duplicated"]
        assert findings[0]["severity"] == ac.MEDIUM

    def test_ledger_itself_is_never_flagged(self, config_dir):
        _write(config_dir, competition_plan="| Fr 04.09. | Grip-Block | geplant |")
        assert ac.check_slot_authority(TODAY) == []

    def test_historical_dates_are_not_commitments(self, config_dir):
        _write(
            config_dir,
            competition_plan="Nichts terminiert.",
            exercise_progressions=(
                "- Anker 13.05.2026 bestätigt, Video-Befund 11.06.2026 sauber."
            ),
        )
        assert ac.check_slot_authority(TODAY) == []

    def test_retrospective_line_is_not_a_commitment(self, config_dir):
        _write(
            config_dir,
            competition_plan="Nichts terminiert.",
            exercise_log="✅ Ausführung 04.09.2026: 3×10 gelaufen, RPE 6.",
        )
        assert ac.check_slot_authority(TODAY) == []

    def test_evidence_is_sanitised_and_bounded(self, config_dir):
        _write(
            config_dir,
            competition_plan="Nichts terminiert.",
            athlete_static="- Slot 04.09.2026 " + "Begründungsprosa " * 60,
        )
        finding = ac.check_slot_authority(TODAY)[0]

        assert len(finding["evidence"]) <= 200

    def test_fix_hint_names_the_planning_consequence(self, config_dir):
        """A hint that only says 'wrong file' does not explain why it matters."""
        _write(
            config_dir,
            competition_plan="Nichts terminiert.",
            athlete_static="- Nächster Heim-Slot 06.09.2026 nach der Kadenz.",
        )
        finding = ac.check_slot_authority(TODAY)[0]

        assert "Tagesplanung" in finding["fix_hint"]
        assert "2026-09-06" in finding["fix_hint"]

    def test_stale_commitment_may_be_removed_not_only_added(self, config_dir):
        """The misfiled entry can be the outdated side — the hint says so."""
        _write(
            config_dir,
            competition_plan="Nichts terminiert.",
            exercise_progressions="- Long Run am 05.09.2026.",
        )
        finding = ac.check_slot_authority(TODAY)[0]

        assert "entfernen" in finding["fix_hint"]

    def test_check_is_registered_and_offline(self):
        assert ac.CHECK_MAP["SLOT_AUTHORITY"] == ("check_slot_authority", False)

    def test_empty_config_dir_is_clean(self, config_dir):
        assert ac.check_slot_authority(TODAY) == []
