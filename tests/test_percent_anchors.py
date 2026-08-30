"""Tests for check_percent_anchors in audit_consistency.

The bug this guards against: a race HR curve filed as "% LTHR" keeps its
percentages after the threshold is revalidated, so the table silently
refers to a denominator that no longer exists. intervals.icu stores the
threshold in force at the time of each activity, which makes the claim
checkable.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import audit_consistency as ac


@pytest.fixture()
def isolated_configs(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    fb = tmp_path / "fallback"
    cd = tmp_path / "config"
    fb.mkdir()
    cd.mkdir()
    monkeypatch.setattr(ac, "CONFIG_FALLBACK", fb)
    monkeypatch.setattr(ac, "CONFIG_DIR", cd)
    return fb, cd


def _categories(findings: list[dict]) -> list[str]:
    return [f["category"] for f in findings]


# ── Marker-Parsing ───────────────────────────────────────────────────


def test_parses_anchor_with_line_number():
    text = "intro\n\n[hr-anchor:i69665243 lthr=154]\n\n| a | b |\n"
    anchors = ac._parse_hr_anchors(text)
    assert anchors == [
        {"activity_id": "i69665243", "declared_lthr": 154, "line": 3}
    ]


def test_parses_multiple_anchors_on_one_line():
    text = "[hr-anchor:i1 lthr=150] und [hr-anchor:i2 lthr=166]\n"
    assert [a["activity_id"] for a in ac._parse_hr_anchors(text)] == ["i1", "i2"]


def test_ignores_malformed_marker():
    # missing lthr= is not an anchor; a bare activity mention is not either
    text = "[hr-anchor:i69665243]\nsiehe i69665243\n"
    assert ac._parse_hr_anchors(text) == []


def test_parses_stated_denominator_variants():
    text = "| Abschnitt | % LTHR (166) |\n| x | %LTHR (154, korrekt) |\n"
    found = [d["lthr"] for d in ac._parse_stated_denominators(text)]
    assert found == [166, 154]


# ── Auswertung eines Ankers ──────────────────────────────────────────


def test_matching_lthr_is_no_finding():
    anchor = {"activity_id": "i1", "declared_lthr": 166, "line": 1}
    assert ac.evaluate_hr_anchor(anchor, {"lthr": 166}) is None


def test_mismatched_lthr_is_high():
    anchor = {"activity_id": "i69665243", "declared_lthr": 166, "line": 1}
    payload = ac.evaluate_hr_anchor(
        anchor, {"lthr": 154, "average_heartrate": 155, "max_heartrate": 163}
    )
    assert payload["severity"] == ac.HIGH
    assert payload["category"] == "percent_anchor_drift"
    assert "154" in payload["evidence"] and "166" in payload["evidence"]


def test_mismatch_names_the_impossible_max_hr():
    """maxHF below the declared threshold is the cheapest tell of drift."""
    anchor = {"activity_id": "i1", "declared_lthr": 166, "line": 1}
    payload = ac.evaluate_hr_anchor(
        anchor, {"lthr": 154, "average_heartrate": 155, "max_heartrate": 163}
    )
    assert "UNTER dem deklarierten LTHR" in payload["evidence"]


def test_mismatch_without_max_hr_still_reports():
    anchor = {"activity_id": "i1", "declared_lthr": 166, "line": 1}
    payload = ac.evaluate_hr_anchor(anchor, {"lthr": 154})
    assert payload["severity"] == ac.HIGH
    assert "UNTER dem deklarierten" not in payload["evidence"]


def test_max_hr_above_declared_lthr_omits_the_hint():
    anchor = {"activity_id": "i1", "declared_lthr": 154, "line": 1}
    payload = ac.evaluate_hr_anchor(
        anchor, {"lthr": 166, "average_heartrate": 160, "max_heartrate": 175}
    )
    assert "UNTER dem deklarierten" not in payload["evidence"]


def test_unreachable_activity_is_low_not_silent():
    anchor = {"activity_id": "i1", "declared_lthr": 166, "line": 1}
    payload = ac.evaluate_hr_anchor(anchor, None)
    assert payload["severity"] == ac.LOW
    assert payload["category"] == "percent_anchor_unverified"


def test_activity_without_lthr_field_is_low():
    anchor = {"activity_id": "i1", "declared_lthr": 166, "line": 1}
    payload = ac.evaluate_hr_anchor(anchor, {"lthr": None})
    assert payload["category"] == "percent_anchor_unverified"


# ── Ende-zu-Ende über die Configs ────────────────────────────────────


def test_clean_anchor_produces_no_findings(isolated_configs):
    _fb, cd = isolated_configs
    (cd / "athlete_status.md").write_text(
        "## HM-Profil\n\n[hr-anchor:i69665243 lthr=154]\n\n"
        "| Abschnitt | % LTHR (154) |\n|---|---|\n| Schluss | 104 % |\n",
        encoding="utf-8",
    )
    findings = ac.check_percent_anchors({"i69665243": {"lthr": 154}})
    assert findings == []


def test_drifted_anchor_is_reported_with_file_and_line(isolated_configs):
    _fb, cd = isolated_configs
    (cd / "athlete_status.md").write_text(
        "## HM-Profil\n\n[hr-anchor:i69665243 lthr=166]\n\n"
        "| Abschnitt | % LTHR (166) |\n|---|---|\n| Schluss | 96 % |\n",
        encoding="utf-8",
    )
    findings = ac.check_percent_anchors(
        {"i69665243": {"lthr": 154, "average_heartrate": 155, "max_heartrate": 163}}
    )
    assert _categories(findings) == ["percent_anchor_drift"]
    assert findings[0]["source_file"] == "config/athlete_status.md"
    assert findings[0]["source_line"] == 3
    assert findings[0]["severity"] == ac.HIGH


def test_percentage_without_anchor_is_flagged(isolated_configs):
    _fb, cd = isolated_configs
    (cd / "athlete_status.md").write_text(
        "| Abschnitt | % LTHR (166) |\n|---|---|\n| Schluss | 96 % |\n",
        encoding="utf-8",
    )
    findings = ac.check_percent_anchors({})
    assert _categories(findings) == ["percent_anchor_missing"]
    assert findings[0]["severity"] == ac.MEDIUM


def test_anchor_far_away_does_not_vouch_for_a_percentage(isolated_configs):
    """The marker belongs next to its table, not somewhere in the file."""
    _fb, cd = isolated_configs
    body = "[hr-anchor:i1 lthr=154]\n" + "filler\n" * 40 + "| x | % LTHR (166) |\n"
    (cd / "athlete_status.md").write_text(body, encoding="utf-8")
    findings = ac.check_percent_anchors({"i1": {"lthr": 154}})
    assert "percent_anchor_missing" in _categories(findings)


def test_wrapper_override_wins_over_framework_default(isolated_configs):
    fb, cd = isolated_configs
    (fb / "athlete_status.md").write_text(
        "[hr-anchor:i1 lthr=166]\n| x | % LTHR (166) |\n", encoding="utf-8"
    )
    (cd / "athlete_status.md").write_text(
        "[hr-anchor:i1 lthr=154]\n| x | % LTHR (154) |\n", encoding="utf-8"
    )
    findings = ac.check_percent_anchors({"i1": {"lthr": 154}})
    assert findings == []


def test_collect_ids_deduplicates_across_files(isolated_configs):
    fb, cd = isolated_configs
    (cd / "athlete_status.md").write_text(
        "[hr-anchor:i1 lthr=154]\n[hr-anchor:i2 lthr=166]\n", encoding="utf-8"
    )
    (fb / "competition_plan.md").write_text(
        "[hr-anchor:i1 lthr=154]\n", encoding="utf-8"
    )
    assert sorted(ac.collect_hr_anchor_ids()) == ["i1", "i2"]


def test_check_is_registered_online():
    assert ac.CHECK_MAP["PERCENT_ANCHORS"] == ("check_percent_anchors", True)


def test_bpm_band_in_parentheses_is_not_a_denominator():
    """`89–95 % LTHR (148–158)` states a beat range, not a threshold."""
    text = "HF-Band 89–95 % LTHR (148–158) statt der Deckel-Tabelle\n"
    assert ac._parse_stated_denominators(text) == []


def test_single_number_is_still_read_as_denominator():
    text = "| Abschnitt | % LTHR (166) |\n"
    assert [d["lthr"] for d in ac._parse_stated_denominators(text)] == [166]


def test_hyphen_range_also_ignored():
    text = "% LTHR (148-158)\n"
    assert ac._parse_stated_denominators(text) == []
