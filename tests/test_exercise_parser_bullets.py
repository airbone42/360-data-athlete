"""Regression tests: list bullets and approximate-RPE markers in description lines.

Workout descriptions are written as bullet lists ("  - Name: 3x8 RPE~7"), and
before the fix `parse_line` never removed the marker. Two consequences, both
silent:

1. `_NAME_COLON_RE` is anchored at `^` and expects a letter, so a leading "- "
   disabled the hyphen-tolerant name path for *every* bulleted line. Parsing
   fell through to the `name_pre` group of `_LINE_RE`, whose character class
   excludes "-" — so any hyphenated exercise name was truncated to the
   fragment after its last hyphen. Real corruption observed in
   `data/muscles/2026-09-04.json`:
       "Side Plank mit Hüft-Abduktion"          -> "abduktion"
       "Side Plank mit Drehung nach unten (T-Reach)" -> "reach)"
       "Stir-the-Pot (Pezziball)"               -> "pot (pezziball)"
   and where `name_pre` did not match at all, `_extract_name_from_line` kept
   the bullet itself in the name ("- mcgill curl-up").

   The downstream effect is what makes this a correctness bug rather than a
   cosmetic one: mangled names miss their mapping key, so the exercise never
   reaches the muscle log, and `prescription_compliance` then reports a
   standing prescription as overdue although it was executed.

2. `RPE~7` — the form the specialist agents actually emit — was not matched by
   either RPE pattern, so the value was dropped and the session was logged
   without an RPE.
"""
from __future__ import annotations

import pytest

from app.analytics.exercise_parser import (
    _ALIAS_NORMALISE,
    normalise_exercise_name,
    parse_description,
    parse_line,
)


# --- 1. Bullet prefixes must not corrupt the extracted name -----------------

@pytest.mark.parametrize(
    "line, expected_name",
    [
        # The four lines that were actually corrupted on 2026-09-04.
        (
            "  - Side Plank mit Hüft-Abduktion: 3x 45 Sek. RPE~7 (Last-/Lever-Schritt.)",
            "side plank mit hüft-abduktion",
        ),
        (
            "  - Side Plank mit Drehung nach unten (T-Reach): 3x 12 Wdh je Seite RPE~6",
            "side plank mit drehung nach unten (t-reach)",
        ),
        (
            "  - Stir-the-Pot (Pezziball): 3x 8 Wdh RPE~6 (8 je Richtung @ Tempo 3-0-3.)",
            "stir the pot (pezziball)",
        ),
        (
            "  - McGill Curl-up: 3x 6 Wdh RPE~5",
            "mcgill curl-up",
        ),
        # Same class, from the mobility block of the same day.
        ("  - Foamroller BWS-Extension: 1x 60 Sek.", "foamroller bws-extension"),
        ("  - Gekoppelter Hüftbeuger-Reset: 2x 45 Sek.", "gekoppelter hüftbeuger-reset"),
        # Other bullet flavours must behave identically.
        ("* Knee-to-Wall Dorsiflexion: 2x10", "knee-to-wall dorsiflexion"),
        ("• Single-Leg RDL: 3x6 12kg", "single leg rdl"),  # alias normalises the hyphen
        ("1. Back Squat: 3x5 60kg", "back squat"),
        ("2) Bulgarian Split Squat: 3x6 20kg", "bulgarian split squat"),
        # An unbulleted line keeps working exactly as before.
        ("Farmer Hold KB: 3x 40 Sek. 33kg", "farmer hold kb"),
    ],
)
def test_bullet_prefix_does_not_truncate_name(line: str, expected_name: str) -> None:
    parsed = parse_line(line)
    assert parsed is not None
    assert parsed.parse_ok is True
    assert parsed.name == expected_name


def test_raw_line_keeps_the_bullet() -> None:
    """`raw_line` must quote the source verbatim — drift sync and the unmapped
    queue report it back to a human, who needs to find the line again."""
    line = "  - Stir-the-Pot (Pezziball): 3x 8 Wdh"
    parsed = parse_line(line)
    assert parsed is not None
    assert parsed.raw_line == "- Stir-the-Pot (Pezziball): 3x 8 Wdh"


def test_feedback_arrow_is_not_read_as_a_bullet() -> None:
    """"->" must stay a feedback marker. The bullet pattern requires trailing
    whitespace precisely so this line is still skipped rather than parsed."""
    assert parse_line("-> Feedback: Hüfte war ruhig, 3x8 geschafft") is None


def test_bulleted_section_header_is_still_skipped() -> None:
    assert parse_line("  - WARM-UP (5 min)") is None


# --- 2. Approximate RPE markers --------------------------------------------

@pytest.mark.parametrize(
    "line, expected_rpe",
    [
        ("- Foo: 3x8 RPE~7", 7.0),
        ("- Foo: 3x8 RPE ~7", 7.0),
        ("- Foo: 3x8 RPE≈7", 7.0),
        ("- Foo: 3x8 RPE~7.5", 7.5),
        ("- Foo: 3x8 RPE~6-7", 6.5),
        # Plain form must be unaffected.
        ("- Foo: 3x8 RPE 7", 7.0),
        ("- Foo: 3x8 RPE 6-7", 6.5),
    ],
)
def test_approximate_rpe_marker_is_parsed(line: str, expected_rpe: float) -> None:
    parsed = parse_line(line)
    assert parsed is not None
    assert parsed.rpe == pytest.approx(expected_rpe)


# --- 3. End-to-end on the description that was corrupted -------------------

