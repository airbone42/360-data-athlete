"""Tests for the `--leg-conflict` swap in `get_balance_rotation.py`.

Covers the leg-conflict routing rule in framework/CLAUDE.md: pool exercises
flagged `leg_conflict: true` (slow-eccentric leg loading, e.g. a TRX-assisted
single-leg squat) must be swapped for a pure stability drill when the head
coach sets the flag — i.e. when today already carries a leg-strength block or
TOMORROW carries a leg-driven quality / long session (>=48h DOMS spacing).
Previously the pool carried this only as a conditional trailing note rendered
verbatim into the athlete-facing event; the swap now happens mechanically.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from scripts import get_balance_rotation as gbr

_TODAY = date(2026, 8, 6)


def _pool(**session_over) -> dict:
    """Minimal synthetic pool: one neutral exercise, one leg_conflict exercise
    WITH a declared fallback, one leg_conflict exercise WITHOUT one."""
    session = {
        "name": "Synthetic Balance Session",
        "duration_min": 10,
        "activation_header": "AKTIVIERUNG",
        "activation": [{"name": "Warmup Drill", "text": "2x10 — easy"}],
        "main_header": "HAUPTTEIL",
        "exercises": [
            {"name": "Stepping-Stone Path", "text": "3x40s | Ziel: S2-S3", "equipment": []},
            {
                "name": "TRX Assisted Single-Leg Squat",
                "text": "3x5/Seite | Ziel: S2-S3",
                "equipment": ["trx"],
                "leg_conflict": True,
                "leg_conflict_fallback": {
                    "name": "Einbeinstand Augen zu",
                    "text": "3x30s/Seite | Ziel: S2-S3 — reiner Stabilitätsdrill",
                    "equipment": [],
                },
            },
            {
                "name": "Slow Step-Down",
                "text": "3x6/Seite | Ziel: S2",
                "equipment": [],
                "leg_conflict": True,
                # no leg_conflict_fallback declared
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


def test_unflagged_exercise_passes_through_unchanged(synthetic_pool):
    _, workout = gbr.build_rotation_workout(_TODAY, leg_conflict=True)
    assert "Stepping-Stone Path: 3x40s | Ziel: S2-S3" in workout["description"]


def test_flag_swaps_leg_conflict_exercise_for_declared_fallback(synthetic_pool):
    _, workout = gbr.build_rotation_workout(_TODAY, leg_conflict=True)
    desc = workout["description"]
    assert "Einbeinstand Augen zu: 3x30s/Seite" in desc
    assert "TRX Assisted Single-Leg Squat:" not in desc


def test_missing_fallback_produces_generic_substitute_and_note(synthetic_pool):
    _, workout = gbr.build_rotation_workout(_TODAY, leg_conflict=True)
    desc = workout["description"]
    assert "Slow Step-Down:" not in desc
    assert "(Bein-Konflikt-Ersatz)" in desc
    assert "No leg_conflict_fallback declared for 'Slow Step-Down'" in desc


def test_marker_present_when_flag_set(synthetic_pool):
    _, workout = gbr.build_rotation_workout(_TODAY, leg_conflict=True)
    assert gbr.LEG_CONFLICT_MARKER in workout["description"]


def test_original_exercises_and_no_marker_when_flag_unset(synthetic_pool):
    _, workout = gbr.build_rotation_workout(_TODAY, leg_conflict=False)
    desc = workout["description"]
    assert gbr.LEG_CONFLICT_MARKER not in desc
    assert "TRX Assisted Single-Leg Squat: 3x5/Seite" in desc
    assert "Slow Step-Down: 3x6/Seite" in desc


def test_leg_conflict_composes_with_travel(synthetic_pool):
    # Leg-conflict runs first; travel then strips equipment from what remains.
    # The declared fallback here is equipment-free, so it must survive travel
    # mode untouched — and both markers must be present.
    _, workout = gbr.build_rotation_workout(_TODAY, travel=True, leg_conflict=True)
    desc = workout["description"]
    assert gbr.LEG_CONFLICT_MARKER in desc
    assert gbr.TRAVEL_MODE_MARKER in desc
    assert "Einbeinstand Augen zu: 3x30s/Seite" in desc
    assert "TRX Assisted Single-Leg Squat:" not in desc
