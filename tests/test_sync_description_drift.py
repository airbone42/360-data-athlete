"""Unit tests for scripts/sync_description_drift.py.

Covers the pure-Python pieces: section parsing, drift computation,
range-tolerance, and in-place line rewriting. The network-dependent
orchestration (`_sync`) is not exercised here.
"""
from __future__ import annotations

import json

import pytest

from scripts import sync_description_drift as sdd


# ── fixtures ─────────────────────────────────────────────────────────────────


PROGRESSIONS_FIXTURE = """\
# Übungs-Progressionen

## Grip

### Wrist Curls
- **Aktueller Stand:** 3×8 je Seite, 9 kg, RPE-Ziel 7–8 (21.04.2025)
- **Progression:** wenn 3×10 @ 9 kg @ RPE ≤6 → +1 kg

### Farmer's Hold (KB, einarmig)
- **Aktueller Stand:** 3×45s je Seite, 30 kg — RPE 7-8 (05.05.2025)
- **Hinweis:** Asymmetrische Last — Warm-up Pflicht ab 27.5 kg

### Pinch Grip Plates (Hantelscheiben)
- **Aktueller Stand:** 3×20s je Seite, 5 kg pro Hand — RPE 7 (08.05.2025)
- **Progression:** wenn RPE ≤6 → +2.5 kg

---

## Pull

### TRX Row
- **Aktueller Stand:** 3×12, 45° — RPE 8–9 (12.04.2025)
- **Hinweis:** Schulter beachten
"""


@pytest.fixture
def mapping() -> dict:
    """Use the real framework mapping (config.example) — keys are stable."""
    from app.utils.paths import resolve_config

    with open(resolve_config("exercise_muscle_mapping.json")) as f:
        data = json.load(f)
    data.pop("_meta", None)
    return data


# ── section parsing ─────────────────────────────────────────────────────────


def test_parse_sections_finds_all_headers():
    sections = sdd._parse_sections(PROGRESSIONS_FIXTURE)
    headers = [s.header for s in sections]
    assert "Wrist Curls" in headers
    assert "Farmer's Hold (KB, einarmig)" in headers
    assert "Pinch Grip Plates (Hantelscheiben)" in headers
    assert "TRX Row" in headers


def test_parse_sections_records_stand_line():
    sections = sdd._parse_sections(PROGRESSIONS_FIXTURE)
    by_header = {s.header: s for s in sections}
    sec = by_header["Wrist Curls"]
    assert sec.stand_line is not None
    line = PROGRESSIONS_FIXTURE.splitlines()[sec.stand_line]
    assert "**Aktueller Stand:**" in line


def test_parse_sections_h2_resets_current(mapping):
    """A `## Pull` header must close the previous section without leaking it."""
    sections = sdd._parse_sections(PROGRESSIONS_FIXTURE)
    # The Pinch Grip section must end before the "## Pull" header, not extend into it.
    pinch = next(s for s in sections if s.header.startswith("Pinch Grip"))
    pull_h2_line = next(
        i for i, line in enumerate(PROGRESSIONS_FIXTURE.splitlines())
        if line.strip().startswith("## Pull")
    )
    assert pinch.end_line <= pull_h2_line


# ── mapping lookup ──────────────────────────────────────────────────────────


def test_section_to_mapping_key_strips_parenthetical(mapping):
    key = sdd._section_mapping_key("Farmer's Hold (KB, einarmig)", mapping)
    # Alias matcher may pick `farmer_hold` or a more specific variant
    # (`farmer_hold_kb`). Either is acceptable — what matters is that the
    # parenthetical clarification did not block the lookup.
    assert key is not None and key.startswith("farmer_hold")


def test_section_to_mapping_key_handles_simple_name(mapping):
    key = sdd._section_mapping_key("Wrist Curls", mapping)
    assert key == "wrist_curl"


# ── formatting helpers ─────────────────────────────────────────────────────


def test_format_num_drops_trailing_zero():
    assert sdd._format_num(5.0) == "5"
    assert sdd._format_num(4.5) == "4.5"
    assert sdd._format_num(30.0) == "30"


def test_replace_weight_keeps_surrounding_text():
    line = "- **Aktueller Stand:** 3×20s je Seite, 5 kg pro Hand — RPE 7"
    out = sdd._replace_weight(line, 4.0)
    assert "4 kg pro Hand" in out
    assert "3×20s je Seite" in out  # not touched


