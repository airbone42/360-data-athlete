"""Tests for R024 — tag-content adequacy (check_tag_content_adequacy)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validate_plan import Context, check_tag_content_adequacy

TAG_MAP = {
    "grip": {
        "min_exercises": 2,
        "exercises": ["Farmer Hold", "Dead Hang", "Pinch Grip", "Wrist Curl"],
    },
    "core": {"min_exercises": 2, "exercises": ["Plank", "Pallof", "Dead Bug"]},
    "plyo": {"min_exercises": 1, "exercises": ["Pogo", "Box Jump"]},
}


def _ctx(tag_map: dict | None = TAG_MAP) -> Context:
    return Context(target_date="2025-05-08", tag_content_map=tag_map or {})


def _w(tags: list[str], description: str, name: str = "Test-Workout") -> dict:
    return {"name": name, "type": "Workout", "tags": tags, "description": description}


def test_underfilled_tag_warns() -> None:
    """The canonical incident: grip tag with a single Farmer Hold."""
    w = _w(["core", "grip"], "Farmer Hold: 3x30s @ 24kg\n\nPlank: 3x45s\n\nPallof Press: 3x10")
    findings = check_tag_content_adequacy([w], _ctx())
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "R024" and "grip" in f.message
    assert "1/2" in f.message


def test_adequate_tags_pass() -> None:
    w = _w(["grip", "core"], "Farmer Hold 3x30s\n\nDead Hang 3x45s\n\nPlank 3x60s\n\nDead Bug 3x10")
    assert check_tag_content_adequacy([w], _ctx()) == []


def test_min_one_tag_passes_with_single_hit() -> None:
    w = _w(["plyo"], "Pogo Hops: 2x10, RPE 6")
    assert check_tag_content_adequacy([w], _ctx()) == []


def test_unmapped_tag_ignored() -> None:
    w = _w(["run"], "60min Z2")
    assert check_tag_content_adequacy([w], _ctx()) == []


def test_empty_map_disables_rule() -> None:
    w = _w(["grip"], "irgendwas ohne Grip-Inhalt")
    assert check_tag_content_adequacy([w], _ctx(tag_map={})) == []


def test_empty_description_skipped() -> None:
    w = _w(["grip"], "")
    assert check_tag_content_adequacy([w], _ctx()) == []


def test_matching_is_case_insensitive() -> None:
    w = _w(["grip"], "FARMER HOLD 3x30s\n\ndead hang 3x45s")
    assert check_tag_content_adequacy([w], _ctx()) == []


def test_duplicate_whitelist_hits_count_once() -> None:
    """Two Farmer-Hold lines are still ONE distinct grip exercise."""
    w = _w(["grip"], "Farmer Hold links 3x30s\n\nFarmer Hold rechts 3x30s")
    findings = check_tag_content_adequacy([w], _ctx())
    assert len(findings) == 1 and "1/2" in findings[0].message
