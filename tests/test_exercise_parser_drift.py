"""Regression tests for exercise_parser drift-sync corruption classes.

Both cases below caused `sync_description_drift.py` to write WRONG values
into `exercise_progressions.md` before the fix:

1. German comma decimal in weight ("5,75 kg") was mis-parsed to 75 kg —
   the dot-only weight regex failed the full-token match, then the
   fallback `_WEIGHT_ONLY_RE` greedily matched "75 kg" inside "5,75 kg".
2. "Towel Farmer's Hold" collided with "Farmer's Hold" — both normalised
   to a name that resolved to the `farmer_hold_kb` mapping key, so the
   Towel session values overwrote the Farmer's Hold progression entry.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.analytics.exercise_parser import (
    parse_line,
    match_to_mapping_key,
)

_MAPPING_PATH = (
    Path(__file__).resolve().parents[1]
    / "config.example"
    / "exercise_muscle_mapping.json"
)


@pytest.fixture(scope="module")
def mapping() -> dict:
    return json.loads(_MAPPING_PATH.read_text(encoding="utf-8"))


# ── Bug 1: German comma decimal in weight ────────────────────────────────────

@pytest.mark.parametrize(
    "line, expected_kg",
    [
        ("KB Horn Pinch: 3x20s/Seite 5,75kg | RPE 6", 5.75),
        ("Wrist Curl: 3x15 6,5 kg", 6.5),
        ("Goblet Squat: 3x10 22,5kg", 22.5),
        # dot decimals must keep working
        ("KB Horn Pinch: 3x20s/Seite 5.75kg | RPE 6", 5.75),
        # integer weights unchanged
        ("Farmer's Hold KB einarmig: 3x35s/Seite 35kg", 35.0),
    ],
)
def test_comma_decimal_weight(line: str, expected_kg: float) -> None:
    pe = parse_line(line)
    assert pe is not None
    assert pe.weight_kg == pytest.approx(expected_kg)


def test_comma_weight_not_truncated_to_post_comma_digits() -> None:
    """The exact regression: 5,75 must not become 75."""
    pe = parse_line("KB Horn Pinch: 3x20s/Seite 5,75kg | RPE 6")
    assert pe is not None
    assert pe.weight_kg != 75.0
    assert pe.weight_kg == pytest.approx(5.75)


# ── Bug 2: Towel Farmer's Hold must not collide with Farmer's Hold ────────────

def test_towel_farmer_distinct_from_farmer(mapping: dict) -> None:
    towel = parse_line("Towel Farmer's Hold: 3x20s/Seite 20kg | RPE 6")
    farmer = parse_line("Farmer's Hold KB einarmig: 3x35s/Seite 35kg | RPE 6-7")
    assert towel is not None and farmer is not None

    towel_key = match_to_mapping_key(towel.name, mapping)
    farmer_key = match_to_mapping_key(farmer.name, mapping)

    assert towel_key == "towel_farmers_hold"
    assert farmer_key == "farmer_hold_kb"
    assert towel_key != farmer_key


def test_towel_farmer_entry_exists(mapping: dict) -> None:
    assert "towel_farmers_hold" in mapping
    assert "towel farmer hold" in [
        a.lower() for a in mapping["towel_farmers_hold"]["aliases"]
    ]


# ── Bug 3: loose token-overlap fallback matched unrelated exercises ───────────
#
# The old fuzzy fallback accepted a candidate when just len(cwords)-1 tokens
# overlapped — for any 2-token alias a single shared generic token ("band",
# "pull", "curl", "plank") sufficed. Real corruption case (24.05./07.2026):
# "90/90 Bow & Arrow: 3x12" resolved to `finger_extensor_band` via the shared
# token "band" and overwrote that entry's Aktueller Stand.

@pytest.mark.parametrize(
    "name, wrong_key",
    [
        ("bow & arrow band", "finger_extensor_band"),
        ("pallof press band", "finger_extensor_band"),
        ("scapular pullups", "banded_pull_apart"),
        ("single-leg hip thrust", "single_leg_rdl"),
        ("kurzhantel curl", "reverse_curl"),
    ],
)
def test_single_shared_token_does_not_match(name: str, wrong_key: str) -> None:
    from app.analytics.exercise_parser import match_to_mapping_key as match

    mapping = json.loads(_MAPPING_PATH.read_text(encoding="utf-8"))
    assert match(name, mapping) != wrong_key


def test_containment_still_matches_specific_forms(mapping: dict) -> None:
    """Legit fuzzy wins must survive the hardening (non-strict mode)."""
    assert match_to_mapping_key("gripmaster fingers", mapping) == "gripmaster"
    # most specific containment wins: the 4-token tuck-hold key beats the
    # 3-token parallettes key
    assert (
        match_to_mapping_key("l-sit parallettes tuck hold", mapping)
        == "l_sit_tuck_hold"
    )


def test_token_set_equality_ignores_order_hyphens_fillers(mapping: dict) -> None:
    key = match_to_mapping_key("band finger-extensoren", mapping, strict=True)
    assert key == "finger_extensor_band"


# ── Bug 4 (P0-10): prefix-colliding NEW exercise must not hit base in strict ──

def test_strict_rejects_unknown_variant_with_extra_token(mapping: dict) -> None:
    """A variant name with an extra qualifier token ("towel", "deficit") must
    NOT strict-match the base exercise — it goes to the unmapped queue instead
    of rewriting the base entry. Simulated with the towel entry removed, i.e.
    the state at the time of the original corruption."""
    without_towel = {k: v for k, v in mapping.items() if k != "towel_farmers_hold"}
    name = "towel farmer hold"
    # non-strict containment may still resolve to the base (logging recall) …
    assert match_to_mapping_key(name, without_towel) == "farmer_hold_kb"
    # … but the strict write-path gate must refuse it.
    assert match_to_mapping_key(name, without_towel, strict=True) is None


def test_longest_match_prefers_specific_entry(mapping: dict) -> None:
    """When both base and variant exist, the variant (more tokens) wins."""
    assert match_to_mapping_key("towel farmer hold", mapping) == "towel_farmers_hold"
