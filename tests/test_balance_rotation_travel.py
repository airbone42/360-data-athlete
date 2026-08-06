"""Tests for the `--travel` / `--no-equipment` equipment swap in
`get_balance_rotation.py`.

Covers the "Equipment availability (travel / limited kit)" rule in
framework/CLAUDE.md: equipment-dependent pool exercises (balance board /
kettlebell / TRX) must be swapped for a bodyweight / soft-surface fallback
when the athlete is travelling, so the auto-balance push never contains an
exercise the athlete cannot perform.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from scripts import get_balance_rotation as gbr

_TODAY = date(2026, 8, 6)


def _pool(**session_over) -> dict:
    """A minimal synthetic pool with one session (rotation key matching
    `_TODAY.toordinal() % 4`), containing one no-equipment exercise, one
    equipment exercise WITH a declared fallback, and one equipment exercise
    WITHOUT a fallback.
    """
    session = {
        "name": "Synthetic Balance Session",
        "duration_min": 10,
        "activation_header": "AKTIVIERUNG",
        "activation": [{"name": "Warmup Drill", "text": "2x10 — easy"}],
        "main_header": "HAUPTTEIL",
        "exercises": [
            {"name": "Bodyweight Hold", "text": "3x30s | Ziel: S2", "equipment": []},
            {
                "name": "Balance Board Single-Leg",
                "text": "2x20s | Ziel: S2-S3",
                "equipment": ["balance_board"],
                "travel_fallback": {
                    "name": "Towel Single-Leg",
                    "text": "2x20s on folded towel | Ziel: S2-S3",
                    "equipment": [],
                },
            },
            {
                "name": "TRX Assisted Squat",
                "text": "3x5 | Ziel: S2",
                "equipment": ["trx"],
                # no travel_fallback declared
            },
        ],
    }
    session.update(session_over)
    rotation_key = gbr.ROTATION_KEYS[_TODAY.toordinal() % 4]
    return {"sessions": {rotation_key: session}}


@pytest.fixture()
def synthetic_pool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    pool = _pool()
    pool_path = tmp_path / "balance_pool.json"
    pool_path.write_text(json.dumps(pool), encoding="utf-8")
    monkeypatch.setattr(gbr, "_pool_path", lambda: str(pool_path))
    return pool


def test_no_equipment_exercise_passes_through_unchanged(synthetic_pool):
    """(b) An exercise with no `equipment` (or an empty list) is untouched by
    travel mode."""
    _, workout = gbr.build_rotation_workout(_TODAY, travel=True)
    assert "Bodyweight Hold: 3x30s | Ziel: S2" in workout["description"]


def test_travel_flag_swaps_equipment_exercise_for_declared_fallback(synthetic_pool):
    """(a) An equipment exercise with a declared `travel_fallback` is
    replaced by that fallback, not by the original."""
    _, workout = gbr.build_rotation_workout(_TODAY, travel=True)
    desc = workout["description"]
    assert "Towel Single-Leg: 2x20s on folded towel | Ziel: S2-S3" in desc
    assert "Balance Board Single-Leg:" not in desc


def test_missing_fallback_produces_generic_substitute_and_note(synthetic_pool):
    """(c) An equipment exercise without a declared `travel_fallback` is
    replaced by the generic single-leg / soft-surface substitute, and a
    coach-facing note about the substitution appears in the output."""
    _, workout = gbr.build_rotation_workout(_TODAY, travel=True)
    desc = workout["description"]
    assert "TRX Assisted Squat:" not in desc
    assert "(Travel-Ersatz)" in desc
    assert "instabiler weicher Unterlage" in desc
    assert "No travel_fallback declared for 'TRX Assisted Squat'" in desc


def test_travel_marker_present_in_description_when_flag_set(synthetic_pool):
    """The workout description must carry a visible marker so the coach sees
    why the exercises differ from the standard rotation."""
    _, workout = gbr.build_rotation_workout(_TODAY, travel=True)
    assert gbr.TRAVEL_MODE_MARKER in workout["description"]


def test_no_travel_marker_and_original_exercises_when_flag_unset(synthetic_pool):
    _, workout = gbr.build_rotation_workout(_TODAY, travel=False)
    desc = workout["description"]
    assert gbr.TRAVEL_MODE_MARKER not in desc
    assert "Balance Board Single-Leg: 2x20s | Ziel: S2-S3" in desc
    assert "TRX Assisted Squat: 3x5 | Ziel: S2" in desc
    assert "(Travel-Ersatz)" not in desc


def test_apply_travel_mode_unit_level():
    """Direct unit coverage of `_apply_travel_mode` independent of file I/O."""
    exercises = [
        {"name": "Bodyweight", "text": "x", "equipment": []},
        {
            "name": "KB Reach",
            "text": "y",
            "equipment": ["kettlebell"],
            "travel_fallback": {"name": "Reach no load", "text": "y2", "equipment": []},
        },
        {"name": "Board Hold", "text": "z", "equipment": ["balance_board"]},
    ]
    result, notes = gbr._apply_travel_mode(exercises)
    assert result[0] == exercises[0]  # untouched
    assert result[1]["name"] == "Reach no load"  # declared fallback used
    assert result[2]["name"] == "Board Hold (Travel-Ersatz)"  # generic substitute
    assert result[2]["equipment"] == []
    assert len(notes) == 1
    assert "Board Hold" in notes[0]


def test_legacy_description_only_schema_renders_verbatim():
    """Consumer pools may still use the pre-structured schema — the opaque
    description must pass through unchanged, never an empty skeleton."""
    from get_balance_rotation import _render_description, TRAVEL_MODE_MARKER

    session = {
        "name": "Legacy A",
        "duration_min": 10,
        "description": "AKTIVIERUNG\n\nEinbeinstand: 2x30s je Seite",
    }
    plain = _render_description(session, travel=False)
    assert plain == session["description"]

    travel = _render_description(session, travel=True)
    assert travel.startswith(TRAVEL_MODE_MARKER)
    assert session["description"] in travel
    assert "could NOT be auto-swapped" in travel
