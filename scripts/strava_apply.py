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
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.strava_client import StravaClient
from app.utils.strava_titles import (
    INSIGHTS_ANCHOR,
    STRAVA_DESCRIPTION_MAX,
)
from app.utils.tracing import script_span, set_span_io


# Patterns that look like elevation citations in German + English insight
# blocks. Anchored on the unit/keyword to avoid catching distance "m" or
# pace tokens like "5:25/km".
_ELEVATION_PATTERNS: list[re.Pattern[str]] = [
    # "260 Höhenmeter", "260 Hm"
    re.compile(r"(\d{2,4})\s*(?:Höhenmeter|Hm\b)", re.IGNORECASE),
    # "260 m Höhe", "260 m positive Höhenmeter", "260 m Ascent",
    # "260 m positiver Anstieg", "260 m elevation gain"
    re.compile(
        r"(\d{2,4})\s*m\s+(?:Höhe|Höhenmeter|Ascent|Anstieg|Aufstieg|positiv|gain|elevation|Climb|D\+)",
        re.IGNORECASE,
    ),
    # "rund 260 m insgesamt" — only when "insgesamt" or "gesamt" is the
    # immediate noun anchor (elevation context implied by adjacent talk)
    re.compile(
        r"(\d{2,4})\s*m\s+(?:insgesamt|gesamt)\b",
        re.IGNORECASE,
    ),
]


def _extract_elevation_citations(desc: str) -> list[int]:
    """Return integer elevation values cited in the description text."""
    found: list[int] = []
    for pat in _ELEVATION_PATTERNS:
        for m in pat.finditer(desc):
            try:
                found.append(int(m.group(1)))
            except ValueError:
                pass
    return found


# Patterns that look like raw heart-rate citations. Strava insights are
# follower-facing — the agent-contract (`agents/strava-publisher.md`
# lesson 2) requires zone language only, not absolute BPM. The
# validator refuses pushes that quote raw HR numbers regardless of
# whether they came from the agent or a re-authored block.
_HR_PATTERNS: list[re.Pattern[str]] = [
    # "132 bpm", "132bpm"
    re.compile(r"\b(\d{2,3})\s*bpm\b", re.IGNORECASE),
    # "HR 132", "max HR 137", "avg HR 132", "Herzfrequenz 132"
    re.compile(
        r"\b(?:max\s*|avg\s*|durchschnittliche?\s*|average\s*)?(?:HR|HF|Herzfrequenz|heart\s*rate)\s*[:=]?\s*(\d{2,3})\b",
        re.IGNORECASE,
    ),
    # "+2 bpm" / "−5 bpm" delta citations
    re.compile(r"[+\-−]\s*(\d{1,3})\s*bpm\b", re.IGNORECASE),
]


def _extract_hr_citations(desc: str) -> list[str]:
    """Return the raw HR substrings cited in the description.

    Returns the matched fragments (for error messaging) rather than just
    integers — the user needs to see what to remove, not just the value.
    """
    found: list[str] = []
    for pat in _HR_PATTERNS:
        for m in pat.finditer(desc):
            found.append(m.group(0).strip())
    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for s in found:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def _validate_raw_hr(desc: str) -> None:
    """Refuse pushes that cite raw HR numbers (Strava-publisher lesson 2).

    Strava is follower-facing; concrete BPM values are too data-y for the
    public stream. Use zone language ("Z2-Decke gehalten",
    "kein Z3-Drift") instead. This is a boundary check — the agent
    contract has carried the rule for a while, but enforcement at write
    time prevents drift through the contract.
    """
    cited = _extract_hr_citations(desc)
    if not cited:
        return
    sample = ", ".join(cited[:5])
    extra = f" (and {len(cited) - 5} more)" if len(cited) > 5 else ""
    print(
        f"error: raw HR citations in description: {sample}{extra}. "
        f"Strava insights must use zone language only "
        f"(`Z2-Decke gehalten`, `kein Z3-Drift`) — not absolute BPM or "
        f"`avg HR 132` style numbers. Re-author with zone framing. "
        f"Override with --skip-hr-check (emergency; document explicitly).",
        file=sys.stderr,
    )
    sys.exit(2)


async def _validate_elevation(activity_id: int, desc: str) -> None:
    """Refuse the push when a cited elevation drifts from Strava's actual.

    Strava is the public-facing source of truth (see
    agents/strava-publisher.md lesson 4). Quoting FIT-derived or
    intervals.icu-derived elevation values that diverge from what
    followers see on the activity is the recurring drift class this
    boundary check prevents.

    Threshold: drift must exceed BOTH 30 m absolute AND 20% relative
    before the push is refused. This catches gross fabrications
    (260 m vs 117 m actual) while tolerating smoothing/rounding
    differences on relatively flat runs.
    """
    cited = _extract_elevation_citations(desc)
    if not cited:
        return
    client = StravaClient()
    try:
        detail = await client.get_activity_detail(activity_id)
    except Exception as exc:
        print(
            f"warning: could not fetch Strava elevation for validation ({exc}); "
            f"skipping elevation check",
            file=sys.stderr,
        )
        return
    actual = detail.get("total_elevation_gain")
    if actual is None or actual <= 0:
        return
    threshold_abs = 30.0
    threshold_pct = 0.20
    for value in cited:
        drift_abs = abs(value - actual)
        drift_pct = drift_abs / actual
        if drift_abs > threshold_abs and drift_pct > threshold_pct:
            print(
                f"error: elevation citation {value} m drifts "
                f"{drift_abs:.0f} m ({drift_pct * 100:.0f}%) from Strava "
                f"actual {actual:.0f} m. Use Strava's value or omit the "
                f"elevation citation. Override with --skip-elevation-check "
                f"(emergency; document explicitly).",
                file=sys.stderr,
            )
            sys.exit(2)


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
    parser.add_argument(
        "--skip-elevation-check",
        action="store_true",
        help=(
            "Bypass the elevation-citation drift check against Strava's "
            "total_elevation_gain. Emergency override only — the agent "
            "should normally use Strava's value or omit the citation."
        ),
    )
    parser.add_argument(
        "--skip-hr-check",
        action="store_true",
        help=(
            "Bypass the raw-HR-citation check. Emergency override only — "
            "Strava insights must normally use zone language only."
        ),
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
        if not args.skip_hr_check:
            _validate_raw_hr(description)
        if not args.skip_elevation_check:
            asyncio.run(_validate_elevation(args.activity_id, description))

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
