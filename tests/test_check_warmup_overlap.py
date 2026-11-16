"""Warm-up overlap detector: real duplicates count, deliberate omissions do not."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from check_warmup_overlap import detect_overlaps, find_drills  # noqa: E402


def test_dosed_drill_is_found() -> None:
    assert find_drills("Cat-Cow 2x8") == {"Cat-Cow"}


def test_prose_without_dose_is_ignored() -> None:
    assert find_drills("A-Skips folgen im Lauf-WU") == set()


def test_negated_reference_with_dose_is_ignored() -> None:
    text = (
        "WARM-UP (5 min)\n"
        "Cat-Cow und Glute Bridge laufen heute schon im Bein-Warm-up (5 min) — hier deshalb nicht doppelt\n"
        "Band Pull-Apart 2x15\n"
    )
    assert find_drills(text) == set()


def test_english_reference_is_ignored() -> None:
    assert find_drills("Leg Swings 2x10 already covered in the run warm-up") == set()


def test_overlap_only_from_prescriptions() -> None:
    workouts = [
        {"name": "Run", "description": "Cat-Cow 2x8\nA-Skips 2x20m"},
        {"name": "Core", "description": "Cat-Cow 2x8 läuft heute schon im Lauf-Warm-up — entfällt\nDead Bug 3x10"},
        {"name": "Legs", "description": "A-Skips 2x20m"},
    ]
    overlaps = detect_overlaps(workouts)
    assert overlaps == [{"drill": "A-Skips", "in_workouts": ["Run", "Legs"]}]


def test_a_skip_name_does_not_trip_reference_filter() -> None:
    # "Skip" must not be mistaken for an omission marker.
    assert find_drills("A-Skips 2x20m") == {"A-Skips"}