def test_replace_sets_reps_for_timed_exercise():
    line = "- **Aktueller Stand:** 3×45s je Seite, 30 kg — RPE 7-8"
    out = sdd._replace_sets_reps_or_duration(line, sets=3, reps=None, duration_s=30.0)
    assert "3×30s je Seite" in out


def test_replace_sets_reps_for_rep_exercise():
    line = "- **Aktueller Stand:** 3×8 je Seite, 9 kg, RPE-Ziel 7–8"
    out = sdd._replace_sets_reps_or_duration(line, sets=3, reps=10.0, duration_s=None)
    assert "3×10 je Seite" in out


def test_stamp_date_replaces_trailing_de_date():
    line = "- **Aktueller Stand:** 3×8 je Seite, 9 kg (21.04.2025)"
    out = sdd._stamp_date(line, "13.05.2025", "i999")
    assert "(13.05.2025, i999, Athlet-Edit)" in out
    assert "21.04.2025" not in out


def test_stamp_date_appends_when_no_trailing_date():
    line = "- **Aktueller Stand:** 3×15, 20 kg — Pflicht alle 2 Tage"
    out = sdd._stamp_date(line, "13.05.2025", "i999")
    assert out.endswith("(13.05.2025, i999, Athlet-Edit)")
    assert "Pflicht alle 2 Tage" in out


# ── range tolerance ─────────────────────────────────────────────────────────


def test_has_range_weight():
    assert sdd._has_range("8–10 kg", 9.0, "weight") is True
    assert sdd._has_range("8–10 kg", 11.0, "weight") is False
    assert sdd._has_range("9 kg", 9.0, "weight") is False  # no range = no skip


def test_has_range_duration():
    assert sdd._has_range("30–45s", 35.0, "duration") is True
    assert sdd._has_range("30–45s", 50.0, "duration") is False


def test_has_range_reps():
    assert sdd._has_range("3×8–10", 9.0, "reps") is True
    assert sdd._has_range("3×8–10", 11.0, "reps") is False


# ── end-to-end drift computation ────────────────────────────────────────────


def _description_pinch_drop():
    """Simulated athlete edit: dropped from 5 kg to 4 kg."""
    return (
        "WARM-UP (5 min)\n"
        "Schulterkreisen: 2×10\n"
        "\n"
        "HAUPTTEIL\n"
        "Pinch Grip Plates: 3x20s je Seite, 4 kg pro Hand | RPE 7\n"
        "Wrist Curls: 3x8 je Seite, 9 kg | RPE 7\n"
    )


def test_compute_drifts_detects_weight_drop(mapping):
    drifts, no_section, unmapped = sdd.compute_drifts(
        description=_description_pinch_drop(),
        progressions_text=PROGRESSIONS_FIXTURE,
        mapping=mapping,
        activity_id="i12345",
        activity_date="2025-05-13",
    )
    # Pinch dropped 5 → 4 kg, Wrist Curls unchanged
    pinch_drifts = [d for d in drifts if "Pinch Grip" in d.section_header]
    wrist_drifts = [d for d in drifts if "Wrist Curl" in d.section_header]

    assert len(pinch_drifts) == 1
    assert len(wrist_drifts) == 0  # unchanged → no drift
    assert "5 kg → 4 kg" in pinch_drifts[0].changes[0] or any(
        "5" in c and "4" in c for c in pinch_drifts[0].changes
    )
    assert "4 kg pro Hand" in pinch_drifts[0].new_line
    assert "i12345" in pinch_drifts[0].new_line
    assert "Athlet-Edit" in pinch_drifts[0].new_line


def test_compute_drifts_respects_range(mapping):
    # Wrist Curls Aktueller Stand says "RPE-Ziel 7–8" but no rep range.
    # Modify fixture so the rep target has a range, then verify a value
    # inside the range does NOT trigger drift.
    fx = PROGRESSIONS_FIXTURE.replace(
        "**Aktueller Stand:** 3×8 je Seite, 9 kg",
        "**Aktueller Stand:** 3×8–10 je Seite, 9 kg",
    )
    desc = "Wrist Curls: 3x9 je Seite, 9 kg | RPE 7\n"
    drifts, _, _ = sdd.compute_drifts(
        description=desc,
        progressions_text=fx,
        mapping=mapping,
        activity_id="i777",
        activity_date="2025-05-13",
    )
    wrist = [d for d in drifts if "Wrist" in d.section_header]
    assert wrist == [], "9 reps is within 8–10 range — should not drift"


