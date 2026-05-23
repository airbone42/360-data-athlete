"""Regression tests for the strava_apply.py description validators
(elevation drift + raw-HR citations)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Import strava_apply as a module without invoking main()
spec = importlib.util.spec_from_file_location(
    "strava_apply",
    str(ROOT / "scripts" / "strava_apply.py"),
)
assert spec is not None and spec.loader is not None
strava_apply = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strava_apply)


def test_extract_elevation_citations_finds_hoehenmeter() -> None:
    desc = "Strecken-Profil ist substanziell: rund 260 Höhenmeter insgesamt."
    assert 260 in strava_apply._extract_elevation_citations(desc)


def test_extract_elevation_citations_finds_m_with_anchor() -> None:
    desc = "Auf welligem Profil mit 117 m positiver Anstieg gelaufen."
    assert 117 in strava_apply._extract_elevation_citations(desc)


def test_extract_elevation_citations_finds_m_insgesamt() -> None:
    desc = "rund 260 m insgesamt auf dem Loop."
    assert 260 in strava_apply._extract_elevation_citations(desc)


def test_extract_elevation_citations_ignores_distance_meters() -> None:
    """`160 m Sprint` and pace tokens should not match — only elevation
    keywords trigger."""
    desc = "150 m Sprint am Schluss, Pace 5:25/km, 32 m Stride length."
    cited = strava_apply._extract_elevation_citations(desc)
    assert cited == []


def test_extract_elevation_citations_ignores_pace_tokens() -> None:
    desc = "Tempo 5:25/km, average 4.79 m/s, 60 min moving time."
    cited = strava_apply._extract_elevation_citations(desc)
    assert cited == []


def test_extract_elevation_citations_finds_dplus() -> None:
    desc = "Bergauf-Stride mit 388 m D+ über den Loop."
    assert 388 in strava_apply._extract_elevation_citations(desc)


# ---------------------------------------------------------------------------
# Raw HR citation detection — Strava insights must use zone language only
# ---------------------------------------------------------------------------


def test_extract_hr_citations_finds_bpm() -> None:
    desc = "132 bpm Durchschnitt, kein Drift über die Mitte hinaus."
    cited = strava_apply._extract_hr_citations(desc)
    assert any("132 bpm" in c.lower() for c in cited)


def test_extract_hr_citations_finds_avg_hr() -> None:
    desc = "Avg HR 132, max 137 — Z2-Decke gehalten."
    cited = strava_apply._extract_hr_citations(desc)
    assert any("avg hr 132" in c.lower() for c in cited)


def test_extract_hr_citations_finds_hf_label() -> None:
    desc = "HF 145 im Bergauf-Segment."
    cited = strava_apply._extract_hr_citations(desc)
    assert any("hf 145" in c.lower() for c in cited)


def test_extract_hr_citations_finds_bpm_delta() -> None:
    desc = "Heute +2 bpm avg HR vs. gestern auf gleicher Strecke."
    cited = strava_apply._extract_hr_citations(desc)
    assert any("+2 bpm" in c.lower() for c in cited)


def test_extract_hr_citations_ignores_zone_language() -> None:
    desc = (
        "Z2-Decke gehalten, kein Z3-Drift im Hauptteil. "
        "5:23/km auf Z2-Range mit 117 m positivem Anstieg laut Strava."
    )
    assert strava_apply._extract_hr_citations(desc) == []


def test_extract_hr_citations_ignores_unrelated_numbers() -> None:
    """TRIMP, step length, vertical oscillation must not trigger HR check."""
    desc = (
        "TRIMP 41 — Step length 1063 mm, vertikale Oszillation 106 mm. "
        "VO 87 mm vs 108 mm im Recovery-Trab."
    )
    assert strava_apply._extract_hr_citations(desc) == []


# ---------------------------------------------------------------------------
# v2 patterns (2026-05-23) — drift incident: "HR zwischen 124 und 132" and
# "(+0,5 bpm)" slipped through the v1 patterns and shipped to Strava. The
# v2 patterns add (a) connector-words between the HR keyword and the digit,
# (b) decimal/comma values before the bpm suffix.
# ---------------------------------------------------------------------------


def test_extract_hr_citations_v2_hr_zwischen() -> None:
    desc = "stabiler HR zwischen 124 und 132 trotz Höhenmeter"
    cited = strava_apply._extract_hr_citations(desc)
    assert any("hr zwischen 124" in c.lower() for c in cited), cited


def test_extract_hr_citations_v2_hr_von_bis() -> None:
    desc = "HR von 124 bis 132 stabil"
    cited = strava_apply._extract_hr_citations(desc)
    assert any("hr von 124" in c.lower() for c in cited), cited


def test_extract_hr_citations_v2_decimal_bpm() -> None:
    desc = "minimal Drift (+0,5 bpm) trotz Höhenmeter"
    cited = strava_apply._extract_hr_citations(desc)
    assert any("0,5 bpm" in c.lower() for c in cited), cited


def test_extract_hr_citations_v2_dot_decimal_bpm() -> None:
    desc = "Drift 0.5 bpm"
    cited = strava_apply._extract_hr_citations(desc)
    assert any("0.5 bpm" in c.lower() for c in cited), cited


def test_extract_hr_citations_v2_no_space_bpm() -> None:
    desc = "132bpm Spitzenwert"
    cited = strava_apply._extract_hr_citations(desc)
    assert any("132bpm" in c.lower() for c in cited), cited


def test_validate_raw_hr_exits_on_leak() -> None:
    import pytest as _pytest
    with _pytest.raises(SystemExit) as exc:
        strava_apply._validate_raw_hr("Drift +2 bpm trotz Tempo")
    assert exc.value.code == 2


def test_validate_raw_hr_silent_on_clean() -> None:
    # No raise → silent pass
    strava_apply._validate_raw_hr("Z2-Decke gehalten, klare aerobe Reserve")


# ---------------------------------------------------------------------------
# Footer-integrity check (validate_description) — added 2026-05-23 after
# a re-push briefing dropped the canonical footer URL.
# ---------------------------------------------------------------------------


def _body_with_footer(content: str = "Test body line") -> str:
    from app.utils.strava_titles import INSIGHTS_ANCHOR
    return f"{content}\n\nFooting {INSIGHTS_ANCHOR}"


def test_validate_description_passes_with_footer() -> None:
    strava_apply._validate_description(_body_with_footer())


def test_validate_description_errors_on_missing_footer() -> None:
    import pytest as _pytest
    with _pytest.raises(SystemExit) as exc:
        strava_apply._validate_description("Test body line without footer")
    assert exc.value.code == 2


def test_validate_description_errors_on_collapsed_footer() -> None:
    """Degraded footer ('by 360° Data Athlete' alone, no URL) must be
    refused — the canonical anchor includes the URL."""
    from app.utils.strava_titles import INSIGHTS_ANCHOR
    import pytest as _pytest
    if "(https://" in INSIGHTS_ANCHOR:
        with _pytest.raises(SystemExit) as exc:
            strava_apply._validate_description(
                "Test body line\n\nFooting by 360° Data Athlete"
            )
        assert exc.value.code == 2


def test_validate_description_errors_on_duplicate_footer() -> None:
    """Two footers in one body would publish twice — refused."""
    from app.utils.strava_titles import INSIGHTS_ANCHOR
    import pytest as _pytest
    with _pytest.raises(SystemExit) as exc:
        strava_apply._validate_description(
            f"line\n\nFooting {INSIGHTS_ANCHOR}\n\nAlso footing {INSIGHTS_ANCHOR}"
        )
    assert exc.value.code == 2


def test_validate_description_silent_on_empty() -> None:
    """Empty / whitespace-only description (e.g. title-only push) does
    not trigger the footer check."""
    strava_apply._validate_description("")
    strava_apply._validate_description("   \n  ")
