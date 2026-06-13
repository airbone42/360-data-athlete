"""Tests for the shared surface vocabulary (app.utils.surface).

Covers review finding F5-05 (code part): docs mandate `forest-path`, but
R003 and the shoe advisor only knew the legacy `forstweg` spelling —
compliant plans drew a spurious R003 WARNING. Canonical tokens and legacy
read-aliases now live in one shared helper.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the scripts/ directory importable.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from app.graphs.shoe_advisor import _detect_terrain_from_context  # noqa: E402
from app.utils.surface import (  # noqa: E402
    CANONICAL_SURFACES,
    SURFACE_ALIASES,
    normalize_surface,
)
from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    check_surface_required,
)


# ─── normalize_surface ───────────────────────────────────────────────────

def test_canonical_tokens_pass_through():
    for token in CANONICAL_SURFACES:
        assert normalize_surface(token) == token


def test_normalize_is_case_insensitive():
    assert normalize_surface("Forest-Path") == "forest-path"


def test_legacy_aliases_map_to_canonical():
    assert normalize_surface("forstweg") == "forest-path"
    assert normalize_surface("weichboden") == "trail"
    assert normalize_surface("bahn") == "track"


def test_aliases_target_canonical_tokens_only():
    assert set(SURFACE_ALIASES.values()) <= CANONICAL_SURFACES


def test_unknown_and_empty_return_none():
    assert normalize_surface("gravelroad") is None
    assert normalize_surface("") is None
    assert normalize_surface(None) is None


# ─── R003 — surface field validation ─────────────────────────────────────

def _run(surface: str | None) -> dict:
    w = {"type": "Run", "name": "Easy Z2", "workout_type": "EASY"}
    if surface is not None:
        w["surface"] = surface
    return w


def _ctx() -> Context:
    return Context(target_date="2025-05-23")


def test_r003_forest_path_is_compliant():
    """The documented canonical token must not draw a WARNING (F5-05)."""
    assert check_surface_required([_run("forest-path")], _ctx()) == []


def test_r003_legacy_forstweg_still_accepted():
    assert check_surface_required([_run("forstweg")], _ctx()) == []


def test_r003_unknown_surface_warns():
    findings = check_surface_required([_run("gravelroad")], _ctx())
    assert len(findings) == 1
    assert findings[0].rule_id == "R003"
    assert findings[0].severity == "WARNING"


def test_r003_missing_surface_errors():
    findings = check_surface_required([_run(None)], _ctx())
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"


# ─── Shoe advisor terrain classification ─────────────────────────────────

def test_shoe_advisor_forest_path_is_asphalt_equivalent():
    assert _detect_terrain_from_context({"surface": "forest-path"}, "") == "asphalt"


def test_shoe_advisor_legacy_aliases_classify_identically():
    assert _detect_terrain_from_context({"surface": "forstweg"}, "") == "asphalt"
    assert _detect_terrain_from_context({"surface": "weichboden"}, "") == "trail"
    assert _detect_terrain_from_context({"surface": "bahn"}, "") == "track"


def test_shoe_advisor_canonical_trail_and_track():
    assert _detect_terrain_from_context({"surface": "trail"}, "") == "trail"
    assert _detect_terrain_from_context({"surface": "track"}, "") == "track"
