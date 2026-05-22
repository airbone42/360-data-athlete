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
