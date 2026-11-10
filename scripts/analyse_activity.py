"""Compact activity analysis for /analyse — one call, no raw streams.

Chains what /analyse used to do by hand (fetch_activity → download_fit →
parse_fit → build_sub_laps) inside the process and prints only the summary:
HR avg/max per lap and sub-lap, time in HR zones by the zones of the
activity's own sport, power, pace, cadence, running dynamics (FIT) and
aerobic decoupling.

Data path:
  * Garmin-sourced activities: FIT from Garmin Connect (matched by start
    time) for laps and running dynamics, intervals.icu streams for the time
    axis.
  * Everything else (indoor ride via Wahoo/Zwift, Strava, uploads) or when the
    FIT download fails: intervals.icu streams + laps (``icu_intervals``).
    The fallback is named in ``notes`` — no error.

Usage:
    python3 scripts/analyse_activity.py --activity-id i12345678
    python3 scripts/analyse_activity.py --activity-id i12345678 --no-fit
    python3 scripts/analyse_activity.py --activity-id i12345678 --fit-path /path/a.fit
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.analytics.activity_analysis import summarize_activity  # noqa: E402
from app.utils.activity_helpers import activity_date  # noqa: E402
from app.utils.alerts import alert_on_failure  # noqa: E402
from app.utils.sanitize import escape_for_prompt  # noqa: E402

# Activity sources whose original file lives in Garmin Connect.
FIT_SOURCES = {"GARMIN_CONNECT"}
_WELLNESS_KEYS = ("hrv", "restingHR", "sleepScore", "sleepSecs", "readiness", "weight")


def _wants_fit(activity: dict, no_fit: bool) -> tuple[bool, str | None]:
    if no_fit:
        return False, "FIT skipped (--no-fit) — intervals.icu streams used"
    source = activity.get("source") or "?"
    if source not in FIT_SOURCES:
        return False, f"no Garmin FIT for source {source} — intervals.icu streams used"
    return True, None


def _load_fit(activity: dict, fit_path: str | None) -> tuple[list, list, str | None]:
    """(fit_laps, fit_records, note). Never raises — a failed FIT is a fallback."""
    from app.utils.fit_parser import parse_fit_laps, parse_fit_records

    try:
        if fit_path:
            path = Path(fit_path)
        else:
            from app.utils.garmin_client import download_fit_for_date

            path = download_fit_for_date(
                activity_date(activity),
                start_time_local=activity.get("start_date_local"),
            )
        return parse_fit_laps(path), parse_fit_records(path), None
    except Exception as exc:  # noqa: BLE001
        return [], [], f"FIT unavailable ({type(exc).__name__}: {str(exc)[:120]}) — intervals.icu streams used"


async def _surface(fit_records: list[dict], streams: dict) -> list[str]:
    try:
        from scripts.build_sub_laps import _enrich_surface

        return await _enrich_surface(fit_records, streams, len(streams.get("time") or []))
    except Exception:  # noqa: BLE001
        return []


async def _gather(activity_id: str, args: argparse.Namespace) -> dict:
    from app.api.intervals_cache import CachedIntervalsClient
    from app.config import settings

    client = CachedIntervalsClient(settings.intervals_icu_athlete_id)
    activity, intervals, streams, athlete_settings = await asyncio.gather(
        client.get_activity(activity_id),
        client.get_activity_intervals(activity_id),
        client.get_streams(activity_id),
        client.get_athlete_settings(),
    )

    want_fit, note = _wants_fit(activity, args.no_fit)
    if args.fit_path:
        want_fit, note = True, None
    fit_laps: list = []
    fit_records: list = []
    if want_fit and streams.get("time"):
        fit_laps, fit_records, note = _load_fit(activity, args.fit_path)
    surface: list[str] = []
    if fit_records and not args.no_surface:
        surface = await _surface(fit_records, streams)

    summary = summarize_activity(
        activity, streams, intervals, athlete_settings,
        fit_laps=fit_laps or None, fit_records=fit_records or None,
        surface_labels=surface or None, data_note=note,
    )

    # Context the analysis needs besides the numbers — trimmed and sanitised
    # (athlete- and third-party-writable text).
    desc = activity.get("description")
    if desc:
        summary["activity"]["description"] = escape_for_prompt(desc, max_len=2000)
    paired = activity.get("paired_event_id")
    if paired:
        try:
            ev = await client.get_event(str(paired))
            summary["planned_workout"] = {
                "name": escape_for_prompt(ev.get("name") or "", max_len=200),
                "description": escape_for_prompt(ev.get("description") or "", max_len=2000),
            }
        except Exception:  # noqa: BLE001
            pass
    day = activity_date(activity)
    if day:
        try:
            w = await client.get_wellness(day)
            summary["wellness"] = {k: w.get(k) for k in _WELLNESS_KEYS if w.get(k) is not None}
        except Exception:  # noqa: BLE001
            pass
    return summary


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Compact activity analysis (no raw streams)")
    parser.add_argument("--activity-id", required=True, help="Activity ID e.g. i12345678")
    parser.add_argument("--no-fit", action="store_true", help="Skip the Garmin FIT download")
    parser.add_argument("--fit-path", help="Use this local FIT file instead of downloading")
    parser.add_argument("--no-surface", action="store_true", help="Skip the Overpass surface lookup")
    args = parser.parse_args()

    from app.utils.tracing import script_span

    with script_span(
        "analyse_activity",
        display_name=f"Analyse activity — {args.activity_id}",
        activity_id=args.activity_id,
    ):
        summary = asyncio.run(_gather(args.activity_id, args))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
