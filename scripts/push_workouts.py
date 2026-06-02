"""Create workout events in intervals.icu from JSON input.

Wraps: workout_parser.prepare_workout_events() + IntervalsClient.post_events_bulk()

Input: JSON array (workouts with structure/intervals_icu fields) via --file or stdin.
Output: JSON array of created event IDs to stdout.

Usage:
    echo '[{...}]' | python3 coach/scripts/push_workouts.py --date YYYY-MM-DD
    python3 coach/scripts/push_workouts.py --date YYYY-MM-DD --file /tmp/workouts.json [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pydantic import ValidationError

from app.api.intervals_client import IntervalsClient
from app.config import settings
from app.graphs.main_daily_planner.workout_parser import prepare_workout_events
from app.schemas.planner import PlannerOutput
from app.utils.alerts import alert_on_failure, notify_error
from app.utils.logging import configure
from app.utils.tracing import configure_tracing
from shoe_recommend import recommend as _recommend_shoes
from validate_plan import (
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    format_findings_text,
    load_context as _load_validator_ctx,
    run_validation,
)

logger = configure(__name__)
configure_tracing()


async def _dedup_existing_events(athlete_id: str, date_str: str, events: list[dict]) -> int:
    """Delete existing intervals.icu events on `date_str` that match name+type
    of any to-be-pushed event.

    Idempotency safety-net: intervals.icu's `upsert=true` matches on its own
    server-side `uid`, not the client-provided `coach-{date}-{i}` value, so
    repeated push calls would otherwise pile up duplicates (pattern from
    real usage). This pre-push sweep guarantees `push_workouts.py` is safe
    to call twice in a row.

    Returns the number of events deleted.
    """
    client = IntervalsClient(athlete_id)
    try:
        existing = await client.get_events(date_str, date_str)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Pre-push dedup: failed to fetch existing events (%s) — proceeding without sweep", exc)
        return 0
    # Match key: (name, type). Only consider non-NOTE events (NOTE events have type=None).
    targets = {(e.get("name"), e.get("type")) for e in events if e.get("name") and e.get("type")}
    to_delete = [
        ev for ev in existing
        if ev.get("type") and (ev.get("name"), ev.get("type")) in targets
    ]
    if not to_delete:
        return 0
    logger.info(
        "Pre-push dedup: deleting %d existing event(s) on %s matching push set: %s",
        len(to_delete), date_str, [(e.get("name"), e.get("type"), e.get("id")) for e in to_delete],
    )
    for ev in to_delete:
        try:
            await client.delete_event(ev["id"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pre-push dedup: failed to delete event %s (%s) — continuing", ev.get("id"), exc)
    return len(to_delete)


async def _push(athlete_id: str, events: list[dict], dry_run: bool, date_str: str) -> list[dict]:
    if dry_run:
        logger.info("[DRY-RUN] Would create %d event(s): %s", len(events), [e.get("uid") for e in events])
        return [{"uid": e["uid"], "dry_run": True} for e in events]
    await _dedup_existing_events(athlete_id, date_str, events)
    client = IntervalsClient(athlete_id)
    created = await client.post_events_bulk(events)
    return created


def _format_shoe_footer(shoe_ctx: dict) -> str:
    """Render a shoe-recommendation footer for run/ride descriptions.

    Uses the primary shoe name, km, and the advisor's reason string (which
    includes type/terrain or rotation hints).
    """
    rec = (shoe_ctx or {}).get("shoeRecommendation") or {}
    primary = rec.get("primary") or {}
    if not primary.get("name"):
        return ""
    km = primary.get("distance_km")
    head = f"Shoe recommendation: {primary['name']}"
    if km is not None:
        head += f" ({km:.0f} km)"
    reason = primary.get("reason")
    line = f"{head} — {reason}" if reason else head
    alt = rec.get("alternative") or {}
    if alt.get("name"):
        alt_km = alt.get("distance_km")
        alt_str = alt["name"] + (f" ({alt_km:.0f} km)" if alt_km is not None else "")
        line += f"\nAlternative: {alt_str}"
    warnings = (shoe_ctx or {}).get("shoeWarnings") or []
    for w in warnings:
        if w.get("msg"):
            line += f"\n{w['msg']}"
    return line


async def _enrich_with_shoes(events: list[dict], workouts: list[dict], weather: str, date_str: str) -> None:
    """Append shoe-recommendation footer to Run event descriptions in-place.

    Legacy Strava-backend behaviour only. With the intervals.icu backend the
    recommended shoe is assigned to the *finished* activity post-run
    (scripts/set_activity_gear.py, /analyse step 6.55) so intervals.icu can
    accumulate the mileage natively — no text footer on the planned event.
    """
    if settings.shoe_tracking_backend != "strava":
        return
    if not any(w.get("type") == "Run" for w in workouts):
        return
    try:
        shoe_ctx = await _recommend_shoes(workouts, weather, date_str)
    except Exception as exc:
        logger.warning("Shoe recommendation failed: %s — workouts pushed without shoe footer", exc)
        return
    footer = _format_shoe_footer(shoe_ctx)
    if not footer:
        return
    for ev in events:
        if ev.get("type") == "Run":
            current = (ev.get("description") or "").rstrip()
            ev["description"] = f"{current}\n\n{footer}" if current else footer


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Push workouts to intervals.icu")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--file", help="Path to JSON file with workouts array")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--weather",
        default="",
        help="weatherInfo string — used to enrich Run events with shoe recommendation footer",
    )
    parser.add_argument(
        "--no-shoes",
        action="store_true",
        help="Skip automatic shoe-recommendation footer for Run events",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validate_plan pre-push check (emergency bypass — document explicitly!)",
    )
    parser.add_argument(
        "--no-auto-balance",
        action="store_true",
        help="Skip auto-push of the daily balance rotation after the main push.",
    )
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            workouts = json.load(f)
    else:
        workouts = json.load(sys.stdin)

    # Normalise to {coaching_notes, workouts} envelope and validate schema
    if isinstance(workouts, dict):
        envelope = workouts
    else:
        envelope = {"workouts": workouts if isinstance(workouts, list) else [workouts]}
    try:
        parsed = PlannerOutput.model_validate(envelope)
        workouts = parsed.workouts
    except ValidationError as exc:
        notify_error("push_workouts: PlannerOutput schema violation", {"errors": str(exc)})
        logger.error("Schema validation failed: %s", exc)
        sys.exit(1)

    from app.utils.tracing import script_span, set_span_io

    # Pre-push validation — MANDATORY, can only be bypassed via --skip-validation.
    if not args.skip_validation:
        try:
            workouts_for_validation = [
                w if isinstance(w, dict) else (w.model_dump() if hasattr(w, "model_dump") else dict(w))
                for w in workouts
            ]
            ctx = _load_validator_ctx(args.date, fetch_remote=True)
            findings = run_validation(workouts_for_validation, ctx)
            errors = [f for f in findings if f.severity == SEVERITY_ERROR]
            warnings = [f for f in findings if f.severity == SEVERITY_WARNING]
            if findings:
                logger.warning("Validator findings:\n%s", format_findings_text(findings))
            if errors:
                notify_error("push_workouts: validate_plan ERROR(s) — push blocked", {
                    "errors": [f.to_dict() for f in errors],
                })
                logger.error("Push blocked due to %d ERROR finding(s). Override with --skip-validation.", len(errors))
                sys.exit(2)
            if warnings:
                logger.warning("Push proceeding with %d WARNING(s).", len(warnings))
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Validator call failed (fail-soft): %s — push proceeding", exc)
    else:
        logger.warning("⚠️ --skip-validation active — pre-push check skipped!")

    logger.info("push_workouts: %d workout(s) for %s", len(workouts), args.date)
    events = prepare_workout_events(workouts, args.date)
    if not args.no_shoes:
        asyncio.run(_enrich_with_shoes(events, workouts, args.weather, args.date))
    athlete_id = settings.intervals_icu_athlete_id
    suffix = " (dry-run)" if args.dry_run else ""
    display = f"Push workouts — {len(workouts)} sessions on {args.date}{suffix}"
    workout_names = [w.get("name", "?") if isinstance(w, dict) else getattr(w, "name", "?") for w in workouts]
    with script_span(
        "push_workouts",
        display_name=display,
        date=args.date,
        workout_count=len(workouts),
        dry_run=args.dry_run,
    ):
        created = asyncio.run(_push(athlete_id, events, args.dry_run, args.date))
        ids = [e.get("uid") or e.get("id") for e in created]
        set_span_io(
            input={"date": args.date, "workouts": workout_names, "dry_run": args.dry_run},
            output={"created": len(created), "ids": ids},
        )
    logger.info("push_workouts: created %d event(s): %s", len(created), ids)
    print(json.dumps(created, ensure_ascii=False, indent=2))

    if not args.dry_run:
        if not args.no_auto_balance:
            _auto_push_balance(args.date, workouts, athlete_id)
        _warn_on_warmup_overlap(args.date)
        _warn_on_mental_coach_triggers(workouts, args.date)


def _auto_push_balance(target_date: str, current_workouts: list, athlete_id: str) -> None:
    """Push the daily balance rotation as a third workout if none exists yet.

    Implements the SSOT for the "Daily balance rotation (mandatory)" rule from
    `framework/CLAUDE.md`: the rule is enforced in code here, not duplicated as
    a workflow step in `commands/training.md`. Fail-soft — never blocks the
    main push.

    Skip conditions:
    - Current push already contains a workout with the `balance` tag (the
      caller is pushing balance themselves, e.g. via the manual
      `get_balance_rotation.py | push_workouts.py` pipe).
    - An intervals.icu event with the `balance` tag already exists for the
      target date (idempotent — re-pushes don't stack duplicates).
    """
    try:
        for w in current_workouts:
            tags = w.get("tags") if isinstance(w, dict) else getattr(w, "tags", None)
            if tags and "balance" in tags:
                logger.debug("Auto-balance: balance already in current push, skipping")
                return
        from datetime import date as _date
        from get_balance_rotation import build_rotation_workout

        client = IntervalsClient(athlete_id)
        existing = asyncio.run(client.get_events(target_date, target_date))
        if any("balance" in (e.get("tags") or []) for e in existing):
            logger.debug("Auto-balance: balance event already exists for %s, skipping", target_date)
            return

        rotation, workout = build_rotation_workout(_date.fromisoformat(target_date))
        logger.info("Auto-balance: pushing rotation %s for %s", rotation, target_date)
        events = prepare_workout_events([workout], target_date)
        asyncio.run(_push(athlete_id, events, dry_run=False, date_str=target_date))
        logger.info("Auto-balance: rotation %s pushed", rotation)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Auto-balance push failed (fail-soft): %s", exc)


def _warn_on_warmup_overlap(target_date: str) -> None:
    """Post-push sanity check: warns on duplicate warm-up drills in the day.

    Fail-soft — if the check fails, it does not block the push.
    """
    try:
        from check_warmup_overlap import detect_overlaps, fetch_workouts
        events = asyncio.run(fetch_workouts(target_date))
        overlaps = detect_overlaps(events)
        if not overlaps:
            return
        logger.warning("⚠️  Drill duplication on %s — %d hit(s):", target_date, len(overlaps))
        for o in overlaps:
            logger.warning("   • %s: %s", o["drill"], " ↔ ".join(o["in_workouts"]))
        logger.warning("   → Coach should clean up warmup or remove one block.")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Warm-up overlap check skipped: %s", exc)


def _warn_on_mental_coach_triggers(workouts: list, target_date: str) -> None:
    """Post-push sanity check: surfaces mechanically detectable mental-coach triggers.

    Triggers (per framework/CLAUDE.md "Mental-coach triggers"):
    - workout_type == "LONG" or duration_min > 90 on a Run
    - workout_type == "RACE"

    Fail-soft — if check fails, it does not block the push. The head
    coach (Claude) reads this WARNING and decides to start mental-coach
    as a pane teammate. The other triggers (bad session, setback note,
    HRV drop, motivation signal) are not derivable from push-workouts
    data and stay head-coach judgment.
    """
    try:
        triggers = []
        for w in workouts:
            wo_type = w.get("type") if isinstance(w, dict) else getattr(w, "type", None)
            wo_subtype = w.get("workout_type") if isinstance(w, dict) else getattr(w, "workout_type", None)
            duration = w.get("duration_min") if isinstance(w, dict) else getattr(w, "duration_min", None)
            name = w.get("name") if isinstance(w, dict) else getattr(w, "name", "(unnamed)")
            if wo_subtype == "RACE":
                triggers.append(("RACE", name, "Race day — pre-race mental setup"))
                continue
            if wo_subtype == "LONG" and wo_type in ("Run", "Ride"):
                triggers.append(("LONG", name, f"Long effort {duration or '?'} min"))
                continue
            if wo_type == "Run" and isinstance(duration, (int, float)) and duration > 90:
                triggers.append(("LONG", name, f"Run > 90 min ({duration} min)"))
        if not triggers:
            return
        logger.warning("🧠 MENTAL-COACH-TRIGGER for %s — %d hit(s):", target_date, len(triggers))
        for kind, name, reason in triggers:
            logger.warning("   • [%s] %s — %s", kind, name, reason)
        logger.warning("   → Head coach: start mental-coach in its own pane (context: workout, HRV, TSB, weather).")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Mental-coach trigger check skipped: %s", exc)


if __name__ == "__main__":
    main()