def test_compute_drifts_detects_out_of_range(mapping):
    fx = PROGRESSIONS_FIXTURE.replace(
        "**Aktueller Stand:** 3×8 je Seite, 9 kg",
        "**Aktueller Stand:** 3×8–10 je Seite, 9 kg",
    )
    desc = "Wrist Curls: 3x12 je Seite, 9 kg | RPE 6\n"
    drifts, _, _ = sdd.compute_drifts(
        description=desc,
        progressions_text=fx,
        mapping=mapping,
        activity_id="i777",
        activity_date="2025-05-13",
    )
    wrist = [d for d in drifts if "Wrist" in d.section_header]
    assert len(wrist) == 1, "12 reps is above 10 — should drift"


def test_compute_drifts_detects_hold_progression(mapping):
    """TUT-progression drift pattern: stand-line says 2s Hold, activity
    description shows 3s Hold. Parser must lift the hold value into the
    stand-line, swapping `2s Hold` → `3s Hold`.
    """
    fx = """\
### Gripmaster Fingers (bilateral)
- **Aktueller Stand:** 3×20 Wdh, 2s Hold am Druckpunkt — RPE 5–6 (21.04.2025)
- **Progression:** TUT primaer
"""
    desc = "Gripmaster Fingers: 3x20 | 3s Hold am Endpunkt (Progression von 2s -> 3s). Alle 4 Finger.\n"
    drifts, _, _ = sdd.compute_drifts(
        description=desc,
        progressions_text=fx,
        mapping=mapping,
        activity_id="i555",
        activity_date="2025-04-30",
    )
    gm = [d for d in drifts if "Gripmaster" in d.section_header]
    assert len(gm) == 1, "Hold drift 2s → 3s should fire"
    assert any("Hold: 2s → 3s" in c for c in gm[0].changes)
    assert "3s Hold am Druckpunkt" in gm[0].new_line
    assert "2s Hold" not in gm[0].new_line
    # Date stamp updated to activity date
    assert "30.04.2025" in gm[0].new_line
    # Surrounding qualifier preserved
    assert "am Druckpunkt" in gm[0].new_line
    # RPE part preserved
    assert "RPE 5–6" in gm[0].new_line


def test_compute_drifts_reports_unmapped(mapping):
    desc = "Squishy Mango Crush: 3x15, 4 kg\n"
    drifts, _, unmapped = sdd.compute_drifts(
        description=desc,
        progressions_text=PROGRESSIONS_FIXTURE,
        mapping=mapping,
        activity_id="i1",
        activity_date="2025-05-13",
    )
    assert drifts == []
    assert any("mango" in u.lower() or "squishy" in u.lower() for u in unmapped)


# ── apply_drifts (file IO simulation) ───────────────────────────────────────


def test_apply_drifts_only_touches_stand_line(mapping):
    drifts, _, _ = sdd.compute_drifts(
        description=_description_pinch_drop(),
        progressions_text=PROGRESSIONS_FIXTURE,
        mapping=mapping,
        activity_id="i999",
        activity_date="2025-05-13",
    )
    assert drifts, "expected at least one drift"

    new_text = sdd._apply_drifts(PROGRESSIONS_FIXTURE, drifts)

    old_lines = PROGRESSIONS_FIXTURE.splitlines()
    new_lines = new_text.splitlines()
    assert len(old_lines) == len(new_lines)

    # Exactly the stand-line(s) of drifted sections should differ.
    drifted_indices = {d.stand_line_idx for d in drifts}
    for i, (a, b) in enumerate(zip(old_lines, new_lines)):
        if i in drifted_indices:
            assert a != b, f"line {i} should have changed"
        else:
            assert a == b, f"line {i} should be untouched (was: {a!r})"


def test_apply_drifts_preserves_form_notes(mapping):
    drifts, _, _ = sdd.compute_drifts(
        description="Farmer's Hold KB: 3x45s je Seite, 27.5 kg | RPE 8\n",
        progressions_text=PROGRESSIONS_FIXTURE,
        mapping=mapping,
        activity_id="i555",
        activity_date="2025-05-13",
    )
    assert drifts, "weight drop 30 → 27.5 kg should drift"
    new_text = sdd._apply_drifts(PROGRESSIONS_FIXTURE, drifts)
    # The Hinweis line directly below the Farmer's Hold stand-line must survive verbatim.
    assert "Asymmetrische Last — Warm-up Pflicht ab 27.5 kg" in new_text
