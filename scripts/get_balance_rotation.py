"""Generate today's balance rotation as a workout JSON for push_workouts.py.

Usage:
    python3 scripts/get_balance_rotation.py [--date YYYY-MM-DD] | python3 scripts/push_workouts.py --date YYYY-MM-DD
    python3 scripts/get_balance_rotation.py --show   # Print human-readable without JSON envelope
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


def get_rotation(target_date: date) -> str:
    return ROTATION_KEYS[target_date.toordinal() % 4]


def main() -> None:
    parser = argparse.ArgumentParser(description="Output balance rotation workout JSON")
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--show", action="store_true", help="Human-readable output, no JSON envelope")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date)
    rotation = get_rotation(target_date)

    with open(_pool_path()) as f:
        pool = json.load(f)

    session = pool["sessions"][rotation]

    if args.show:
        print(f"Rotation {rotation}: {session['name']} ({session['duration_min']} min)")
        print()
        print(session["description"].replace("\\n", "\n"))
        return

    workout = {
        "type": "Workout",
        "name": session["name"],
        "tags": ["balance"],
        "duration_min": session["duration_min"],
        "intensity": "low",
        "workout_type": "WORKOUT",
        "indoor": True,
        "description": session["description"],
    }

    json.dump({"coaching_notes": f"Tägliche Balance-Rotation {rotation}", "workouts": [workout]}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
