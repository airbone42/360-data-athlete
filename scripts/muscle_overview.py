"""Terminal overview of current muscle fatigue status.

Reads data/muscles/YYYY-MM-DD.json files (last 30 days by default),
computes per-muscle fatigue, and displays a grouped table with ANSI colors.

Usage:
    python3 scripts/muscle_overview.py              # show overview
    python3 scripts/muscle_overview.py --days 14    # shorter window
    python3 scripts/muscle_overview.py --backfill 30  # run historical log first
    python3 scripts/muscle_overview.py --review-unmapped  # show queue of unknown exercises
    python3 scripts/muscle_overview.py --json       # machine-readable output
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.utils.paths import DATA_DIR as _DATA_ROOT, resolve_config  # noqa: E402

DATA_DIR = _DATA_ROOT / "muscles"
UNMAPPED_PATH = DATA_DIR / "_unmapped.jsonl"
MUSCLE_DB_PATH = resolve_config("muscle_db.md")
ATHLETE_TZ = ZoneInfo("Europe/Berlin")

# ── ANSI colors ───────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
GRAY   = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

FATIGUE_LOW_THRESHOLD  = 30.0   # ≤ → green (trainierbar)
FATIGUE_HIGH_THRESHOLD = 65.0   # > → red (pausieren)


# ── Muscle DB ─────────────────────────────────────────────────────────────────

def _parse_muscle_db() -> dict[str, list[tuple[str, str]]]:
    """Return {section_name: [(muscle_id, regen_group), ...]}."""
    with open(MUSCLE_DB_PATH) as f:
        content = f.read()
    sections = re.split(r"^### (.+)$", content, flags=re.MULTILINE)
    groups: dict[str, list[tuple[str, str]]] = {}
    for i in range(1, len(sections), 2):
        section_name = sections[i].strip()
        section_body = sections[i + 1]
        rows = [
            l for l in section_body.split("\n")
            if l.startswith("|") and not l.startswith("| ID") and not l.startswith("|---")
        ]
        muscles: list[tuple[str, str]] = []
        for row in rows:
            cols = [c.strip() for c in row.split("|")[1:-1]]
            if len(cols) >= 3 and cols[0] and not cols[0].startswith("-"):
                muscles.append((cols[0], cols[2]))  # (muscle_id, regen_group)
        if muscles:
            groups[section_name] = muscles
    return groups


# ── Load aggregation ──────────────────────────────────────────────────────────

def _collect_loads(days: int) -> dict[str, dict]:
    """Aggregate loads per muscle over the last N days.

    Returns dict: muscle_id → {
        strength_load_total: float,
        cardio_load_total: float,
        rpe_peak: float,
        last_load_date: str | None,   # most recent date with any load
        sets_total: int,
    }
    """
    today = date.today()
    results: dict[str, dict] = {}

    for delta in range(days):
        d = today - timedelta(days=delta)
        path = DATA_DIR / f"{d.isoformat()}.json"
        if not path.exists():
            continue
        try:
            day_data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        for session in day_data.get("sessions", []):
            for muscle_id, vals in session.get("muscle_load", {}).items():
                if muscle_id not in results:
                    results[muscle_id] = {
                        "strength_load_total": 0.0,
                        "cardio_load_total": 0.0,
                        "rpe_peak": 0.0,
                        "last_load_date": None,
                        "sets_total": 0,
                    }
                r = results[muscle_id]
                r["strength_load_total"] += vals.get("strength_load", 0.0)
                r["rpe_peak"] = max(r["rpe_peak"], vals.get("rpe_peak", 0.0))
                r["sets_total"] += vals.get("sets", 0)
                # Track most recent date (delta=0 is today, smaller delta = more recent)
                if r["last_load_date"] is None:
                    r["last_load_date"] = d.isoformat()

            for muscle_id, vals in session.get("cardio_load", {}).items():
                if muscle_id not in results:
                    results[muscle_id] = {
                        "strength_load_total": 0.0,
                        "cardio_load_total": 0.0,
                        "rpe_peak": 0.0,
                        "last_load_date": None,
                        "sets_total": 0,
                    }
                r = results[muscle_id]
                r["cardio_load_total"] += vals.get("cardio_load", 0.0)
                r["rpe_peak"] = max(r["rpe_peak"], vals.get("rpe_peak", 0.0))
                if r["last_load_date"] is None:
                    r["last_load_date"] = d.isoformat()

    return results


def _compute_fatigue(muscle_id: str, regen_group: str, last_load_date: str | None, rpe_peak: float) -> float:
    """Return fatigue_pct_remaining (0–100). 0 if no recent load."""
    from app.analytics.muscle_load import (
        fatigue_pct_remaining, rpe_to_tier, regen_hours_for_muscle, REGEN_HOURS,
    )
    if last_load_date is None:
        return 0.0

    today = date.today()
    last = date.fromisoformat(last_load_date)
    hours_since = (today - last).total_seconds() / 3600.0

    tier = rpe_to_tier(rpe_peak if rpe_peak > 0 else None)
    regen_h = REGEN_HOURS.get(regen_group, REGEN_HOURS["medium"]).get(tier, 60.0)
    return fatigue_pct_remaining(hours_since, regen_h)


def _next_ok_hours(regen_group: str, rpe_peak: float) -> float:
    """Return hours until fatigue drops below 30% (ready to train)."""
    from app.analytics.muscle_load import (
        next_optimal_hours, rpe_to_tier, REGEN_HOURS,
    )
    tier = rpe_to_tier(rpe_peak if rpe_peak > 0 else None)
    regen_h = REGEN_HOURS.get(regen_group, REGEN_HOURS["medium"]).get(tier, 60.0)
    # Time until fatigue ≤ 30%
    from app.analytics.muscle_load import decay_tau
    import math
    tau = decay_tau(regen_h)
    return tau * math.log(100.0 / 30.0)  # hours until 30%


# ── Formatting helpers ────────────────────────────────────────────────────────

def _fatigue_badge(pct: float) -> str:
    if pct <= FATIGUE_LOW_THRESHOLD:
        return f"{GREEN}🟢 {pct:4.0f}%{RESET}"
    if pct <= FATIGUE_HIGH_THRESHOLD:
        return f"{YELLOW}🟡 {pct:4.0f}%{RESET}"
    return f"{RED}🔴 {pct:4.0f}%{RESET}"


def _next_ok_str(fatigue_pct: float, regen_group: str, rpe_peak: float) -> str:
    if fatigue_pct <= FATIGUE_LOW_THRESHOLD:
        return f"{GREEN}JETZT{RESET}"
    next_h = _next_ok_hours(regen_group, rpe_peak)
    today = date.today()
    ok_dt = datetime.now(ATHLETE_TZ) + timedelta(hours=next_h)
    if ok_dt.date() == today:
        return f"heute ~{ok_dt.strftime('%H:%M')}"
    days_diff = (ok_dt.date() - today).days
    return f"in {days_diff}d (~{ok_dt.strftime('%d.%m %H:%M')})"


def _last_load_str(last_load_date: str | None) -> str:
    if last_load_date is None:
        return f"{GRAY}>30d{RESET}"
    today = date.today()
    d = date.fromisoformat(last_load_date)
    delta = (today - d).days
    if delta == 0:
        return "heute"
    if delta == 1:
        return "gestern"
    return f"vor {delta}d"


# ── Display ───────────────────────────────────────────────────────────────────

def _print_overview(groups: dict[str, list[tuple[str, str]]], loads: dict[str, dict], days: int) -> None:
    today = date.today()
    print(f"\n{BOLD}🩻 Muscle Overview — {today.isoformat()} (letzte {days} Tage){RESET}\n")

    # Column headers
    hdr = f"  {'Muskel':<42} {'Last Load':<12} {'Load':<10} {'Fatigue':<16} {'Next OK':<22}"
    print(f"{BOLD}{hdr}{RESET}")
    print("  " + "─" * 100)

    for section_name, muscles in groups.items():
        # Only print section if at least one muscle has data OR if showing all
        has_data = any(m[0] in loads for m in muscles)
        print(f"\n  {BOLD}{section_name}{RESET}")

        for muscle_id, regen_group in muscles:
            data = loads.get(muscle_id)
            if data is None:
                # No load in window → fresh — pad BEFORE colorizing to preserve alignment
                name_pad = f"{muscle_id:<42}"
                row = (
                    f"  {GRAY}{name_pad}{RESET}"
                    f" {GRAY}{'—':<12}{RESET}"
                    f" {GRAY}{'—':<10}{RESET}"
                    f" {GREEN}🟢   0%{RESET}     "
                    f" {GREEN}JETZT{RESET}"
                )
                print(row)
                continue

            last_str = _last_load_str(data["last_load_date"])
            fatigue = _compute_fatigue(muscle_id, regen_group, data["last_load_date"], data["rpe_peak"])
            badge = _fatigue_badge(fatigue)
            next_str = _next_ok_str(fatigue, regen_group, data["rpe_peak"])

            # Combined load display (strength + cardio)
            s_load = data["strength_load_total"]
            c_load = data["cardio_load_total"]
            if s_load > 0 and c_load > 0:
                load_str = f"S:{s_load:.1f}+C:{c_load:.2f}"
            elif s_load > 0:
                load_str = f"S:{s_load:.1f}"
            elif c_load > 0:
                load_str = f"C:{c_load:.2f}"
            else:
                load_str = "—"

            # Pad visible fields before adding color codes for correct terminal alignment
            row = (
                f"  {muscle_id:<42}"
                f" {last_str:<12}"
                f" {load_str:<18}"
                f" {badge}"
                f"   {next_str}"
            )
            print(row)

    print(f"\n  {BOLD}Legende:{RESET}")
    print(f"  {GREEN}🟢 ≤30% Fatigue — trainierbar{RESET} | {YELLOW}🟡 30–65% — leicht/moderat{RESET} | {RED}🔴 >65% — pausieren{RESET}")
    print(f"  S = Strength-Last | C = Cardio-Last (separate Skalen, nicht addieren)")
    print()


def _print_json(groups: dict[str, list[tuple[str, str]]], loads: dict[str, dict]) -> None:
    output = {}
    for section_name, muscles in groups.items():
        section_data = []
        for muscle_id, regen_group in muscles:
            data = loads.get(muscle_id)
            fatigue = 0.0
            if data:
                fatigue = _compute_fatigue(muscle_id, regen_group, data["last_load_date"], data["rpe_peak"])
            section_data.append({
                "muscle": muscle_id,
                "regen_group": regen_group,
                "fatigue_pct": round(fatigue, 1),
                "last_load_date": data["last_load_date"] if data else None,
                "strength_load_30d": round(data["strength_load_total"], 3) if data else 0.0,
                "cardio_load_30d": round(data["cardio_load_total"], 3) if data else 0.0,
                "rpe_peak": data["rpe_peak"] if data else 0.0,
            })
        output[section_name] = section_data
    print(json.dumps(output, ensure_ascii=False, indent=2))


def _print_unmapped() -> None:
    if not UNMAPPED_PATH.exists():
        print("Keine ungekannten Übungen in der Queue.")
        return
    entries = []
    with open(UNMAPPED_PATH) as f:
        for line in f:
            try:
                entries.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue

    if not entries:
        print("Queue leer — alle Übungen gemappt.")
        return

    print(f"\n{BOLD}Unmapped Exercise Queue ({len(entries)} Einträge){RESET}\n")
    # Deduplicate by parsed_name
    seen: dict[str, dict] = {}
    for e in entries:
        name = e.get("parsed_name", "?")
        if name not in seen:
            seen[name] = {"count": 0, "example": e.get("raw", ""), "dates": []}
        seen[name]["count"] += 1
        d = e.get("date", "")
        if d not in seen[name]["dates"]:
            seen[name]["dates"].append(d)

    print(f"  {'Parsed Name':<40} {'Count':>6}  {'Dates'}")
    print("  " + "─" * 80)
    for name, info in sorted(seen.items(), key=lambda x: -x[1]["count"]):
        dates_str = ", ".join(sorted(info["dates"])[-3:])
        print(f"  {name:<40} {info['count']:>6}  {dates_str}")
        if info["example"] and info["example"] != "(unresolved)":
            print(f"    {GRAY}→ raw: {info['example'][:80]}{RESET}")
    print()


# ── Backfill integration ──────────────────────────────────────────────────────

async def _backfill_and_show(days: int, silent_fill: bool) -> None:
    """Run backfill then show overview."""
    # Import here to avoid circular
    from scripts.log_muscle_load import _backfill
    print(f"Backfill der letzten {days} Tage läuft...")
    await _backfill(days, silent=silent_fill)
    print("Backfill abgeschlossen.\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Muskel-Übersicht anzeigen")
    parser.add_argument("--days", type=int, default=30, help="Aggregations-Fenster in Tagen (default: 30)")
    parser.add_argument("--backfill", type=int, metavar="DAYS", help="Vor der Anzeige N Tage Backfill laufen lassen")
    parser.add_argument("--review-unmapped", action="store_true", help="Queue unbekannter Übungen anzeigen")
    parser.add_argument("--json", action="store_true", help="JSON-Output statt Terminal-Tabelle")
    args = parser.parse_args()

    if args.backfill:
        asyncio.run(_backfill_and_show(args.backfill, silent_fill=False))

    if args.review_unmapped:
        _print_unmapped()
        return

    groups = _parse_muscle_db()
    loads = _collect_loads(args.days)

    if args.json:
        _print_json(groups, loads)
    else:
        _print_overview(groups, loads, args.days)


if __name__ == "__main__":
    main()
