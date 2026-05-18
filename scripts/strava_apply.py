"""Push title and/or description to a Strava activity.

Single write path replacing the writing portion of the retired
`sync_strava_titles.py`. Caller (the strava-publisher agent) is
responsible for composing the final description text — including any
preservation of athlete-written prose and stripping the trailing legacy
footer marker before appending the new insights block. This script is
intentionally dumb:

  - Validates Strava-Description-Limit (`STRAVA_DESCRIPTION_MAX`).
  - Refuses an update that would inject a second
    `INSIGHTS_ANCHOR` line (idempotency safety net).
  - In `--dry-run` mode, only prints the intended diff to stdout.
  - Otherwise calls `StravaClient.update_activity()`.

Usage:
    python3 scripts/strava_apply.py --activity-id 123 --title "..."
    python3 scripts/strava_apply.py --activity-id 123 \\
        --description "$(cat block.txt)"
    cat block.txt | python3 scripts/strava_apply.py \\
        --activity-id 123 --description-stdin
    python3 scripts/strava_apply.py --activity-id 123 --title "..." \\
        --description-stdin --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.strava_client import StravaClient
from app.utils.strava_titles import (
    INSIGHTS_ANCHOR,
    STRAVA_DESCRIPTION_MAX,
)
from app.utils.tracing import script_span, set_span_io


def _read_description(args: argparse.Namespace) -> str | None:
    if args.description is not None and args.description_stdin:
        print(
            "error: --description und --description-stdin schließen sich aus",
            file=sys.stderr,
        )
        sys.exit(2)
    if args.description is not None:
        return args.description
    if args.description_stdin:
        return sys.stdin.read()
    return None


def _validate_description(desc: str) -> None:
    if len(desc) > STRAVA_DESCRIPTION_MAX:
        print(
            f"error: description too long ({len(desc)} > {STRAVA_DESCRIPTION_MAX} chars)",
            file=sys.stderr,
        )
        sys.exit(2)
    if desc.count(INSIGHTS_ANCHOR) > 1:
        print(
            f"error: description contains '{INSIGHTS_ANCHOR}' more than once — "
            "would duplicate the insights block",
            file=sys.stderr,
        )
        sys.exit(2)


async def _apply(
    activity_id: int,
    title: str | None,
    description: str | None,
    dry_run: bool,
) -> dict:
    client = StravaClient()
    if dry_run:
        return {
            "dry_run": True,
            "activity_id": activity_id,
            "title": title,
            "description": description,
            "description_chars": len(description) if description is not None else None,
        }
    result = await client.update_activity(
        activity_id=activity_id,
        name=title,
        description=description,
    )
    return {
        "dry_run": False,
        "activity_id": activity_id,
        "title_pushed": title,
        "description_chars": len(description) if description is not None else None,
        "strava_status": "OK",
        "strava_returned_name": result.get("name"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Push title/description to Strava.")
    parser.add_argument("--activity-id", type=int, required=True, help="Strava-Activity-ID (integer)")
    parser.add_argument("--title", type=str, default=None, help="Neuer Activity-Titel")
    parser.add_argument(
        "--description",
        type=str,
        default=None,
        help="Neue Description (komplett, kein Append)",
    )
    parser.add_argument(
        "--description-stdin",
        action="store_true",
        help="Description aus stdin lesen",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur Vorschau, kein Push",
    )
    args = parser.parse_args()

    description = _read_description(args)

    if args.title is None and description is None:
        print(
            "error: weder --title noch --description angegeben — nichts zu tun",
            file=sys.stderr,
        )
        sys.exit(2)

    if description is not None:
        _validate_description(description)

    display = f"Strava apply — {args.activity_id}"
    with script_span(
        "strava_apply",
        display_name=display,
        activity_id=args.activity_id,
        dry_run=args.dry_run,
        title_update=args.title is not None,
        desc_update=description is not None,
    ):
        result = asyncio.run(
            _apply(
                activity_id=args.activity_id,
                title=args.title,
                description=description,
                dry_run=args.dry_run,
            )
        )
        set_span_io(
            input={
                "activity_id": args.activity_id,
                "title": args.title,
                "desc_chars": result.get("description_chars"),
                "dry_run": args.dry_run,
            },
            output=("dry-run" if args.dry_run else "pushed"),
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
