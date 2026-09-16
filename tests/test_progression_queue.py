"""Tests for app/analytics/progression_queue.py.

The module exists because a pending progression step and its agreed order get
filed next to the exercise they belong to, where the planning flow does not
look for either. Two failures follow: two steps on the same tissue land in one
session and spend the next morning's reading, and a decided order gets
re-derived from whatever heuristic is at hand.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.analytics.progression_queue import (  # noqa: E402
    UNASSIGNED_CHAIN,
    format_queue,
    group_by_chain,
    parse_open_steps,
)


THREE_ON_ONE_CHAIN = """## Grip

### Wrist Curls
- **Aktueller Stand:** 3x10/Seite @ 11,5 kg, RPE 5
- **Schritt-offen:** 11,5 → 12,5 kg
- **Schritt-Kette:** Unterarm/Schulter
- **Schritt-Rang:** 1

### Dead Hang
- **Schritt-offen:** 20 → 25 s
- **Schritt-Kette:** Unterarm/Schulter
- **Schritt-Rang:** 2

### Farmer's Hold
- **Schritt-offen:** 33 → 35 kg
- **Schritt-Kette:** Unterarm/Schulter
- **Schritt-Rang:** 3

### Stir-the-Pot
- **Schritt-offen:** 3x9 → 3x10 pro Richtung
- **Schritt-Kette:** Rumpf
"""


def test_parses_only_entries_that_declare_a_step() -> None:
    doc = """### Has a step
- **Schritt-offen:** 10 → 12 kg

### Has none
- **Aktueller Stand:** 3x10 @ 10 kg
- **Soll-Frequenz:** 2x/Woche
"""
    steps = parse_open_steps(doc)
    assert [s.exercise for s in steps] == ["Has a step"]


def test_empty_and_missing_content_produce_nothing() -> None:
    assert parse_open_steps(None) == []
    assert parse_open_steps("") == []
    assert format_queue([]) is None


def test_declaration_before_any_heading_is_ignored() -> None:
    """A step with no exercise to attribute it to is dropped, not guessed.

    A step booked against the wrong exercise reads as deliberate afterwards,
    which is worse than one that never appeared.
    """
    doc = """- **Schritt-offen:** 10 → 12 kg

### Real exercise
- **Aktueller Stand:** nothing pending
"""
    assert parse_open_steps(doc) == []


def test_rank_orders_the_chain() -> None:
    chains = group_by_chain(parse_open_steps(THREE_ON_ONE_CHAIN))
    assert [s.exercise for s in chains["Unterarm/Schulter"]] == [
        "Wrist Curls",
        "Dead Hang",
        "Farmer's Hold",
    ]


def test_unranked_steps_sort_after_ranked_ones_in_document_order() -> None:
    """No rank means no decision — it must not be promoted to rank zero."""
    doc = """### No rank first in the document
- **Schritt-offen:** a
- **Schritt-Kette:** K

### Ranked
- **Schritt-offen:** b
- **Schritt-Kette:** K
- **Schritt-Rang:** 2

### Also no rank
- **Schritt-offen:** c
- **Schritt-Kette:** K
"""
    chains = group_by_chain(parse_open_steps(doc))
    assert [s.step for s in chains["K"]] == ["b", "a", "c"]


def test_missing_chain_falls_back_to_its_own_bucket() -> None:
    doc = """### Lonely
- **Schritt-offen:** 10 → 12 kg
"""
    steps = parse_open_steps(doc)
    assert steps[0].chain == UNASSIGNED_CHAIN


def test_collision_is_warned_per_chain_not_across_the_file() -> None:
    out = format_queue(parse_open_steps(THREE_ON_ONE_CHAIN))
    assert out is not None
    # The chain with three steps carries the warning marker...
    assert "⚠️" in out
    assert "Unterarm/Schulter" in out
    # ...and the single-step chain is listed without it.
    rumpf_line = next(line for line in out.splitlines() if "Rumpf" in line)
    assert "⚠️" not in rumpf_line
    assert "1 Schritt offen" in rumpf_line
    # The one-step-per-session consequence is spelled out, not left implicit.
    assert "ein Schritt pro Session" in out


def test_single_chain_single_step_emits_no_collision_warning() -> None:
    doc = """### Only one
- **Schritt-offen:** 10 → 12 kg
- **Schritt-Kette:** K
"""
    out = format_queue(parse_open_steps(doc))
    assert out is not None
    assert "⚠️" not in out
    assert "ein Schritt pro Session" not in out


def test_plain_unbolded_fields_are_accepted() -> None:
    """Both spellings occur in real files; the parser must not care."""
    doc = """### Plain
- Schritt-offen: 20 → 25 s
- Schritt-Kette: K
- Schritt-Rang: 4
"""
    steps = parse_open_steps(doc)
    assert steps[0].step == "20 → 25 s"
    assert steps[0].chain == "K"
    assert steps[0].rank == 4


def test_rank_tolerates_surrounding_prose() -> None:
    doc = """### Loose
- **Schritt-offen:** 10 → 12 kg
- **Schritt-Rang:** 2 (hinter dem Wrist Curl)
"""
    assert parse_open_steps(doc)[0].rank == 2


def test_first_declaration_per_entry_wins() -> None:
    """A later mention inside the same entry is prose, not a second step."""
    doc = """### One entry
- **Schritt-offen:** 10 → 12 kg
- Historie: frueher stand hier **Schritt-offen:** 8 → 10 kg
"""
    steps = parse_open_steps(doc)
    assert len(steps) == 1
    assert steps[0].step == "10 → 12 kg"


def test_bold_markup_is_stripped_from_values_and_headings() -> None:
    doc = """### **Bold Name**
- **Schritt-offen:** **33 → 35 kg**
"""
    steps = parse_open_steps(doc)
    assert steps[0].exercise == "Bold Name"
    assert steps[0].step == "33 → 35 kg"
