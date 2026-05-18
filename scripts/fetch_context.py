"""Fetch complete athlete context from intervals.icu and build coaching context dict.

Wraps: app.graphs.sub_athlete_context.context_builder.build_context()

Output: JSON to stdout (same schema as context_summary dict).

Usage:
    python3 coach/scripts/fetch_context.py [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date, timedelta

import httpx

# Ensure project root is on path when run from any directory
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.intervals_cache import CachedIntervalsClient as IntervalsClient
from app.api.strava_client import StravaClient, bust_shoes_cache
from app.config import settings
from app.graphs.sub_athlete_context.context_builder import build_context
from app.utils.logging import configure
from app.utils.tracing import configure_tracing

configure("fetch_context", level="WARNING")
configure_tracing()


def _athlete_status_path() -> str:
    """Resolve config/athlete_status.md — prefer COACH_HOME, fallback to framework."""
    from app.utils.paths import COACH_HOME, FRAMEWORK_ROOT
    primary = COACH_HOME / "config" / "athlete_status.md"
    if primary.exists():
        return str(primary)
    return str(FRAMEWORK_ROOT / "config.example" / "athlete_status.md")


def _parse_deload_state() -> dict:
    """Parse Erholungswoche-Status from config/athlete_status.md."""
    try:
        with open(_athlete_status_path(), encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return {}

    import re
    section_match = re.search(
        r"## Erholungswoche-Status\n(.*?)(?=\n##|\Z)", content, re.DOTALL
    )
    if not section_match:
        return {}

    section = section_match.group(1)
    result: dict = {}
    for key in ("aktiv", "start", "ende_geplant", "begründung"):
        m = re.search(rf"\*\*{re.escape(key)}:\*\*\s*(.+)", section)
        if m:
            result[key] = m.group(1).strip()
    return result


def _parse_deload_ctl_threshold() -> float | None:
    """Parse `deload_ctl_threshold` override from athlete_status.md.

    Returns None when the athlete uses the framework default (24).
    Looked up as `**deload_ctl_threshold:** <float>` anywhere in the file.
    """
    try:
        with open(_athlete_status_path(), encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return None
    import re
    m = re.search(r"\*\*deload_ctl_threshold:\*\*\s*([0-9.]+)", content)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


async def _fetch_all(athlete_id: str, date_str: str) -> dict:
    today = date.fromisoformat(date_str)
    client = IntervalsClient(athlete_id)

    oldest_4w = (today - timedelta(weeks=4)).isoformat()
    oldest_7d = (today - timedelta(days=7)).isoformat()
    oldest_90d = (today - timedelta(days=90)).isoformat()
    oldest_notes = oldest_4w  # match activity range for HRV-Review detection
    newest_6w = (today + timedelta(days=42)).isoformat()

    # Fetch wellness, activities, workouts (past events), upcoming events, history, settings, notes
    # + Strava shoes (optional, degrades gracefully if not configured) — all in parallel
    strava_client = StravaClient()

    async def _fetch_shoes() -> list[dict]:
        if not settings.strava_client_id or not settings.strava_refresh_token:
            return []
        try:
            return await strava_client.list_shoes()
        except Exception as e:
            logging.getLogger(__name__).warning("strava shoes fetch failed: %s", e)
            return []

    wellness, activities, workouts, events, wellness_history, athlete_settings, notes, strava_shoes = (
        await asyncio.gather(
            client.get_wellness(date_str),
            client.get_activities(oldest_4w, date_str),
            client.get_events(oldest_4w, date_str),
            client.get_events(date_str, newest_6w),
            client.get_wellness_history(oldest_90d, date_str),
            client.get_athlete_settings(),
            client.get_notes(oldest_notes, date_str),
            _fetch_shoes(),
        )
    )

    # Weather with retry (3 attempts)
    weather: dict = {}
    weather_warning = False
    for attempt in range(3):
        try:
            weather = await client.get_weather_forecast()
            break
        except (httpx.ReadTimeout, httpx.ConnectTimeout):
            if attempt == 2:
                weather_warning = True

    deload_state = _parse_deload_state()
    deload_ctl_threshold = _parse_deload_ctl_threshold()

    state: dict = {
        "athlete_id": athlete_id,
        "date": date_str,
        "wellness": wellness,
        "rhr_retry_count": 0,
        "activities": activities,
        "workouts": workouts,
        "events": events,
        "wellness_history": wellness_history,
        "weather": weather,
        "weather_warning": weather_warning,
        "athlete_settings": athlete_settings,
        "notes": notes,
        "strava_shoes": strava_shoes,
        "context_summary": {},
        "deload_state": deload_state,
        "deload_ctl_threshold": deload_ctl_threshold,
    }

    if not wellness.get("restingHR"):
        state.setdefault("dataWarnings", [])
        state["dataWarnings"] = ["RHR nicht verfügbar – Garmin noch nicht synchronisiert"]

    context = build_context(state)
    if weather_warning:
        context.setdefault("dataWarnings", [])
        context["dataWarnings"].append("Wetterdaten nicht verfügbar")

    # Soft drift-check: surface stale entries in exercise_progressions.md so the
    # planner / specialists see them at session start, not only when /audit is
    # run explicitly. Failure-tolerant — never blocks context.
    try:
        from scripts.audit_consistency import check_log_vs_history
        from app.utils.sanitize import escape_for_prompt
        # Only run against the last 30 days of activities — check_log_vs_history
        # iterates per entry × per activity, full 90d would dominate cold-cache
        # context loading time.
        recent_acts = activities[-50:] if activities else []
        drift_findings = check_log_vs_history(recent_acts)
        if drift_findings:
            # `evidence` carries activity-description excerpts (Strava-roundtrip-
            # reachable, so athlete-/third-party-controlled) → sanitize at this
            # write boundary before the dict lands in the planner prompt.
            context["configDrift"] = [
                {
                    "source_file": f.get("source_file"),
                    "source_line": f.get("source_line"),
                    "evidence": escape_for_prompt(
                        (f.get("evidence") or "").split("\n")[0],
                        max_len=200,
                    ),
                }
                for f in drift_findings
            ]
    except Exception:  # noqa: BLE001
        # Drift-Check ist Komfort-Surface, kein Blocker. Schlucken.
        pass

    return context


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    from app.utils.tracing import script_span, set_span_io

    parser = argparse.ArgumentParser(description="Fetch athlete context JSON")
    parser.add_argument("--date", default=date.today().isoformat(), help="Date YYYY-MM-DD")
    parser.add_argument("--fresh-shoes", action="store_true", help="Bust Strava shoe cache before fetching")
    args = parser.parse_args()
    if args.fresh_shoes:
        bust_shoes_cache()

    athlete_id = settings.intervals_icu_athlete_id
    display = f"Load coach context — {args.date}"
    with script_span(
        "fetch_context",
        display_name=display,
        date=args.date,
        fresh_shoes=args.fresh_shoes,
    ):
        context = asyncio.run(_fetch_all(athlete_id, args.date))
        n_acts = len(context.get("activities", []))
        hrv = context.get("hrv") or "?"
        rhr = context.get("rhr") or "?"
        tsb = context.get("tsb") or "?"
        ctl = context.get("ctlDisplay") or context.get("ctl") or "?"
        set_span_io(
            input={"date": args.date, "fresh_shoes": args.fresh_shoes},
            output=f"HRV={hrv} · RHR={rhr} · CTL={ctl} · TSB={tsb} · {n_acts} activities (4w)",
        )
    print(json.dumps(context, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
