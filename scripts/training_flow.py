"""Training Flow Orchestrator — macht IO-Schritte des /training-Flows callable.

Ersetzt NICHT den Claude-/training-Flow (Agents bleiben Claude-Agents).
Macht die deterministischen IO-Schritte explizit callable und validiert sie.

Library-Nutzung (von Claude-Code oder anderen Scripts):
    from scripts.training_flow import run_push, run_pre_push_validate

CLI:
    # Validieren + Pushen + Schuh-Empfehlung in einem Schritt:
    python3 scripts/training_flow.py push --file workouts.json --date 2026-04-20
    python3 scripts/training_flow.py push --file workouts.json --date 2026-04-20 --dry-run
    python3 scripts/training_flow.py validate --file workouts.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.alerts import alert_on_failure, notify_error
from app.utils.logging import configure

logger = configure(__name__)

_REPO = Path(__file__).parent.parent


# ─── Library functions ────────────────────────────────────────────────────────


def run_context(date_str: str, fresh_shoes: bool = False) -> dict:
    """Run fetch_context.py and return parsed context dict."""
    cmd = [sys.executable, str(_REPO / "scripts" / "fetch_context.py"), "--date", date_str]
    if fresh_shoes:
        cmd.append("--fresh-shoes")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_REPO))
    if result.returncode != 0:
        notify_error("fetch_context failed", {"stderr": result.stderr[:500]})
        raise RuntimeError(f"fetch_context failed: {result.stderr[:200]}")
    return json.loads(result.stdout)


def run_health_check(context: dict) -> list[str]:
    """Return list of health warnings from context (HRV, data warnings)."""
    warnings: list[str] = []
    warnings.extend(context.get("dataWarnings") or [])
    readiness = context.get("intensityReadiness", "")
    if "🔴" in str(readiness):
        hrv = context.get("hrv", "?")
        baseline = context.get("hrvBaseline", "?")
        dev = context.get("hrvDeviation", "?")
        warnings.append(f"HRV supprimiert: {hrv} (Baseline {baseline}, {dev}%) — Rückfrage Athlet empfohlen")
    return warnings


def run_type_history(date_str: str, workout_type: str, tags: str = "", max_sessions: int = 3) -> list[dict]:
    """Run fetch_type_history.py and return parsed sessions list."""
    cmd = [
        sys.executable, str(_REPO / "scripts" / "fetch_type_history.py"),
        "--date", date_str,
        "--type", workout_type,
        "--max-sessions", str(max_sessions),
    ]
    if tags:
        cmd += ["--tags", tags]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_REPO))
    if result.returncode != 0:
        logger.warning("fetch_type_history failed: %s", result.stderr[:200])
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def run_pre_push_validate(
    planned_workouts: list[dict],
    context: dict,
    date_str: str,
) -> list[str]:
    """Validate workouts against recovery rules. Returns list of violations."""
    from scripts.pre_push_validator import validate
    recent = context.get("activities", [])
    today = date.fromisoformat(date_str)
    return validate(planned_workouts, recent, today)


def run_push(workouts: list[dict], date_str: str, dry_run: bool = False) -> list[dict]:
    """Push workouts to intervals.icu. Returns created event list."""
    cmd = [
        sys.executable, str(_REPO / "scripts" / "push_workouts.py"),
        "--date", date_str,
    ]
    if dry_run:
        cmd.append("--dry-run")
    result = subprocess.run(
        cmd,
        input=json.dumps(workouts, ensure_ascii=False),
        capture_output=True, text=True, cwd=str(_REPO),
    )
    if result.returncode != 0:
        notify_error("push_workouts failed", {"stderr": result.stderr[:500]})
        raise RuntimeError(f"push_workouts failed: {result.stderr[:200]}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def run_shoe_recommend(workouts: list[dict], weather: str, date_str: str) -> dict:
    """Return shoe context dict for the planned workouts."""
    from scripts.shoe_recommend import recommend
    return asyncio.run(recommend(workouts, weather, date_str))


def run_hrv_reminder(context: dict) -> str | None:
    """Return HRV review question if pending, else None."""
    pending = context.get("hrvReviewPending")
    if pending:
        return (
            f"Dein HRV war am {pending.get('date', '?')} deutlich niedriger als erwartet "
            f"(actual: {pending.get('pct', '?')}%, erwartet: {pending.get('expected_pct', '?')}%). "
            "Gab es externe Faktoren — schlechter Schlaf, Stress, Alkohol, Erkältung?"
        )
    return None


# ─── CLI ─────────────────────────────────────────────────────────────────────


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Training Flow Orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    # push: validate → push → shoe_recommend
    push_p = sub.add_parser("push", help="Validate + push workouts + shoe recommend")
    push_p.add_argument("--date", default=date.today().isoformat())
    push_p.add_argument("--file", help="JSON-Datei mit Workouts-Array")
    push_p.add_argument("--weather", default="", help="Wetter-String für Schuh-Empfehlung")
    push_p.add_argument("--dry-run", action="store_true")
    push_p.add_argument("--skip-validate", action="store_true", help="Pre-push-Validation überspringen")

    # validate: nur validieren, nicht pushen
    val_p = sub.add_parser("validate", help="Nur Validation, kein Push")
    val_p.add_argument("--date", default=date.today().isoformat())
    val_p.add_argument("--file", help="JSON-Datei mit Workouts-Array")
    val_p.add_argument("--context-file", help="fetch_context.py Output für Activity-History")

    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            workouts = json.load(f)
    else:
        raw = sys.stdin.read().strip()
        workouts = json.loads(raw) if raw else []

    if not isinstance(workouts, list):
        workouts = [workouts]

    if args.command == "validate":
        ctx: dict = {}
        if hasattr(args, "context_file") and args.context_file:
            with open(args.context_file) as f:
                ctx = json.load(f)
        violations = run_pre_push_validate(workouts, ctx, args.date)
        if violations:
            for v in violations:
                print(v, file=sys.stderr)
            sys.exit(1)
        print(f"✅ {len(workouts)} Workout(s) validiert — keine Sperren verletzt")
        return

    # push flow
    if not args.skip_validate:
        violations = run_pre_push_validate(workouts, {}, args.date)
        if violations:
            print("⛔ Validation fehlgeschlagen — Push abgebrochen:", file=sys.stderr)
            for v in violations:
                print(f"  {v}", file=sys.stderr)
            sys.exit(1)

    logger.info("training_flow push: %d workout(s) for %s", len(workouts), args.date)
    created = run_push(workouts, args.date, dry_run=args.dry_run)
    logger.info("training_flow push: %d event(s) created", len(created))
    print(json.dumps(created, ensure_ascii=False, indent=2))

    shoe_ctx = run_shoe_recommend(workouts, args.weather, args.date)
    if shoe_ctx and shoe_ctx.get("shoeRecommendation", {}).get("primary"):
        rec = shoe_ctx["shoeRecommendation"]["primary"]
        print(f"\n👟 {rec['name']}: {rec.get('reason', '')}")


if __name__ == "__main__":
    main()
