"""Log muscle load from an intervals.icu activity to data/muscles/YYYY-MM-DD.json.

Reads the activity description, matches exercises to exercise_muscle_mapping.json,
computes per-muscle fatigue, and writes the daily load file.

For endurance activities (Run/Ride), uses icu_hr_zone_times from the activity.
Idempotent: re-running with the same activity_id overwrites that session entry.

Usage:
    python3 scripts/log_muscle_load.py --activity-id i12345678
    python3 scripts/log_muscle_load.py --activity-id i12345678 --silent
    python3 scripts/log_muscle_load.py --backfill 30
    python3 scripts/log_muscle_load.py --backfill 30 --silent
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.utils.paths import DATA_DIR as _DATA_ROOT, resolve_config  # noqa: E402

DATA_DIR = _DATA_ROOT / "muscles"
MAPPING_PATH = resolve_config("exercise_muscle_mapping.json")
E1RM_STATE_PATH = DATA_DIR / "_e1rm_state.json"
UNMAPPED_PATH = DATA_DIR / "_unmapped.jsonl"
ATHLETE_TZ = ZoneInfo("Europe/Berlin")
EMA_ALPHA = 0.3

# Zone index → zone name mapping (intervals.icu icu_hr_zone_times is [Z1,Z2,Z3,Z4,Z5])
ZONE_NAMES = ["Z1", "Z2", "Z3", "Z4", "Z5"]
# Which mapping key to use per zone (endurance activities)
ZONE_TO_MAPPING: dict[str, dict[str, str]] = {
    "run":  {"Z1": "run_z1_z2", "Z2": "run_z1_z2", "Z3": "run_z3", "Z4": "run_z4_z5", "Z5": "run_z4_z5"},
    "ride": {"Z1": "ride_z1_z2", "Z2": "ride_z1_z2", "Z3": "ride_z3", "Z4": "ride_z4_z5", "Z5": "ride_z4_z5"},
}
ENDURANCE_ACTIVITY_TYPES = {"Run", "Ride", "VirtualRun", "VirtualRide"}
STRENGTH_ACTIVITY_TYPES = {"WeightTraining", "Workout"}
HANDLED_ACTIVITY_TYPES = ENDURANCE_ACTIVITY_TYPES | STRENGTH_ACTIVITY_TYPES


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_mapping() -> dict:
    with open(MAPPING_PATH) as f:
        data = json.load(f)
    # Strip _meta key if present
    data.pop("_meta", None)
    return data


def _load_e1rm_state() -> dict:
    if E1RM_STATE_PATH.exists():
        return json.loads(E1RM_STATE_PATH.read_text())
    return {}


def _save_e1rm_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = E1RM_STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    tmp.rename(E1RM_STATE_PATH)


def _load_day(date_str: str) -> dict:
    path = DATA_DIR / f"{date_str}.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"date": date_str, "sessions": []}


def _save_day(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{data['date']}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    tmp.rename(path)


def _append_unmapped(exercise_name: str, raw_line: str, activity_id: str, date_str: str) -> None:
    from app.utils.sanitize import escape_for_prompt
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "date": date_str,
        "activity_id": activity_id,
        # raw line originates from a user-controlled activity description.
        # The _unmapped.jsonl file is later read by the audit/review flow and
        # may be loaded into an LLM context for mapping decisions — escape
        # injection-friendly characters before persisting.
        "raw": escape_for_prompt(raw_line, max_len=500),
        "parsed_name": escape_for_prompt(exercise_name, max_len=200),
    }
    with open(UNMAPPED_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _modality_from_type(activity_type: str) -> str | None:
    # Virtual variants load the same muscles as their outdoor counterpart.
    if activity_type in ("Run", "VirtualRun"):
        return "run"
    if activity_type in ("Ride", "VirtualRide"):
        return "ride"
    return None


def _report_skipped(skipped: list[dict]) -> None:
    """One-line stderr summary of activities dropped for unhandled types.

    Printed even with --silent (the analyse flow always runs silent) so a
    missing data/muscles/YYYY-MM-DD.json reliably means "rest day", not
    "activity type silently dropped".
    """
    if not skipped:
        return
    type_counts: dict[str, int] = {}
    for a in skipped:
        t = a.get("type") or "?"
        type_counts[t] = type_counts.get(t, 0) + 1
    print(
        f"skipped {len(skipped)} activities with unhandled types: {type_counts}",
        file=sys.stderr,
    )


def _zone_minutes_from_activity(activity: dict) -> dict[str, float]:
    """Extract zone minutes from icu_hr_zone_times (seconds per zone, 0-indexed)."""
    zone_times_secs: list = activity.get("icu_hr_zone_times") or []
    result: dict[str, float] = {}
    for i, name in enumerate(ZONE_NAMES):
        secs = zone_times_secs[i] if i < len(zone_times_secs) else 0
        if secs > 0:
            result[name] = round(secs / 60.0, 2)
    return result


def _elevation_loss(activity: dict) -> float:
    """Return elevation loss in metres (positive value)."""
    return float(activity.get("total_elevation_loss") or 0.0)


# ── Core processing ───────────────────────────────────────────────────────────

def _process_strength(
    activity: dict,
    mapping: dict,
    e1rm_state: dict,
    date_str: str,
    activity_id: str,
    silent: bool,
) -> dict:
    """Parse description → match exercises → compute muscle fatigue."""
    from app.analytics.exercise_parser import parse_description, match_to_mapping_key
    from app.analytics.muscle_load import (
        SetResult, MuscleEntry, CONTRIBUTION,
        estimate_e1rm, rpe_to_rir, compute_set_fatigue, aggregate_session_load,
    )

    description = activity.get("description") or ""
    parsed_exercises, unmapped_lines = parse_description(description)

    exercises_log: list[dict] = []
    muscle_load_raw: dict[str, dict] = {}

    newly_unmapped: list[tuple[str, str]] = []  # (parsed_name, raw_line)

    for pe in parsed_exercises:
        if not pe.name:
            continue
        mapping_key = match_to_mapping_key(pe.name, mapping)
        if mapping_key is None:
            _append_unmapped(pe.name, pe.raw_line, activity_id, date_str)
            newly_unmapped.append((pe.name, pe.raw_line))
            if not silent:
                print(f"  [unmapped] {pe.name!r} — raw: {pe.raw_line!r}")
            continue

        ex_mapping = mapping[mapping_key]
        load_mode = ex_mapping.get("load_mode", "free_weight")
        eccentric_dominant = ex_mapping.get("eccentric_dominant", False)
        lever_factor = ex_mapping.get("lever_factor", 1.0)

        # Update e1RM state (EMA α=0.3) for weighted free_weight sets
        if pe.weight_kg and pe.reps and load_mode == "free_weight":
            rir = rpe_to_rir(pe.rpe or 6.0)
            adj_reps = pe.reps + rir
            new_e1rm = estimate_e1rm(pe.weight_kg, adj_reps)
            prev = e1rm_state.get(mapping_key)
            e1rm_state[mapping_key] = (
                EMA_ALPHA * new_e1rm + (1 - EMA_ALPHA) * prev if prev else new_e1rm
            )

        e1rm = e1rm_state.get(mapping_key)

        result = SetResult(
            exercise_key=mapping_key,
            weight_kg=pe.weight_kg,
            reps=pe.reps,
            duration_s=pe.duration_s,
            rpe=pe.rpe,
            per_side=pe.per_side,
            load_mode=load_mode,
            lever_factor=lever_factor,
            eccentric_dominant=eccentric_dominant,
        )

        exercises_log.append({
            "mapping_key": mapping_key,
            "name": pe.name,
            "sets": pe.sets,
            "reps": pe.reps,
            "duration_s": pe.duration_s,
            "weight_kg": pe.weight_kg,
            "rpe": pe.rpe,
            "per_side": pe.per_side,
            "load_mode": load_mode,
        })

        # Compute fatigue for each muscle role
        n_sets = pe.sets or 1
        all_muscles = (
            [(m["muscle"], m["intensity"], "primary")   for m in ex_mapping.get("primary", [])] +
            [(m["muscle"], m["intensity"], "secondary") for m in ex_mapping.get("secondary", [])] +
            [(m["muscle"], m["intensity"], "stabilizer") for m in ex_mapping.get("stabilizer", [])]
        )

        for muscle_id, intensity, role in all_muscles:
            entry = MuscleEntry(muscle=muscle_id, intensity=intensity, role=role)
            fat_per_set = compute_set_fatigue(result, entry, e1rm)
            total_fat = fat_per_set * n_sets

            if muscle_id not in muscle_load_raw:
                muscle_load_raw[muscle_id] = {"strength_load": 0.0, "rpe_peak": 0.0, "sets": 0}
            muscle_load_raw[muscle_id]["strength_load"] += total_fat
            muscle_load_raw[muscle_id]["rpe_peak"] = max(
                muscle_load_raw[muscle_id]["rpe_peak"], result.rpe or 6.0
            )
            muscle_load_raw[muscle_id]["sets"] += n_sets

    # Log unmapped lines that weren't already caught
    for raw_line in unmapped_lines:
        _append_unmapped("(unresolved)", raw_line, activity_id, date_str)
        if not silent:
            print(f"  [unresolved] {raw_line!r}")

    # Always surface real unmapped exercises — even in silent mode
    if newly_unmapped:
        print(f"\n⚠️  MAPPING FEHLT — {len(newly_unmapped)} unbekannte Übung(en) in {activity_id} ({date_str}):")
        for name, raw in newly_unmapped:
            print(f"   • {name!r}  ← {raw[:80]}")
        print(f"   → Mapping ergänzen in config/exercise_muscle_mapping.json")
        print(f"   → Dann: python3 scripts/log_muscle_load.py --backfill 30 --force --silent\n")

    return {
        "exercises": exercises_log,
        "muscle_load": muscle_load_raw,
        "cardio_load": {},
        "newly_unmapped": newly_unmapped,
    }


def _process_endurance(
    activity: dict,
    mapping: dict,
    date_str: str,
    activity_id: str,
    silent: bool,
) -> dict:
    """Compute cardio muscle fatigue from zone distribution."""
    from app.analytics.muscle_load import aggregate_endurance_load

    activity_type = activity.get("type", "")
    modality = _modality_from_type(activity_type)
    if not modality:
        return {"exercises": [], "muscle_load": {}, "cardio_load": {}}

    zone_minutes = _zone_minutes_from_activity(activity)
    elev_loss = _elevation_loss(activity)

    if not zone_minutes:
        if not silent:
            print(f"  [endurance] no HR zone data for {activity_id}")
        return {"exercises": [], "muscle_load": {}, "cardio_load": {}}

    session_loads = aggregate_endurance_load(zone_minutes, modality, elev_loss, mapping)

    cardio_load: dict[str, dict] = {}
    for muscle_id, sml in session_loads.items():
        cardio_load[muscle_id] = {
            "cardio_load": round(sml.fatigue_contribution, 4),
            "rpe_peak": sml.rpe_peak,
            "sets": sml.sets_count,
        }

    if not silent:
        total_min = sum(zone_minutes.values())
        print(f"  [endurance] {modality} {total_min:.0f} min | zones: {zone_minutes} | {len(cardio_load)} muscles")

    return {
        "exercises": [],
        "muscle_load": {},
        "cardio_load": cardio_load,
    }


# ── Main per-activity logic ────────────────────────────────────────────────────

def _process_activity(
    activity: dict,
    mapping: dict,
    e1rm_state: dict,
    date_str: str,
    activity_id: str,
    silent: bool,
) -> dict | None:
    """Process one activity and return the session dict to be stored."""
    activity_type = activity.get("type", "")
    start_local = activity.get("start_date_local", "")
    time_str = start_local[11:16] if len(start_local) >= 16 else "??"
    workout_name = activity.get("name", activity_type)

    if not silent:
        print(f"  Processing {activity_id}: {workout_name!r} ({activity_type}) @ {time_str}")

    if activity_type in ENDURANCE_ACTIVITY_TYPES:
        result = _process_endurance(activity, mapping, date_str, activity_id, silent)
    elif activity_type in STRENGTH_ACTIVITY_TYPES:
        result = _process_strength(activity, mapping, e1rm_state, date_str, activity_id, silent)
    else:
        if not silent:
            print(f"  [skip] unknown type {activity_type!r}")
        return None

    session = {
        "activity_id": activity_id,
        "time": time_str,
        "workout_name": workout_name,
        "activity_type": activity_type,
        **result,
    }
    return session


async def _log_single(activity_id: str, silent: bool) -> None:
    from app.api.intervals_client import IntervalsClient

    client = IntervalsClient()
    activity = await client.get_activity(activity_id)

    # Normalise activity_id (ensure "i" prefix)
    norm_id = activity_id if activity_id.startswith("i") else f"i{activity_id}"
    start_local = activity.get("start_date_local", "")
    date_str = start_local[:10] if start_local else date.today().isoformat()

    mapping = _load_mapping()
    e1rm_state = _load_e1rm_state()
    day_data = _load_day(date_str)

    # Idempotency: remove existing session with same activity_id
    day_data["sessions"] = [
        s for s in day_data["sessions"] if s.get("activity_id") != norm_id
    ]

    session = _process_activity(activity, mapping, e1rm_state, date_str, norm_id, silent)
    if session:
        day_data["sessions"].append(session)
        _save_day(day_data)
        _save_e1rm_state(e1rm_state)
        if not silent:
            print(f"  → wrote data/muscles/{date_str}.json")
    else:
        # Surface the drop even in silent mode — "no file" must mean rest day.
        _report_skipped([activity])
        if not silent:
            print(f"  → skipped (unsupported type)")


async def _backfill(days: int, silent: bool, force: bool = False) -> None:
    from app.api.intervals_client import IntervalsClient

    client = IntervalsClient()
    today = date.today()
    oldest = today - timedelta(days=days - 1)

    if not silent:
        print(f"Backfill: {oldest.isoformat()} → {today.isoformat()} ({days} days)")

    activities = await client.get_activities(
        oldest=oldest.isoformat(), newest=today.isoformat()
    )

    # Filter to strength/endurance only — and surface the drop even in
    # silent mode, so unhandled types never disappear without trace.
    relevant = [a for a in activities if a.get("type") in HANDLED_ACTIVITY_TYPES]
    _report_skipped([a for a in activities if a.get("type") not in HANDLED_ACTIVITY_TYPES])
    if not silent:
        print(f"Found {len(relevant)} relevant activities (of {len(activities)} total)")

    mapping = _load_mapping()
    e1rm_state = _load_e1rm_state()

    # Group by date
    by_date: dict[str, list[dict]] = {}
    for a in relevant:
        start_local = a.get("start_date_local", "")
        d = start_local[:10] if start_local else "unknown"
        by_date.setdefault(d, []).append(a)

    for date_str in sorted(by_date.keys()):
        day_acts = by_date[date_str]
        day_data = _load_day(date_str)

        # Fetch full activity detail for each (backfill needs description + zone data)
        for a in day_acts:
            raw_id = str(a.get("id", ""))
            norm_id = raw_id if raw_id.startswith("i") else f"i{raw_id}"

            # Check if already logged
            existing = [s for s in day_data["sessions"] if s.get("activity_id") == norm_id]
            if existing and not force:
                if not silent:
                    print(f"  [skip] {norm_id} already logged in {date_str}")
                continue
            if existing and force:
                day_data["sessions"] = [s for s in day_data["sessions"] if s.get("activity_id") != norm_id]

            # Fetch full activity (description may not be in list response)
            try:
                full_activity = await client.get_activity(norm_id)
            except Exception as e:
                if not silent:
                    print(f"  [error] failed to fetch {norm_id}: {e}")
                continue

            session = _process_activity(full_activity, mapping, e1rm_state, date_str, norm_id, silent)
            if session:
                day_data["sessions"].append(session)

        _save_day(day_data)
        _save_e1rm_state(e1rm_state)
        if not silent:
            print(f"  → {date_str}: {len(day_acts)} activities → saved")

    if not silent:
        print(f"\nBackfill complete. e1RM state: {len(e1rm_state)} exercises tracked.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Muskel-Last einer Activity loggen")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--activity-id", help="Activity-ID (z.B. i12345678)")
    group.add_argument("--backfill", type=int, metavar="DAYS", help="Letzten N Tage rückwirkend befüllen")
    parser.add_argument("--silent", action="store_true", help="Keine stdout-Ausgabe (für /analyse-Integration)")
    parser.add_argument("--force", action="store_true", help="Bereits geloggte Activities neu verarbeiten (nach Mapping-Updates)")
    args = parser.parse_args()

    if args.activity_id:
        asyncio.run(_log_single(args.activity_id, args.silent))
    else:
        asyncio.run(_backfill(args.backfill, args.silent, force=args.force))


if __name__ == "__main__":
    main()