_SCHICHT_D_2026_09_04 = """Warm-up (3 min): Beckenkippen 10x, Hüft-Mobilisation Seitenlage 1x8/Seite.

Main (30 min): 30 s Pause zwischen Sätzen, ~45 s zwischen Übungen.

  - Side Plank mit Hüft-Abduktion: 3x 45 Sek. RPE~7 (Last-/Lever-Schritt: leichter Mini-Loop oberhalb der Knie.)

  - Side Plank mit Drehung nach unten (T-Reach): 3x 12 Wdh je Seite RPE~6 (Anker gehalten, kein Schritt.)

  - Stir-the-Pot (Pezziball): 3x 8 Wdh RPE~6 (8 je Richtung @ Tempo 3-0-3.)

  - Pallof Hold (isometrisch, Sprossenleiter): 3x 20 Sek. RPE~5 (Erst-Anker, leichtes Band.)

  - McGill Curl-up: 3x 6 Wdh RPE~5
"""


def test_schicht_d_description_yields_all_five_exercises() -> None:
    """The session that exposed the bug logged 2 of 5 exercises, both under a
    corrupted name. All five must now parse with an intact name and an RPE."""
    parsed, _unmapped = parse_description(_SCHICHT_D_2026_09_04)
    names = [p.name for p in parsed]

    assert names == [
        "side plank mit hüft-abduktion",
        "side plank mit drehung nach unten (t-reach)",
        "stir the pot (pezziball)",
        "pallof hold (isometrisch, sprossenleiter)",
        "mcgill curl-up",
    ]
    assert all(p.rpe is not None for p in parsed)
    assert [p.sets for p in parsed] == [3, 3, 3, 3, 3]


# --- 4. Alias table must be idempotent -------------------------------------

@pytest.mark.parametrize(
    "pattern, replacement",
    [(p.pattern, r) for p, r in _ALIAS_NORMALISE],
    ids=[p.pattern for p, _ in _ALIAS_NORMALISE],
)
def test_alias_table_is_idempotent(pattern: str, replacement: str) -> None:
    """Normalising an already-normalised name must be a no-op.

    The alias list is applied in order and each rule sees the output of the
    ones before it. A rule that expands a substring into a superstring still
    containing that substring therefore fires again on its own result. Three
    rules did exactly that:

        "Bulgarian Split Squat" -> "bulgarian split squat squat"
        "Overhead Press"        -> "kb kb overhead press"
        "L-Sit Tuck Hold"       -> "l-sit parallettes tuck hold"

    The third is the dangerous one: it splices the name of a *different*
    exercise into an already-correct one. Guard expanding rules with a
    lookahead/lookbehind rather than relying on ordering.
    """
    assert normalise_exercise_name(replacement) == replacement


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Bulgarian Split Squat", "bulgarian split squat"),
        ("Bulgarian Split", "bulgarian split squat"),  # short form still expands
        ("L-Sit Tuck Hold", "l-sit tuck hold"),
        ("L-Sit Parallettes", "l-sit parallettes"),
        ("L-Sit", "l-sit parallettes"),  # bare form still expands
        ("KB Overhead Press", "kb overhead press"),
        ("Overhead Press", "kb overhead press"),  # short form still expands
    ],
)
def test_expanding_aliases_do_not_duplicate_tokens(raw: str, expected: str) -> None:
    assert normalise_exercise_name(raw) == expected


# --- 5. Asymmetric per-side set counts -------------------------------------

def test_asymmetric_side_split_sets_are_summed() -> None:
    """Rehab work is routinely biased to the affected side.

    "3 Sätze rechts / 2 links x 8 Wdh" matched neither branch of `_LINE_RE`,
    and because `parse_description` also demands an N×M counter before it
    queues a line as unmapped, the line vanished without a trace: no exercise,
    no unmapped entry. `prescription_compliance` then reported the Single-Leg
    Hip Thrust as 24 days overdue although it had run three days earlier.
    """
    line = (
        "Single-Leg Hip Thrust: 3 Sätze rechts / 2 links x 8 Wdh Bodyweight, "
        "1s Hold oben | RPE bis 6 | rechts zuerst, kontrolliert ab"
    )
    parsed = parse_line(line)
    assert parsed is not None
    assert parsed.parse_ok is True
    assert parsed.name == "single-leg hip thrust"
    assert parsed.sets == 5  # 3 right + 2 left
    assert parsed.reps == 8.0
    assert parsed.rpe == 6.0
    assert parsed.hold_s == 1.0
    # The sum already covers both sides — doubling on top would be wrong.
    assert parsed.per_side is False


def test_compact_asymmetric_notation() -> None:
    parsed = parse_line("- Single-Leg Hip Thrust: 3r/2l x 8 Bodyweight")
    assert parsed is not None
    assert parsed.sets == 5
    assert parsed.reps == 8.0
    assert parsed.per_side is False


def test_symmetric_per_side_still_doubles() -> None:
    """The asymmetric path must not disturb the ordinary "je Seite" case."""
    parsed = parse_line("- Foo: 3x8 je Seite RPE 7")
    assert parsed is not None
    assert parsed.sets == 3
    assert parsed.per_side is True


@pytest.mark.parametrize(
    "line, expected_rpe",
    [
        ("- Foo: 3x8 RPE bis 6", 6.0),
        ("- Foo: 3x8 RPE ca. 7", 7.0),
        ("- Foo: 3x8 RPE max 8", 8.0),
    ],
)
def test_german_rpe_qualifiers(line: str, expected_rpe: float) -> None:
    parsed = parse_line(line)
    assert parsed is not None
    assert parsed.rpe == pytest.approx(expected_rpe)
