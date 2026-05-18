"""Scan today's intervals.icu workouts for duplicated warm-up drills.

Holt alle WORKOUT-Events des Tages, scannt ihre Descriptions auf bekannte
Warm-up-/Drill-Tokens und meldet Doppelungen.

Designed als Sanity-Check NACH push_workouts.py — kann mehrfach pro Tag
laufen, weil push_workouts.py oft pro Workout separat aufgerufen wird
(Plyo, Lauf, Balance jeweils eigener Push).

Usage:
    python3 scripts/check_warmup_overlap.py [--date YYYY-MM-DD] [--json]

Exit Codes:
    0 — keine Doppelungen
    0 — Doppelungen gefunden (Warnung, nicht blocking)
    1 — technischer Fehler
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.intervals_client import IntervalsClient
from app.config import settings


# Drill-Tokens, die typischerweise im Warm-up auftauchen.
# Format: kanonischer Name → Liste regex-fähiger Synonyme (case-insensitive).
DRILL_PATTERNS: dict[str, list[str]] = {
    "A-Skips": [r"\bA-?Skip", r"\bA Skip"],
    "B-Skips": [r"\bB-?Skip", r"\bB Skip"],
    "Beinpendel/Leg Swings": [r"Beinpendel", r"Leg Swing"],
    "Hip Flexor Mobilität": [r"Hip Flexor", r"Hüftöffner", r"H[uü]ftbeuger"],
    "Knöchelkreisen": [r"Kn[oö]chelkreis", r"Ankle Circle", r"Fu[sß]gelenk-?Rotation"],
    "Ankle Bounces": [r"Ankle Bounce"],
    "Wadenheben (locker, im WU)": [r"Wadenheben locker"],
    "Steigerungen/Strides": [r"Steigerung", r"\bStride"],
    "Pogo Jumps/Hops": [r"Pogo[-\s]?(Hop|Jump)"],
    "Lateral Bound": [r"Lateral Bound"],
    "Arm-Pendel/Schulterkreisen": [r"Arm-?Pendel", r"Schulterkreis"],
    "Hampelmann/Jumping Jacks": [r"Hampelmann", r"Jumping Jack"],
    "High Knees/Kniehub": [r"\bHigh Knee", r"Kniehub"],
    "Butt Kicks/Anfersen": [r"Butt Kick", r"Anfersen"],
    "Cat-Cow": [r"Cat-?Cow"],
    "Hüftkreise": [r"H[uü]ftkreis"],
}


# Eine Übungs-Zeile muss eine Mengen-/Zeitangabe enthalten — sonst ist es Fließtext.
_QUANT_PATTERN = re.compile(
    r"\d+\s*(?:x|×|m\b|min\b|sec\b|s\b|/Seite|Wdh|Sätze|Hops|Reps|spm|°|sek)",
    flags=re.IGNORECASE,
)

# Section-Header (WARM-UP (5 min), HAUPTTEIL (12 min), BLOCK 1, ...) sind keine Übungen.
_SECTION_HEADER_PATTERN = re.compile(
    r"^(WARM-?UP|HAUPTTEIL|HAUPT-TEIL|COOL-?DOWN|AKTIVIERUNG|BLOCK\b|MAIN\b|FINISHER\b)",
    flags=re.IGNORECASE,
)


def _strip_parentheses(line: str) -> str:
    """Klammern-Inhalte entfernen — typische Annotationen ('A-Skips folgen im Lauf-WU')."""
    return re.sub(r"\([^)]*\)", "", line)


def _is_exercise_line(line: str) -> bool:
    """True wenn die Zeile wie eine Übungs-Anweisung aussieht.

    Filtert Section-Header heraus (WARM-UP (2 min) usw.).
    """
    if _SECTION_HEADER_PATTERN.match(line):
        return False
    return bool(_QUANT_PATTERN.search(line))


def find_drills(text: str) -> set[str]:
    """Return canonical drill names found as actual exercise instructions in text.

    Scannt zeilenweise und ignoriert Fließtext-Erwähnungen ohne Mengenangabe
    (z.B. Hinweise wie 'A-Skips folgen im Lauf-WU').
    """
    if not text:
        return set()
    found: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or not _is_exercise_line(line):
            continue
        scan_line = _strip_parentheses(line)
        for name, patterns in DRILL_PATTERNS.items():
            if name in found:
                continue
            for pat in patterns:
                if re.search(pat, scan_line, flags=re.IGNORECASE):
                    found.add(name)
                    break
    return found


def detect_overlaps(workouts: list[dict]) -> list[dict]:
    """Return list of overlap reports."""
    by_drill: dict[str, list[str]] = defaultdict(list)
    for w in workouts:
        name = w.get("name") or "(unbenannt)"
        drills = find_drills(w.get("description") or "")
        for d in drills:
            by_drill[d].append(name)
    overlaps = []
    for drill, names in by_drill.items():
        if len(names) >= 2:
            overlaps.append({"drill": drill, "in_workouts": names})
    return overlaps


async def fetch_workouts(target_date: str) -> list[dict]:
    client = IntervalsClient(settings.intervals_icu_athlete_id)
    events = await client.get_events(target_date, target_date)
    return [
        e
        for e in events
        if e.get("category") == "WORKOUT"
        and (e.get("start_date_local") or "").startswith(target_date)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan today's workouts for duplicated warm-up drills")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--json", action="store_true", help="JSON-Output statt Klartext")
    args = parser.parse_args()

    try:
        workouts = asyncio.run(fetch_workouts(args.date))
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  Fehler beim Laden der Workouts: {exc}", file=sys.stderr)
        return 1

    overlaps = detect_overlaps(workouts)

    if args.json:
        print(json.dumps({"date": args.date, "workout_count": len(workouts), "overlaps": overlaps}, ensure_ascii=False, indent=2))
        return 0

    if not overlaps:
        print(f"✅ {args.date}: keine Drill-Doppelungen in {len(workouts)} Workout(s).")
        return 0

    print(f"⚠️  {args.date}: {len(overlaps)} Drill-Doppelung(en) in {len(workouts)} Workout(s):")
    for o in overlaps:
        names = " ↔ ".join(o["in_workouts"])
        print(f"  • {o['drill']}: {names}")
    print("\n→ Im jeweiligen Workout WU bereinigen oder einen WU-Block weglassen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
