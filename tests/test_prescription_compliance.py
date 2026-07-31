"""Tests for exercise-level prescription-compliance tracking."""

from __future__ import annotations

import json
from datetime import date

import pytest

from app.analytics import prescription_compliance as pc


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("täglich", 1),
        ("taeglich", 1),
        ("daily", 1),
        ("alle 2 Tage", 2),
        ("alle 3 Tage", 3),
        ("every 2 days", 2),
        ("2x/Woche", 5),
        ("3x/Woche", 4),
        ("1x/Woche", 8),
        ("wöchentlich", 8),
        ("woechentlich", 8),
        ("weekly", 8),
        ("gelegentlich mal", None),
        ("", None),
    ],
)
def test_parse_frequency(raw, expected):
    assert pc.parse_frequency(raw) == expected


def test_parse_prescriptions_strips_heading_documentation():
    md = (
        "### Single-Leg Hip Thrust (Kernlift-Option A)\n"
        "- **Soll-Frequenz:** 2x/Woche — Begründung nach dem Gedankenstrich\n"
        "### TRX Plank (Arme angewinkelt) — Physio-Protokoll ab 27.07.2026\n"
        "- **Soll-Frequenz:** alle 2 Tage\n"
        "### Ohne Deklaration\n"
        "- irgendeine Zeile\n"
    )
    got = pc.parse_prescriptions(md)
    assert [g["name"] for g in got] == ["Single-Leg Hip Thrust", "TRX Plank"]
    # Prose after the dash is documentation, not part of the cadence.
    assert got[0]["raw_frequency"] == "2x/Woche"
    assert got[0]["max_gap_days"] == 5
    assert got[1]["max_gap_days"] == 2


def test_umlaut_spellings_match_each_other():
    """Descriptions use real umlauts and ASCII digraphs interchangeably."""
    assert pc._normalise("TRX Rücken-Hochdrücken") == pc._normalise(
        "trx ruecken-hochdruecken"
    )


def _write_log(tmp_path, day: str, names: list[str]) -> None:
    muscles = tmp_path / "muscles"
    muscles.mkdir(exist_ok=True)
    payload = {
        "date": day,
        "sessions": [
            {
                "workout_name": "session",
                "exercises": [
                    {"name": n, "mapping_key": "hip_thrust"} for n in names
                ],
            }
        ],
    }
    (muscles / f"{day}.json").write_text(json.dumps(payload), encoding="utf-8")


MD = (
    "### Single-Leg Hip Thrust (Kernlift-Option A)\n"
    "- **Soll-Frequenz:** 2x/Woche\n"
)


def test_mapping_key_never_counts_as_execution(tmp_path, monkeypatch):
    """A shared mapping key must not mark a different exercise as executed.

    Mapping keys deliberately collapse variants for muscle-load purposes, so a
    single-leg glute bridge also carries `hip_thrust`. Counting that as the
    prescribed hip thrust would report a never-executed prescription as
    satisfied — the one failure this checker must not have.
    """
    monkeypatch.setattr(pc, "DATA_DIR", tmp_path)
    _write_log(tmp_path, "2026-07-30", ["single-leg glute bridge (neu)"])

    findings = pc.compute_prescription_compliance(MD, date(2026, 7, 31))
    assert len(findings) == 1
    assert findings[0]["status"] == "never"


def test_recent_execution_clears_the_finding(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "DATA_DIR", tmp_path)
    _write_log(tmp_path, "2026-07-30", ["single-leg hip thrust, 3x8 bodyweight"])

    assert pc.compute_prescription_compliance(MD, date(2026, 7, 31)) == []


def test_stale_execution_is_reported_with_the_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "DATA_DIR", tmp_path)
    _write_log(tmp_path, "2026-07-20", ["single-leg hip thrust"])

    findings = pc.compute_prescription_compliance(MD, date(2026, 7, 31))
    assert len(findings) == 1
    assert findings[0]["status"] == "overdue"
    assert findings[0]["days_since"] == 11
    assert findings[0]["last_execution"] == "2026-07-20"


def test_no_declaration_means_no_tracking(tmp_path, monkeypatch):
    monkeypatch.setattr(pc, "DATA_DIR", tmp_path)
    md = "### Irgendeine Übung\n- **Aktueller Stand:** 3x10\n"
    assert pc.compute_prescription_compliance(md, date(2026, 7, 31)) == []


def test_format_findings_is_none_when_clean():
    assert pc.format_findings([]) is None
