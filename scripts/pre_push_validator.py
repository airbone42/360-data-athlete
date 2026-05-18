"""Pre-push validator — prüft geplante Workouts gegen Recovery-Sperren und Reihenfolge-Regeln.

Macht CLAUDE.md-Prompt-Regeln zu Runtime-Gates vor push_workouts.py.

Usage:
    # Workouts als JSON-Array via stdin + Kontext-JSON via --context-file
    echo '[{"type":"Run","tags":["run"],...}]' | python3 scripts/pre_push_validator.py --date 2026-04-20
    echo '[...]' | python3 scripts/pre_push_validator.py --context-file /tmp/context.json

Exit-Codes:
    0 — alle Checks bestanden
    1 — mindestens eine Violation (Fehlermeldungen auf stderr)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.analytics.recovery import RECOVERY_RULES
from app.utils.alerts import alert_on_failure
from app.utils.logging import configure

logger = configure(__name__)


def _days_since(activity_date_str: str, today: date) -> int:
    try:
        return (today - date.fromisoformat(activity_date_str)).days
    except (ValueError, TypeError):
        return 999


def check_recovery_rules(
    planned_workouts: list[dict],
    recent_activities: list[dict],
    today: date,
) -> list[str]:
    """Return list of violations from recovery rules."""
    violations: list[str] = []

    for trigger_tags, min_days, label in RECOVERY_RULES:
        trigger_set = set(trigger_tags)
        # Find the most recent activity that triggered this rule
        for activity in sorted(recent_activities, key=lambda a: a.get("date", ""), reverse=True):
            act_tags = set(str(t).lower() for t in (activity.get("tags") or []))
            if trigger_set <= act_tags:
                days = _days_since(activity.get("date", ""), today)
                if days < min_days:
                    # Check if any planned workout uses the blocked tags
                    for w in planned_workouts:
                        w_tags = set(str(t).lower() for t in (w.get("tags") or []))
                        if trigger_set <= w_tags:
                            violations.append(
                                f"⛔ {label}: '{w.get('name')}' — "
                                f"letzte Session mit {trigger_tags} vor {days}d "
                                f"(Minimum: {min_days}d)"
                            )
                break

    return violations


def check_order_rule(planned_workouts: list[dict]) -> list[str]:
    """WeightTraining/Workout must come before Run/Ride on the same day."""
    violations: list[str] = []
    found_endurance = False
    for w in planned_workouts:
        t = w.get("type", "")
        if t in ("Run", "Ride"):
            found_endurance = True
        elif t in ("WeightTraining", "Workout") and found_endurance:
            violations.append(
                f"⛔ Reihenfolge-Verstoß: '{w.get('name')}' ({t}) nach Lauf/Ride — "
                "WeightTraining immer VOR dem Lauf planen"
            )
    return violations


def validate(
    planned_workouts: list[dict],
    recent_activities: list[dict],
    today: date,
) -> list[str]:
    violations: list[str] = []
    violations.extend(check_recovery_rules(planned_workouts, recent_activities, today))
    violations.extend(check_order_rule(planned_workouts))
    return violations


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-push validator für geplante Workouts")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--context-file", help="Pfad zu fetch_context.py JSON-Output")
    args = parser.parse_args()

    today = date.fromisoformat(args.date)

    raw = sys.stdin.read().strip()
    try:
        planned = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        print("Error: stdin muss ein JSON-Array mit Workouts sein", file=sys.stderr)
        sys.exit(1)

    # Load recent activities from context file if provided
    recent: list[dict] = []
    if args.context_file:
        with open(args.context_file) as f:
            ctx = json.load(f)
        recent = ctx.get("activities", [])

    violations = validate(planned, recent, today)

    if violations:
        for v in violations:
            print(v, file=sys.stderr)
        logger.warning("pre_push_validator: %d violation(s)", len(violations))
        sys.exit(1)

    logger.info("pre_push_validator: OK — %d workout(s) validated", len(planned))
    print(f"✅ {len(planned)} Workout(s) validiert — keine Sperren verletzt")


if __name__ == "__main__":
    main()
