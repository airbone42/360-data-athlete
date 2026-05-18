"""Tests for check_override_drift in audit_consistency.

These tests use temporary directories to control CONFIG_DIR and
CONFIG_FALLBACK in isolation. They do NOT rely on the real
framework/config.example/ or config/ contents.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import audit_consistency as ac


@pytest.fixture()
def isolated_configs(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    """Point CONFIG_DIR and CONFIG_FALLBACK at empty tmp dirs."""
    fb = tmp_path / "fallback"
    cd = tmp_path / "config"
    fb.mkdir()
    cd.mkdir()
    monkeypatch.setattr(ac, "CONFIG_FALLBACK", fb)
    monkeypatch.setattr(ac, "CONFIG_DIR", cd)
    return fb, cd


def _categories(findings: list[dict]) -> list[str]:
    return [f["category"] for f in findings]


def test_no_drift_when_only_clean_framework(isolated_configs):
    fb, _cd = isolated_configs
    (fb / "training_paradigms.md").write_text(
        "# Trainingsparadigmen\n\n## Polarized\n- 80/20 Z1/Z2 vs Z4/Z5\n",
        encoding="utf-8",
    )
    (fb / "exercise_progressions.md").write_text(
        "# Übungs-Progressionen\n\n## Grip\n\n### KB Horn Pinch\n- Progression: Hold-Zeit steigern\n",
        encoding="utf-8",
    )
    findings = ac.check_override_drift()
    assert findings == [], f"Expected no findings, got {_categories(findings)}"


def test_framework_leak_detects_raw_bpm(isolated_configs):
    fb, _cd = isolated_configs
    (fb / "training_paradigms.md").write_text(
        "# Paradigmen\n\n## Zonen\n- Z2: 126–139 bpm — Grundlage\n",
        encoding="utf-8",
    )
    findings = ac.check_override_drift()
    assert any(f["category"] == "framework_leak" for f in findings)
    leak = next(f for f in findings if f["category"] == "framework_leak")
    assert "raw HR range" in leak["evidence"]
    assert "126–139 bpm" in leak["evidence"]


def test_framework_leak_skipped_when_reference_present(isolated_configs):
    """`athlete_static.md` nearby = legitimate reference, not a leak."""
    fb, _cd = isolated_configs
    (fb / "training_paradigms.md").write_text(
        "# Paradigmen\n\n## Zonen\n"
        "- Genaue BPM siehe `athlete_static.md` — Beispielwert wäre 126–139 bpm.\n",
        encoding="utf-8",
    )
    findings = ac.check_override_drift()
    assert not any(f["category"] == "framework_leak" for f in findings), \
        "Leak should be skipped when 'athlete_static.md' is in context"


def test_pointless_override_detected(isolated_configs):
    fb, cd = isolated_configs
    content = "# Paradigmen\n\n## Polarized\n- 80/20\n"
    (fb / "training_paradigms.md").write_text(content, encoding="utf-8")
    (cd / "training_paradigms.md").write_text(content, encoding="utf-8")
    findings = ac.check_override_drift()
    assert any(f["category"] == "pointless_override" for f in findings)


def test_wrapper_missing_section_detected(isolated_configs):
    fb, cd = isolated_configs
    (fb / "training_paradigms.md").write_text(
        "# Paradigmen\n\n## Polarized\n- 80/20\n\n## Pyramidal\n- 70/15/10\n",
        encoding="utf-8",
    )
    (cd / "training_paradigms.md").write_text(
        "# Paradigmen\n\n## Polarized\n- 80/20 (athlete-specific tweak)\n",
        encoding="utf-8",
    )
    findings = ac.check_override_drift()
    missing = [f for f in findings if f["category"] == "wrapper_missing_section"]
    assert missing, "Should detect missing 'Pyramidal' section"
    assert "Pyramidal" in missing[0]["evidence"]


def test_missing_tracking_for_exercise_progressions(isolated_configs):
    fb, cd = isolated_configs
    (fb / "exercise_progressions.md").write_text(
        "# Progressionen\n\n## Grip\n\n### KB Horn Pinch\n- Progression: Hold-Zeit\n",
        encoding="utf-8",
    )
    # Wrapper without any "Aktueller Stand:" entry — same structure
    (cd / "exercise_progressions.md").write_text(
        "# Progressionen\n\n## Grip\n\n### KB Horn Pinch\n- Progression: Hold-Zeit\n"
        "- **Hinweis:** Athlet bevorzugt KB statt Steckscheiben\n",
        encoding="utf-8",
    )
    findings = ac.check_override_drift()
    tracking = [f for f in findings if f["category"] == "missing_tracking"]
    assert tracking, "Should warn that wrapper override has no tracking entries"


def test_tracking_present_in_wrapper_no_warning(isolated_configs):
    fb, cd = isolated_configs
    (fb / "exercise_progressions.md").write_text(
        "# Progressionen\n\n## Grip\n\n### KB Horn Pinch\n- Progression: Hold-Zeit\n",
        encoding="utf-8",
    )
    (cd / "exercise_progressions.md").write_text(
        "# Progressionen\n\n## Grip\n\n### KB Horn Pinch\n"
        "- **Aktueller Stand:** 3×20s je Seite, 4 kg — RPE 6\n"
        "- Progression: Hold-Zeit\n",
        encoding="utf-8",
    )
    findings = ac.check_override_drift()
    assert not any(f["category"] == "missing_tracking" for f in findings)


def test_wrapper_dated_heading_matches_framework_generic(isolated_configs):
    """Wrapper-Heading mit Datums-/KW-Annotation matcht generische Framework-Variante."""
    fb, cd = isolated_configs
    (fb / "training_paradigms.md").write_text(
        "# Paradigmen\n\n"
        "## Bein-Block (1×/Woche)\n- foo\n\n"
        "## Kadenz (KEINE Vorgabe mehr in Workouts):\n- bar\n\n"
        "## Tägliche Balance-Routine (permanent)\n- baz\n\n"
        "## Maximalkraft-Übungen\n- qux\n",
        encoding="utf-8",
    )
    (cd / "training_paradigms.md").write_text(
        "# Paradigmen\n\n"
        "## Bein-Block (1×/Woche, ab KW42 = 14.10.2025)\n- foo + tweak\n\n"
        "## Kadenz (Stand 01.03.2025 — KEINE Vorgabe mehr in Workouts):\n- bar + tweak\n\n"
        "## Tägliche Balance-Routine (ab 15.02.2025, permanent)\n- baz + tweak\n\n"
        "## Maximalkraft-Übungen (Update 10.01.2025)\n- qux + tweak\n",
        encoding="utf-8",
    )
    findings = ac.check_override_drift()
    missing = [f for f in findings if f["category"] == "wrapper_missing_section"]
    assert not missing, (
        f"Wrapper dated-heading-Varianten sollten zu Framework-generic matchen, "
        f"aber Check meldet missing: {missing}"
    )


def test_normalize_heading_strips_dates_and_kw():
    """Direkter Unit-Test des Normalisierers."""
    assert ac._normalize_heading("Bein-Block (1×/Woche, ab KW42 = 14.10.2025)") \
        == "Bein-Block (1×/Woche)"
    assert ac._normalize_heading("Kadenz (Stand 01.03.2025 — KEINE Vorgabe mehr in Workouts):") \
        == "Kadenz (KEINE Vorgabe mehr in Workouts)"
    assert ac._normalize_heading("Tägliche Balance-Routine (ab 15.02.2025, permanent)") \
        == "Tägliche Balance-Routine (permanent)"
    assert ac._normalize_heading("Maximalkraft-Übungen (Update 10.01.2025)") \
        == "Maximalkraft-Übungen"
    # Bereits clean — Idempotenz
    assert ac._normalize_heading("Polarized") == "Polarized"


def test_aktueller_stand_in_framework_is_a_leak(isolated_configs):
    fb, _cd = isolated_configs
    (fb / "exercise_progressions.md").write_text(
        "# Progressionen\n\n### KB Horn Pinch\n"
        "- **Aktueller Stand:** 3×20s je Seite, 4 kg — RPE 6\n",
        encoding="utf-8",
    )
    findings = ac.check_override_drift()
    leaks = [f for f in findings if f["category"] == "framework_leak"]
    assert any("Aktueller-Stand" in f["evidence"] for f in leaks)
