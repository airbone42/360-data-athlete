"""Typisierter Helper zum Speichern von Athleten-Feedback als NOTE in intervals.icu.

Ersetzt raw `post_message.py --note` mit explizitem Logging + Kategorie-Mapping.

Usage:
    python3 scripts/save_feedback.py --date 2026-04-20 --note "Achilles ok" --category hrv_review
    python3 scripts/save_feedback.py --date 2026-04-20 --note "Mental gut" --category mental
    python3 scripts/save_feedback.py --note "RPE 8, Beine schwer"  # default: athlete_feedback
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.intervals_client import IntervalsClient
from app.config import settings
from app.utils.alerts import alert_on_failure
from app.utils.logging import configure

logger = configure(__name__)

_CATEGORY_NAMES: dict[str, str] = {
    "athlete_feedback": "Athleten-Feedback",
    "hrv_review": "HRV-Review",
    "mental": "Mental-Coach",
    "dfa": "DFA-Analyse",
    "video": "Video-Formcheck",
}

VALID_CATEGORIES = list(_CATEGORY_NAMES.keys())


async def _save(date_str: str, note: str, category: str, dry_run: bool) -> None:
    name = _CATEGORY_NAMES.get(category, "Athleten-Feedback")
    event = {
        "category": "NOTE",
        "start_date_local": f"{date_str}T08:00:00",
        "name": name,
        "description": note,
    }
    if dry_run:
        logger.info("[DRY-RUN] Would save NOTE: %s | %s | %s", date_str, name, note[:80])
        print(json.dumps([event], ensure_ascii=False, indent=2))
        return
    client = IntervalsClient(settings.intervals_icu_athlete_id)
    result = await client.post_events_bulk([event])
    logger.info("NOTE saved: %s | %s | %s", category, date_str, note[:80])
    print(json.dumps(result, ensure_ascii=False, indent=2))


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Athleten-Feedback als NOTE in intervals.icu speichern")
    parser.add_argument("--date", default=date.today().isoformat(), help="Datum YYYY-MM-DD")
    parser.add_argument("--note", required=True, help="Feedback-Text")
    parser.add_argument(
        "--category",
        default="athlete_feedback",
        choices=VALID_CATEGORIES,
        help=f"Kategorie: {', '.join(VALID_CATEGORIES)}",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(_save(args.date, args.note, args.category, args.dry_run))


if __name__ == "__main__":
    main()
