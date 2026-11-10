"""Tests for exercise-level prescription-compliance tracking."""

from __future__ import annotations

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


def _activity(day: str, names: list[str], workout_name: str = "session",
              activity_type: str = "WeightTraining") -> dict:
    """An intervals.icu activity whose description lists the given exercises."""
    return {
        "start_date_local": f"{day}T18:00:00",
        "name": workout_name,
        "type": activity_type,
        "description": "\n".join(f"{n}: 3x8 RPE 6" for n in names),
    }


MD = (
    "### Single-Leg Hip Thrust (Kernlift-Option A)\n"
    "- **Soll-Frequenz:** 2x/Woche\n"
)


def test_related_variant_never_counts_as_execution():
    """A related variant must not mark a different exercise as executed.

    An alias table collapses a single-leg glute bridge and a single-leg hip
    thrust under one key. Counting that as the prescribed hip thrust would
    report a never-executed prescription as satisfied — the one failure this
    checker must not have.
    """
    acts = [_activity("2026-07-30", ["Single-Leg Glute Bridge (neu)"])]

    findings = pc.compute_prescription_compliance(MD, date(2026, 7, 31), acts)
    assert len(findings) == 1
    assert findings[0]["status"] == "never"


def test_recent_execution_clears_the_finding():
    acts = [_activity("2026-07-30", ["Single-Leg Hip Thrust"])]

    assert pc.compute_prescription_compliance(MD, date(2026, 7, 31), acts) == []


def test_stale_execution_is_reported_with_the_gap():
    acts = [_activity("2026-07-20", ["Single-Leg Hip Thrust"])]

    findings = pc.compute_prescription_compliance(MD, date(2026, 7, 31), acts)
    assert len(findings) == 1
    assert findings[0]["status"] == "overdue"
    assert findings[0]["days_since"] == 11
    assert findings[0]["last_execution"] == "2026-07-20"


def test_no_declaration_means_no_tracking():
    md = "### Irgendeine Übung\n- **Aktueller Stand:** 3x10\n"
    assert pc.compute_prescription_compliance(md, date(2026, 7, 31), []) == []


def test_format_findings_is_none_when_clean():
    assert pc.format_findings([]) is None


BLOCK_MD = (
    "### Schulter-Mobilisation + Atemübungen — Physio-Protokoll\n"
    "- **Soll-Frequenz:** alle 2 Tage\n"
)


def test_block_prescription_counts_its_own_session():
    """A block-level prescription is executed when its session ran.

    The block's parts are logged under their own names; the block name only
    ever appears as the session name. Reading exercises alone reported a
    block run every other day as "never executed".
    """
    acts = [_activity(
        "2026-10-09",
        ["Open Book Seitenlage"],
        workout_name="Schulter-Mobilisation + Atemübungen (Urlaubsfassung)",
        activity_type="Workout",
    )]

    assert pc.compute_prescription_compliance(BLOCK_MD, date(2026, 10, 10), acts) == []


def test_session_name_needs_prefix_not_mention():
    """A session that only mentions the exercise in its title does not count."""
    acts = [_activity("2026-07-30", [], workout_name="Bein-Tag mit Single-Leg Hip Thrust")]

    findings = pc.compute_prescription_compliance(MD, date(2026, 7, 31), acts)
    assert len(findings) == 1
    assert findings[0]["status"] == "never"


def test_run_description_is_not_read_as_exercises():
    """Only strength sessions list exercises; a run description is prose."""
    acts = [_activity("2026-07-30", ["Single-Leg Hip Thrust"], activity_type="Run")]

    findings = pc.compute_prescription_compliance(MD, date(2026, 7, 31), acts)
    assert [f["status"] for f in findings] == ["never"]


def test_activity_outside_the_window_is_ignored():
    acts = [_activity("2026-05-01", ["Single-Leg Hip Thrust"])]

    findings = pc.compute_prescription_compliance(
        MD, date(2026, 7, 31), acts, lookback_days=28
    )
    assert [f["status"] for f in findings] == ["never"]
