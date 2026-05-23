"""Tests for validate_plan.py R016 — Exercise regression guard."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    _match_exercise_name,
    _parse_exercise_progressions,
    _parse_workout_exercise_line,
    check_exercise_regression,
)


# Minimal progressions document covering the test exercises
PROGRESSIONS = """# config/exercise_progressions.md

## Core

### McGill Curl-up
- **Aktueller Stand:** 3×10 je Seite, 8s Hold — RPE 6-7 (21.05.2026)
- **Progression-Vektor:** Hold-Zeit primär, NIE Reps-Erhöhung über 10.

### Farmer's Hold (KB, einarmig)
- **Aktueller Stand:** 3×35s je Seite, 32.5 kg — RPE 7 (17.05.2026)
- **Progression:** +2.5 kg bei RPE ≤6.

### Wrist Curls
- **Aktueller Stand:** 3×10 je Seite, 9 kg — RPE 5-6 (Joint-Signal, Last-Cap @ 9 kg)

### Side Plank
- **Aktueller Stand:** unbekannt
"""


def _ctx() -> Context:
    return Context(target_date="2026-05-23", exercise_progressions=PROGRESSIONS)


def _wo(description: str, coaching_notes: str = "", name: str = "Test Ninja") -> dict:
    return {
        "type": "WeightTraining",
        "name": name,
        "tags": ["ninja", "grip"],
        "coaching_notes": coaching_notes,
        "description": description,
    }


# ─── parsing primitives ──────────────────────────────────────────────────

def test_parse_progressions_extracts_hold_time():
    parsed = _parse_exercise_progressions(PROGRESSIONS)
    assert "McGill Curl-up" in parsed
    assert parsed["McGill Curl-up"]["hold_s"] == 8
    assert parsed["McGill Curl-up"]["reps"] == 10


def test_parse_progressions_extracts_weight():
    parsed = _parse_exercise_progressions(PROGRESSIONS)
    farmer = parsed.get("Farmer's Hold (KB, einarmig)")
    assert farmer is not None
    assert farmer["weight_kg"] == 32.5


def test_parse_progressions_skips_unknown_state():
    parsed = _parse_exercise_progressions(PROGRESSIONS)
    sp = parsed.get("Side Plank")
    assert sp is not None
    assert sp["hold_s"] is None
    assert sp["weight_kg"] is None


def test_parse_workout_line_hold():
    p = _parse_workout_exercise_line(
        "McGill Curl-up: 3x10/Seite mit 7s Hold | Bracing 'Tss!'"
    )
    assert p is not None
    assert p["name"] == "McGill Curl-up"
    assert p["hold_s"] == 7
    assert p["reps"] == 10


def test_parse_workout_line_weight():
    p = _parse_workout_exercise_line(
        "Farmer's Hold KB einarmig: 3x35s/Seite 32.5kg | RPE 7"
    )
    assert p is not None
    assert p["weight_kg"] == 32.5


def test_parse_workout_line_ignores_metadata():
    """Non-exercise lines (headings, sublines) should not parse."""
    assert _parse_workout_exercise_line("MAIN BLOCK") is None
    assert _parse_workout_exercise_line("") is None
    assert _parse_workout_exercise_line("# Heading") is None


def test_match_exercise_name_fuzzy():
    docs = ["Farmer's Hold (KB, einarmig)", "McGill Curl-up", "Wrist Curls"]
    assert _match_exercise_name("Farmer's Hold KB einarmig", docs) == "Farmer's Hold (KB, einarmig)"
    assert _match_exercise_name("McGill Curl-up", docs) == "McGill Curl-up"


# ─── regression detection ───────────────────────────────────────────────

def test_r016_fires_on_silent_hold_regression():
    """Canonical McGill 21.05.→23.05. case: 8s → 7s without exemption."""
    wo = _wo("McGill Curl-up: 3x10/Seite mit 7s Hold | Bracing 'Tss!'")
    findings = check_exercise_regression([wo], _ctx())
    errs = [f for f in findings if f.severity == "ERROR" and f.rule_id == "R016"]
    assert len(errs) == 1
    assert "hold_s 7<8" in errs[0].message
    assert "McGill" in errs[0].message


def test_r016_silent_on_held_value():
    """Same hold-time as documented = no regression."""
    wo = _wo("McGill Curl-up: 3x10/Seite mit 8s Hold")
    assert check_exercise_regression([wo], _ctx()) == []


def test_r016_silent_on_eskalation():
    """Higher hold-time than documented = progression, no error."""
    wo = _wo("McGill Curl-up: 3x10/Seite mit 9s Hold")
    assert check_exercise_regression([wo], _ctx()) == []


def test_r016_fires_on_weight_regression():
    """Farmer 32.5kg documented, plan drops to 30kg without reason → ERROR."""
    wo = _wo("Farmer's Hold KB einarmig: 3x35s/Seite 30kg | RPE 6")
    findings = check_exercise_regression([wo], _ctx())
    errs = [f for f in findings if f.severity == "ERROR"]
    assert any("weight_kg 30.0<32.5" in f.message for f in errs)


def test_r016_skips_undocumented_exercise():
    """An exercise without an Aktueller Stand entry won't fire."""
    wo = _wo("Unbekannte Übung: 3x10 mit 5s Hold")
    assert check_exercise_regression([wo], _ctx()) == []


