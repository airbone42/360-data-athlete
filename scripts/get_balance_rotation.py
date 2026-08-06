"""Generate today's balance rotation as a workout JSON for push_workouts.py.

Usage:
    python3 scripts/get_balance_rotation.py [--date YYYY-MM-DD] | python3 scripts/push_workouts.py --date YYYY-MM-DD
    python3 scripts/get_balance_rotation.py --show   # Print human-readable without JSON envelope
    python3 scripts/get_balance_rotation.py --travel # Swap equipment-dependent exercises for bodyweight variants
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.utils.paths import COACH_HOME, FRAMEWORK_ROOT  # noqa: E402


def _pool_path() -> str:
    """Resolve balance_pool.json — prefer wrapper override, fall back to framework default."""
    primary = COACH_HOME / "config" / "balance_pool.json"
    if primary.exists():
        return str(primary)
    return str(FRAMEWORK_ROOT / "config.example" / "balance_pool.json")


ROTATION_KEYS = ["A", "B", "C", "D"]

TRAVEL_MODE_MARKER = "Travel mode: equipment-free variants"


def get_rotation(target_date: date) -> str:
    return ROTATION_KEYS[target_date.toordinal() % 4]


def _generic_travel_substitute(original: dict) -> dict:
    """Generic bodyweight/soft-surface fallback for an equipment exercise that
    has no pool-declared `travel_fallback`.

    Preserves the single-leg-stand + instability stimulus shared by the
    equipment-dependent pool entries (balance board / KB / TRX) without
    requiring any gear.
    """
    orig_name = original.get("name", "Exercise")
    return {
        "name": f"{orig_name} (Travel-Ersatz)",
        "text": (
            "Einbeinstand auf instabiler weicher Unterlage (gefaltetes Handtuch/Kissen): "
            "3×20s/Seite | Ziel: S2–S3 — generischer bodyweight-Ersatz, kein Pool-Fallback hinterlegt"
        ),
        "equipment": [],
    }


def _apply_travel_mode(exercises: list[dict]) -> tuple[list[dict], list[str]]:
    """Swap equipment-dependent exercises for their `travel_fallback`.

    Exercises without an `equipment` list (or an empty one) pass through
    unchanged. Exercises that declare equipment but no `travel_fallback` get
    the generic single-leg/soft-surface substitute, and a coach-facing note
    is returned so the substitution is visible in the output.

    Returns (possibly-substituted exercise list, substitution notes).
    """
    result: list[dict] = []
    notes: list[str] = []
    for ex in exercises:
        equipment = ex.get("equipment") or []
        if not equipment:
            result.append(ex)
            continue
        fallback = ex.get("travel_fallback")
        if fallback:
            result.append(fallback)
        else:
            result.append(_generic_travel_substitute(ex))
            notes.append(
                f"No travel_fallback declared for '{ex.get('name')}' — "
                "substituted generic single-leg / soft-surface variant."
            )
    return result, notes


def _render_description(session: dict, travel: bool) -> str:
    """Render the session description text, applying travel substitutions if requested.

    Every chunk (headers + one "Name: text" line per activation/exercise
    entry, plus an optional trailing note) is joined by a blank line — this
    matches the flat paragraph-per-exercise format the pool content used
    before the structured schema.
    """
    chunks: list[str] = []
    if travel:
        chunks.append(TRAVEL_MODE_MARKER)

    # Legacy pool schema: one opaque `description` string per session (no
    # structured exercises[]). Consumer pools may still carry it — render it
    # verbatim; travel mode cannot do structured swaps there, so surface a
    # loud coach note instead of silently pushing equipment exercises.
    if "description" in session and "exercises" not in session:
        chunks.append(session["description"])
        if travel:
            chunks.append(
                "⚠️ Travel mode: pool uses the legacy description-only schema — "
                "equipment exercises could NOT be auto-swapped; coach must swap "
                "manually (see CLAUDE.md pool-content rules)."
            )
        return "\n\n".join(chunks)

    chunks.append(session.get("activation_header", "AKTIVIERUNG (5 min)"))
    for act in session.get("activation", []):
        chunks.append(f"{act['name']}: {act['text']}")

    exercises = session.get("exercises", [])
    substitution_notes: list[str] = []
    if travel:
        exercises, substitution_notes = _apply_travel_mode(exercises)

    chunks.append(session.get("main_header", "BALANCE-HAUPTTEIL"))
    for ex in exercises:
        chunks.append(f"{ex['name']}: {ex['text']}")

    trailing = session.get("trailing_note")
    if trailing:
        chunks.append(trailing)

    if substitution_notes:
        chunks.append("\n".join(f"⚠️ {n}" for n in substitution_notes))

    return "\n\n".join(chunks)


def build_rotation_workout(target_date: date, travel: bool = False) -> tuple[str, dict]:
    """Return (rotation_key, workout_dict) for the given date.

    Exposed for in-process callers (e.g. push_workouts.py auto-push) so they
    don't need to subprocess this script.

    `travel=True` swaps every equipment-dependent exercise for its
    `travel_fallback` (or a generic bodyweight substitute when none is
    declared) — see "Equipment availability (travel / limited kit)" in
    framework/CLAUDE.md.
    """
    rotation = get_rotation(target_date)
    with open(_pool_path()) as f:
        pool = json.load(f)
    session = pool["sessions"][rotation]
    workout = {
        "type": "Workout",
        "name": session["name"],
        "tags": ["balance"],
        "duration_min": session["duration_min"],
        "intensity": "low",
        "workout_type": "WORKOUT",
        "indoor": True,
        "description": _render_description(session, travel),
    }
    return rotation, workout


def main() -> None:
    parser = argparse.ArgumentParser(description="Output balance rotation workout JSON")
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--show", action="store_true", help="Human-readable output, no JSON envelope")
    parser.add_argument(
        "--travel", "--no-equipment",
        dest="travel",
        action="store_true",
        help="Swap equipment-dependent exercises (balance board / kettlebell / TRX) for "
             "bodyweight / soft-surface fallbacks.",
    )
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date)

    if args.show:
        rotation = get_rotation(target_date)
        with open(_pool_path()) as f:
            pool = json.load(f)
        session = pool["sessions"][rotation]
        print(f"Rotation {rotation}: {session['name']} ({session['duration_min']} min)")
        print()
        print(_render_description(session, args.travel).replace("\\n", "\n"))
        return

    rotation, workout = build_rotation_workout(target_date, travel=args.travel)
    coaching_notes = f"Daily balance rotation {rotation}"
    if args.travel:
        coaching_notes += " (travel mode — equipment-free variants)"
    json.dump({"coaching_notes": coaching_notes, "workouts": [workout]}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
