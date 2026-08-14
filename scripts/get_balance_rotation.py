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

LEG_CONFLICT_MARKER = "Leg-conflict mode: slow-eccentric leg exercises swapped for pure stability drills"


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


def _generic_leg_conflict_substitute(original: dict) -> dict:
    """Generic pure-stability fallback for a `leg_conflict`-flagged exercise
    that has no pool-declared `leg_conflict_fallback`.

    Keeps the single-leg balance stimulus while dropping the slow-eccentric
    leg-loading component that collides with the >=48h spacing rule before a
    leg-driven quality / long session (framework/CLAUDE.md DOMS-spacing).
    """
    orig_name = original.get("name", "Exercise")
    return {
        "name": f"{orig_name} (Bein-Konflikt-Ersatz)",
        "text": (
            "Einbeinstand Augen zu: 3×30s/Seite | Ziel: S2–S3 — reiner "
            "Störungs-/Stabilitätsdrill ohne slow-eccentric; generischer "
            "Ersatz, kein Pool-Fallback hinterlegt"
        ),
        "equipment": [],
    }


def _apply_leg_conflict_mode(exercises: list[dict]) -> tuple[list[dict], list[str]]:
    """Swap `leg_conflict`-flagged exercises for their `leg_conflict_fallback`.

    Pool entries flag slow-eccentric leg-loading exercises (e.g. a TRX-assisted
    single-leg squat) with `"leg_conflict": true` and may declare a
    `leg_conflict_fallback` in the same shape as the exercise itself. Flagged
    exercises without a declared fallback get the generic pure-stability
    substitute, surfaced with a coach-facing note.

    Returns (possibly-substituted exercise list, substitution notes).
    """
    result: list[dict] = []
    notes: list[str] = []
    for ex in exercises:
        if not ex.get("leg_conflict"):
            result.append(ex)
            continue
        fallback = ex.get("leg_conflict_fallback")
        if fallback:
            result.append(fallback)
        else:
            result.append(_generic_leg_conflict_substitute(ex))
            notes.append(
                f"No leg_conflict_fallback declared for '{ex.get('name')}' — "
                "substituted generic pure-stability drill."
            )
    return result, notes


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


def _render_description(session: dict, travel: bool, leg_conflict: bool = False) -> str:
    """Render the session description text, applying the requested swap modes.

    Every chunk (headers + one "Name: text" line per activation/exercise
    entry, plus an optional trailing note) is joined by a blank line — this
    matches the flat paragraph-per-exercise format the pool content used
    before the structured schema.
    """
    chunks: list[str] = []
    if travel:
        chunks.append(TRAVEL_MODE_MARKER)
    if leg_conflict:
        chunks.append(LEG_CONFLICT_MARKER)

    # Legacy pool schema: one opaque `description` string per session (no
    # structured exercises[]). Consumer pools may still carry it — render it
    # verbatim; the swap modes cannot do structured swaps there, so surface a
    # loud coach note instead of silently pushing conflicting exercises.
    if "description" in session and "exercises" not in session:
        chunks.append(session["description"])
        if travel:
            chunks.append(
                "⚠️ Travel mode: pool uses the legacy description-only schema — "
                "equipment exercises could NOT be auto-swapped; coach must swap "
                "manually (see CLAUDE.md pool-content rules)."
            )
        if leg_conflict:
            chunks.append(
                "⚠️ Leg-conflict mode: pool uses the legacy description-only schema — "
                "slow-eccentric leg exercises could NOT be auto-swapped; coach must "
                "swap manually (see CLAUDE.md pool-content rules)."
            )
        return "\n\n".join(chunks)

    chunks.append(session.get("activation_header", "AKTIVIERUNG (5 min)"))
    for act in session.get("activation", []):
        chunks.append(f"{act['name']}: {act['text']}")

    exercises = session.get("exercises", [])
    substitution_notes: list[str] = []
    # Leg-conflict first, then travel: a leg-conflict fallback may itself
    # declare equipment, and travel mode must still be able to strip it.
    if leg_conflict:
        exercises, lc_notes = _apply_leg_conflict_mode(exercises)
        substitution_notes.extend(lc_notes)
    if travel:
        exercises, tv_notes = _apply_travel_mode(exercises)
        substitution_notes.extend(tv_notes)

    chunks.append(session.get("main_header", "BALANCE-HAUPTTEIL"))
    for ex in exercises:
        chunks.append(f"{ex['name']}: {ex['text']}")

    trailing = session.get("trailing_note")
    if trailing:
        chunks.append(trailing)

    if substitution_notes:
        chunks.append("\n".join(f"⚠️ {n}" for n in substitution_notes))

    return "\n\n".join(chunks)


def build_rotation_workout(
    target_date: date, travel: bool = False, leg_conflict: bool = False
) -> tuple[str, dict]:
    """Return (rotation_key, workout_dict) for the given date.

    Exposed for in-process callers (e.g. push_workouts.py auto-push) so they
    don't need to subprocess this script.

    `travel=True` swaps every equipment-dependent exercise for its
    `travel_fallback` (or a generic bodyweight substitute when none is
    declared) — see "Equipment availability (travel / limited kit)" in
    framework/CLAUDE.md.

    `leg_conflict=True` swaps every `leg_conflict`-flagged exercise for its
    `leg_conflict_fallback` (or a generic pure-stability substitute) — set it
    when today already carries a leg-strength block or TOMORROW carries a
    leg-driven quality / long session, so a slow-eccentric leg exercise never
    lands inside the >=48h DOMS-spacing window. The head coach passes the
    flag at push time; nothing infers the conflict automatically (the
    next-day plan is often not an intervals.icu event yet).
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
        "description": _render_description(session, travel, leg_conflict),
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
    parser.add_argument(
        "--leg-conflict",
        dest="leg_conflict",
        action="store_true",
        help="Swap leg_conflict-flagged exercises (slow-eccentric leg loading) for "
             "pure stability drills — set when today has a leg-strength block or "
             "tomorrow has a leg-driven quality / long session (>=48h DOMS spacing).",
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
        print(_render_description(session, args.travel, args.leg_conflict).replace("\\n", "\n"))
        return

    rotation, workout = build_rotation_workout(
        target_date, travel=args.travel, leg_conflict=args.leg_conflict
    )
    coaching_notes = f"Daily balance rotation {rotation}"
    if args.travel:
        coaching_notes += " (travel mode — equipment-free variants)"
    if args.leg_conflict:
        coaching_notes += " (leg-conflict mode — slow-eccentric leg exercises swapped)"
    json.dump({"coaching_notes": coaching_notes, "workouts": [workout]}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
