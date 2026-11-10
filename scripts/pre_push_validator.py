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

from app.analytics.recovery import RECOVERY_RULES, active_recovery_spacings, canonicalise_tags
from app.utils.alerts import alert_on_failure
from app.utils.logging import configure

logger = configure(__name__)


def check_recovery_rules(
    planned_workouts: list[dict],
    recent_activities: list[dict],
    today: date,
) -> list[str]:
    """Planned workouts that break a running recovery-spacing rule.

    Same rule set and matching as the planning context
    (``active_recovery_spacings``, legacy ``beine`` included). The message
    names a planning rule, not an injury.
    """
    violations: list[str] = []
    for sp in active_recovery_spacings(recent_activities, today, RECOVERY_RULES):
        trigger_set = set(sp["trigger_tags"])
        for w in planned_workouts:
            if trigger_set <= set(canonicalise_tags(w.get("tags"))):
                violations.append(
                    f"⛔ Recovery spacing (planning rule, not an injury) — {sp['label']}: "
                    f"'{w.get('name')}' — last {'+'.join(sp['trigger_tags'])} session "
                    f"{sp['days_ago']}d ago, minimum {sp['min_days']}d "
                    f"(free from {sp['free_from'].isoformat()})"
                )
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
