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

from app.api.intervals_cache import CachedIntervalsClient
from app.config import settings
from app.utils.event_backup import backup_events_before_delete
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


async def _dedup_existing_events(
    athlete_id: str, date_str: str, events: list[dict], incremental: bool = False
) -> int:
    """Delete existing intervals.icu events on `date_str` that match name+type
    of any to-be-pushed event.

    Idempotency safety-net: intervals.icu's `upsert=true` matches on its own
    server-side `uid`, not the client-provided `coach-{date}-{i}` value, so
    repeated push calls would otherwise pile up duplicates (pattern from
    real usage). This pre-push sweep guarantees `push_workouts.py` is safe
    to call twice in a row.

    `incremental=True` narrows the sweep to exact (name, type) matches: the
    push ADDS events to an already-planned day instead of regenerating it, so
    same-type siblings pushed earlier must survive. Use for late add-ons
    (a gated block released by the athlete, a reaction block after a symptom
    report). The default full-regeneration sweep would delete those siblings —
    that is the correct semantic only when the whole day is re-planned.

    Returns the number of events deleted.
    """
    client = CachedIntervalsClient(athlete_id)
    try:
        existing = await client.get_events(date_str, date_str)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Pre-push dedup: failed to fetch existing events (%s) — proceeding without sweep", exc)
        return 0
    # Match key: (TYPE, is_balance) — not name+type. A coach re-push
    # regenerates the full daily plan, so it must replace the previously-pushed
    # planned events of the same type(s) — regardless of whether the workout was
    # renamed between pushes. Matching on name broke exactly that: a renamed
    # workout left the stale, old-named event behind and the day ended up with a
    # duplicate. intervals assigns a random server-side uid and stores no
    # external_id, so there is no stable per-event coach marker to match on; the
    # type of the regenerated plan is the reliable key.
    #
    # The `is_balance` partition (tag `balance`) is required because the daily
    # balance rotation is pushed in a SEPARATE call (`_auto_push_balance`, a
    # post-step after the main push). Balance events are `type="Workout"`, and
    # so are ninja / mobility / generic-strength mains — a pure type match made
    # the balance push's dedup delete the freshly-created mains (and vice
    # versa) whenever both shared `type="Workout"` (a ninja or mobility day).
    # Partitioning the key on balance-ness keeps a balance push replacing only
    # balance events and a main push replacing only non-balance events, while a
    # combined push (mains + balance in one call) still replaces both. The
    # type-based rename robustness is preserved within each partition.
    #
    # Guards: only planned WORKOUT-category events (never RACE_A/B/C, never
    # NOTE which has type=None), and never an event already paired to a
    # completed activity (don't touch what the athlete has actually done).
    def _is_balance(ev: dict) -> bool:
        return "balance" in (ev.get("tags") or [])

    if incremental:
        # Add-on semantics: replace only an event this push re-sends by exact
        # (name, type) — never same-type siblings from an earlier push.
        push_keys = {(e.get("name"), e.get("type")) for e in events if e.get("type")}
        to_delete = [
            ev for ev in existing
            if ev.get("category") == "WORKOUT"
            and (ev.get("name"), ev.get("type")) in push_keys
            and not ev.get("paired_activity_id")
        ]
    else:
        push_keys = {(e.get("type"), _is_balance(e)) for e in events if e.get("type")}
        to_delete = [
            ev for ev in existing
            if ev.get("category") == "WORKOUT"
            and (ev.get("type"), _is_balance(ev)) in push_keys
            and not ev.get("paired_activity_id")
        ]
        # Heads-up when the full-regeneration sweep is about to remove events
        # the push set does not re-send by name: correct on a true re-plan,
        # but the signature of a forgotten --incremental on an add-on push
        # (pattern from real usage: a late mobility block deleted the day's
        # already-pushed core session).
        push_names = {e.get("name") for e in events}
        collateral = [ev.get("name") for ev in to_delete if ev.get("name") not in push_names]
        if collateral:
            logger.warning(
                "Pre-push dedup will DELETE same-type event(s) not re-sent by this push: %s — "
                "intended only for a full day re-plan; use --incremental to add to an existing day.",
                collateral,
            )
    if not to_delete:
        return 0
    logger.info(
        "Pre-push dedup: deleting %d existing event(s) on %s matching push set: %s",
        len(to_delete), date_str, [(e.get("name"), e.get("type"), e.get("id")) for e in to_delete],
    )
    # Safety net: capture full content BEFORE deleting so a dedup sweep can
    # never silently lose a planned block that was not meant to be regenerated.
    backup_events_before_delete(to_delete, reason=f"push-dedup {date_str}")
    for ev in to_delete:
        try:
            await client.delete_event(ev["id"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pre-push dedup: failed to delete event %s (%s) — continuing", ev.get("id"), exc)
    return len(to_delete)


async def _push(
    athlete_id: str, events: list[dict], dry_run: bool, date_str: str, incremental: bool = False
) -> list[dict]:
    if dry_run:
        logger.info("[DRY-RUN] Would create %d event(s): %s", len(events), [e.get("uid") for e in events])
        return [{"uid": e["uid"], "dry_run": True} for e in events]
    await _dedup_existing_events(athlete_id, date_str, events, incremental=incremental)
    client = CachedIntervalsClient(athlete_id)
    created = await client.post_events_bulk(events)
    return created


def _format_shoe_footer(
    shoe_ctx: dict,
    include_gear_marker: bool = False,
    planned_workout: dict | None = None,
) -> str:
    """Render a shoe-recommendation footer for run/ride descriptions.

    Uses the primary shoe name, km, and the advisor's reason string (which
    includes type/terrain or rotation hints).

    When ``include_gear_marker`` is set (intervals.icu backend), two trailing
    machine-readable markers are appended:

    - ``[coach-gear:<gear_id>]`` — the push-time shoe pick as the single source
      of truth. ``/analyse`` step 6.55 (set_activity_gear) reads it back and
      assigns exactly that shoe to the finished activity, matching the push
      pick (which already weighed surface, pace, preferences, mileage,
      rotation, weather) instead of re-deriving from partial data.
    - ``[coach-plan:surface=…,workout_type=…,intensity=…]`` — the planner
      metadata that shaped the pick. Persisting it makes the same filters
      (terrain, pace bucket) reproducible at read-time, so the context path
      re-derives the same recommendation as the push path from identical
      inputs. When ``planned_workout`` is None or the fields are empty, the
      marker is skipped rather than emitted with placeholder values (so the
      read side sees "unknown" instead of a fabricated default).
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
    if include_gear_marker and primary.get("gear_id"):
        line += f"\n[coach-gear:{primary['gear_id']}]"
        if planned_workout:
            plan_marker = _format_coach_plan_marker(planned_workout)
            if plan_marker:
                line += f"\n{plan_marker}"
    return line


def _format_coach_plan_marker(planned_workout: dict) -> str:
    """Serialise the decision-shaping planner fields into a machine marker.

    Only non-empty scalar fields are included, in a fixed order for stable
    output. Values are restricted to ``[A-Za-z0-9._/-]`` (the enum values
    used by planner/specialist output today — asphalt/forest-path/trail/…,
    EASY/LONG/INTERVALS/…, low/medium/high) so the marker survives round-trip
    without escaping. Any value containing other characters is skipped rather
    than emitted, so the reader defaults to "unknown" for that field instead
    of parsing a distorted value.
    """
    import re as _re
    _SAFE_VALUE = _re.compile(r"^[A-Za-z0-9._/-]+$")
    ordered_keys = ("surface", "workout_type", "intensity")
    parts: list[str] = []
    for k in ordered_keys:
        v = planned_workout.get(k)
        if v is None:
            continue
        vs = str(v).strip()
        if not vs or not _SAFE_VALUE.match(vs):
            continue
        parts.append(f"{k}={vs}")
    if not parts:
        return ""
    return "[coach-plan:" + ",".join(parts) + "]"


async def _enrich_with_shoes(events: list[dict], workouts: list[dict], weather: str, date_str: str) -> None:
    """Append shoe-recommendation footer to Run event descriptions in-place.

    The footer carries the recommendation **plus** a ``[coach-gear:<id>]``
    marker, so ``/analyse`` step 6.55 assigns *exactly* the push-time pick to
    the finished activity (deterministic, full-context) instead of
    re-deriving it. The native mileage accrues on the finished activity, not
    the plan.
    """
    if settings.shoe_tracking_backend != "intervals":
        return
    if not any(w.get("type") == "Run" for w in workouts):
        return
    try:
        shoe_ctx = await _recommend_shoes(workouts, weather, date_str)
    except Exception as exc:
        logger.warning("Shoe recommendation failed: %s — workouts pushed without shoe footer", exc)
        return
    # Same disambiguation as shoe_recommend.recommend(): the advisor scores
    # against the first Run workout in the plan. Persist that workout's
    # decision-shaping fields in the marker so the read path re-derives from
    # the same inputs.
    plan_wo: dict | None = next(
        (w for w in workouts if (w.get("type") if isinstance(w, dict) else getattr(w, "type", None)) == "Run"),
        None,
    )
    if plan_wo is not None and not isinstance(plan_wo, dict):
        plan_wo = plan_wo.model_dump() if hasattr(plan_wo, "model_dump") else dict(plan_wo)
    footer = _format_shoe_footer(
        shoe_ctx,
        include_gear_marker=(settings.shoe_tracking_backend == "intervals"),
        planned_workout=plan_wo,
    )
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
        "--incremental",
        action="store_true",
        help="Add to an already-planned day: the pre-push dedup replaces only "
             "exact (name, type) matches instead of sweeping all same-type "
             "planned events. Required for late add-ons (gated blocks, "
             "reaction blocks) so earlier-pushed siblings survive.",
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
    parser.add_argument(
        "--travel", "--no-equipment",
        dest="travel",
        action="store_true",
        help="Forwarded to the auto-balance rotation: swap equipment-dependent balance "
             "exercises (balance board / kettlebell / TRX) for bodyweight / soft-surface "
             "fallbacks. Default off.",
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
        created = asyncio.run(_push(athlete_id, events, args.dry_run, args.date, incremental=args.incremental))
        ids = [e.get("uid") or e.get("id") for e in created]
        set_span_io(
            input={"date": args.date, "workouts": workout_names, "dry_run": args.dry_run},
            output={"created": len(created), "ids": ids},
        )
    logger.info("push_workouts: created %d event(s): %s", len(created), ids)
    print(json.dumps(created, ensure_ascii=False, indent=2))

    if not args.dry_run:
        if not args.no_auto_balance:
            _auto_push_balance(args.date, workouts, athlete_id, travel=args.travel)
        _warn_on_warmup_overlap(args.date)
        _warn_on_mental_coach_triggers(workouts, args.date)


def _auto_push_balance(target_date: str, current_workouts: list, athlete_id: str, travel: bool = False) -> None:
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

    `travel` is forwarded to `build_rotation_workout` — swaps equipment-
    dependent exercises (balance board / kettlebell / TRX) for bodyweight /
    soft-surface fallbacks (see `get_balance_rotation.py --travel`).
    """
    try:
        for w in current_workouts:
            tags = w.get("tags") if isinstance(w, dict) else getattr(w, "tags", None)
            if tags and "balance" in tags:
                logger.debug("Auto-balance: balance already in current push, skipping")
                return
        from datetime import date as _date
        from get_balance_rotation import build_rotation_workout

        client = CachedIntervalsClient(athlete_id)
        existing = asyncio.run(client.get_events(target_date, target_date))
        if any("balance" in (e.get("tags") or []) for e in existing):
            logger.debug("Auto-balance: balance event already exists for %s, skipping", target_date)
            return

        rotation, workout = build_rotation_workout(_date.fromisoformat(target_date), travel=travel)
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
