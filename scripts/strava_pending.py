"""List Strava activities that may need a title or insights update.

Replacement for the listing portion of the retired
`sync_strava_titles.py`. Pure read (apart from an optional intervals.icu
title rename when an Indoor-Activity carries an Outdoor-Surface term —
that side-effect normalises the source-of-truth name and is gated by
`--apply-iv-rename`, default off).

Output: JSON list (stdout). One entry per matched Strava/intervals.icu
pair.

SECURITY NOTE: The text fields `raw_name`, `current_name`,
`cleaned_name_proposal`, and `current_desc` contain athlete- or
Strava-controlled input verbatim (no `escape_for_prompt` is applied
here on purpose, so the JSON stays human-readable for display). Any
downstream consumer that inlines these fields into an LLM prompt MUST
apply `app.utils.sanitize.escape_for_prompt` at that boundary — see
`SECURITY.md` (prompt-injection threat model).

Schema per entry:
    {
      "iv_id":                  str,
      "sv_id":                  int,
      "type":                   str,     # intervals.icu activity type
      "start_date":             str,     # ISO UTC
      "raw_name":               str,     # intervals.icu name (verbatim)
      "current_name":           str,     # Strava name right now
      "cleaned_name_proposal":  str,     # hashtag-/surface-cleaned suggestion
      "name_needs_update":      bool,
      "current_desc":           str,
      "has_insights_anchor":    bool,    # Idempotency: skip if true
      "insights_eligible":      bool     # type ∈ {Run, VirtualRun, Ride, VirtualRide}
                                         # AND `STRAVA_PUBLISHER_FOOTER_ENABLED` true
    }

Usage:
    python3 scripts/strava_pending.py --days 2
    python3 scripts/strava_pending.py --days 2 --apply-iv-rename
    python3 scripts/strava_pending.py --activity-id i12345678
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.intervals_client import IntervalsClient
from app.api.strava_client import StravaClient
from app.utils.strava_titles import (
    INSIGHTS_ANCHOR,
    INSIGHTS_ENABLED,
    INSIGHTS_TYPES,
    clean_name,
    detect_surface_mismatch,
    find_strava_match,
    parse_iso,
)
from app.utils.tracing import script_span, set_span_io


def _home_locations() -> list[str]:
    """Optional list of athlete home locations to strip from Strava titles.

    Athlete-specific override via the env var
    `STRAVA_HOME_LOCATIONS="Langen (Hessen),Langen"` — comma-separated.
    Unset → no Heimatort-Strip.
    """
    raw = os.environ.get("STRAVA_HOME_LOCATIONS", "").strip()
    if not raw:
        return []
    return [loc.strip() for loc in raw.split(",") if loc.strip()]


async def _collect(days: int, activity_id: str | None, apply_iv_rename: bool) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    oldest = (today - timedelta(days=days)).isoformat()
    newest = today.isoformat()

    iv_client = IntervalsClient()
    sv_client = StravaClient()

    iv_activities = await iv_client.get_activities(oldest=oldest, newest=newest)
    if activity_id:
        iv_activities = [a for a in iv_activities if a.get("id") == activity_id]

    after_epoch = int(
        datetime.combine(
            today - timedelta(days=days), datetime.min.time(), tzinfo=timezone.utc
        ).timestamp()
    )
    sv_activities = await sv_client.list_activities(after_epoch=after_epoch, per_page=50)

    locations = _home_locations()
    out: list[dict] = []

    for iv in iv_activities:
        iv_id = iv.get("id") or ""
        iv_name_raw = iv.get("name") or ""
        iv_start_str = iv.get("start_date") or iv.get("start_date_local")
        if not iv_start_str:
            continue
        try:
            iv_start = parse_iso(iv_start_str)
        except Exception:
            continue

        cleaned = clean_name(iv_name_raw, locations=locations)
        if not cleaned:
            continue

        # Surface-Mismatch: Indoor-Activity mit Outdoor-Surface-Begriff im Titel.
        fixed_name, mismatch_reason = detect_surface_mismatch(iv, cleaned)
        if fixed_name is not None and fixed_name != cleaned:
            if apply_iv_rename:
                try:
                    await iv_client.update_activity_name(iv_id, fixed_name)
                except Exception as e:
                    print(
                        f"warn: intervals.icu rename {iv_id} failed: {e}",
                        file=sys.stderr,
                    )
            cleaned = fixed_name

        sv = find_strava_match(iv_start, sv_activities)
        if not sv:
            continue

        sv_id = sv["id"]
        try:
            sv_detail = await sv_client.get_activity_detail(sv_id)
        except Exception as e:
            print(f"warn: Strava detail {sv_id} failed: {e}", file=sys.stderr)
            continue

        sv_name = sv_detail.get("name") or ""
        sv_desc = sv_detail.get("description") or ""
        iv_type = iv.get("type") or ""

        out.append(
            {
                "iv_id": iv_id,
                "sv_id": sv_id,
                "type": iv_type,
                "start_date": iv_start_str,
                "raw_name": iv_name_raw,
                "current_name": sv_name,
                "cleaned_name_proposal": cleaned,
                "name_needs_update": sv_name != cleaned,
                "current_desc": sv_desc,
                "has_insights_anchor": INSIGHTS_ANCHOR in sv_desc,
                "insights_eligible": (
                    iv_type in INSIGHTS_TYPES and INSIGHTS_ENABLED
                ),
            }
        )

    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List Strava activities pending title/insights update."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=2,
        help="Tage zurück inklusive heute (default: 2 = heute + gestern)",
    )
    parser.add_argument(
        "--activity-id",
        type=str,
        default=None,
        help="Optional: nur diese intervals.icu Activity-ID prüfen",
    )
    parser.add_argument(
        "--apply-iv-rename",
        action="store_true",
        help="Wenn gesetzt: Surface-Mismatch wird auch in intervals.icu gepatcht "
        "(default: nur lesen).",
    )
    args = parser.parse_args()

    display = f"Strava pending — last {args.days} days"
    with script_span(
        "strava_pending",
        display_name=display,
        days=args.days,
        activity_id=args.activity_id,
    ):
        result = asyncio.run(
            _collect(
                days=args.days,
                activity_id=args.activity_id,
                apply_iv_rename=args.apply_iv_rename,
            )
        )
        set_span_io(
            input={"days": args.days, "activity_id": args.activity_id},
            output=f"{len(result)} pending entries",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