def test_r016_skips_exercise_with_unknown_state():
    """Side Plank has 'unbekannt' → no comparison possible."""
    wo = _wo("Side Plank: 3x20s/Seite")
    assert check_exercise_regression([wo], _ctx()) == []


# ─── exemption keywords ─────────────────────────────────────────────────

def test_r016_exempts_on_workout_coaching_notes_rhr_drift():
    """RHR-Drift in coaching_notes → INFO instead of ERROR."""
    wo = _wo(
        "McGill Curl-up: 3x10/Seite mit 7s Hold",
        coaching_notes="McGill auf 7s wegen RHR-Drift +4 bpm/7d zurückgenommen",
    )
    findings = check_exercise_regression([wo], _ctx())
    assert all(f.severity == "INFO" for f in findings if f.rule_id == "R016")


def test_r016_exempts_on_workout_coaching_notes_deload():
    wo = _wo(
        "McGill Curl-up: 3x10/Seite mit 7s Hold",
        coaching_notes="Deload week active — alle Holds um 1s reduziert",
    )
    findings = check_exercise_regression([wo], _ctx())
    assert all(f.severity == "INFO" for f in findings if f.rule_id == "R016")


def test_r016_exempts_on_line_level_last_cap():
    """Line-level 'Last-Cap aktiv' → INFO, not ERROR."""
    wo = _wo(
        "Farmer's Hold KB einarmig: 3x35s/Seite 30kg | Last-Cap aktiv | RPE 6"
    )
    findings = check_exercise_regression([wo], _ctx())
    farmer_findings = [f for f in findings if "Farmer" in f.message and f.rule_id == "R016"]
    assert farmer_findings
    assert all(f.severity == "INFO" for f in farmer_findings)


def test_r016_does_not_exempt_on_unrelated_held_words():
    """'gehalten' alone in coaching_notes (for OTHER exercise) does NOT
    exempt a real regression on this exercise. The canonical drift had
    'Farmer 32.5kg gehalten' in coaching_notes; that must not shield
    a McGill regression in the same workout."""
    wo = _wo(
        "McGill Curl-up: 3x10/Seite mit 7s Hold | Bracing\n"
        "Farmer's Hold KB einarmig: 3x35s/Seite 32.5kg | RPE 7 | Last gehalten",
        coaching_notes="Heavy-Grip-Kadenz 6d on-cadence: Farmer 32.5kg gehalten",
    )
    findings = check_exercise_regression([wo], _ctx())
    mcgill = [f for f in findings if "McGill" in f.message and f.rule_id == "R016"]
    assert mcgill
    assert mcgill[0].severity == "ERROR"


def test_r016_silent_when_progressions_missing():
    """Athletes without exercise_progressions.md → rule no-op."""
    ctx_empty = Context(target_date="2026-05-23", exercise_progressions="")
    wo = _wo("McGill Curl-up: 3x10/Seite mit 7s Hold")
    assert check_exercise_regression([wo], ctx_empty) == []
