"""Garmin Connect client for downloading FIT files.

Uses garminconnect 0.3.2 with token caching — replaces the deprecated garth/gcexport approach.
Tokens are persisted in cache/garmin-session/ and reused on subsequent calls (no SSO hit).
"""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

from garminconnect import Garmin

from app.config import settings

DEFAULT_OUTPUT_DIR = Path("/tmp/garmin")
GARMIN_SESSION_DIR = Path(__file__).parents[2] / "cache" / "garmin-session"


def _get_client() -> Garmin:
    """Return an authenticated Garmin client, using cached tokens when available."""
    GARMIN_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    client = Garmin(email=settings.garmin_email, password=settings.garmin_password)
    client.login(str(GARMIN_SESSION_DIR))
    return client


def _pick_activity(activities: list[dict], start_time_local: str | None) -> dict:
    """The Garmin activity matching ``start_time_local`` (±15 min), else the newest.

    With several sessions on one day, "the most recent" is the wrong file for
    every session but the last one. When a start time is given and nothing
    lies within 15 minutes, raise instead of analysing another session.
    """
    if not start_time_local:
        return activities[0]
    from datetime import datetime

    try:
        target = datetime.fromisoformat(start_time_local[:19])
    except ValueError:
        return activities[0]
    best, best_gap = None, None
    for act in activities:
        raw = str(act.get("startTimeLocal") or "").replace(" ", "T")[:19]
        try:
            gap = abs((datetime.fromisoformat(raw) - target).total_seconds())
        except ValueError:
            continue
        if best_gap is None or gap < best_gap:
            best, best_gap = act, gap
    if best is None or best_gap is None or best_gap > 15 * 60:
        raise FileNotFoundError(
            f"No Garmin activity within 15 min of {start_time_local}"
        )
    return best


def download_fit_for_date(
    date: str,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    start_time_local: str | None = None,
) -> Path:
    """Download FIT file for a specific date from Garmin Connect.

    Args:
        date: Date in YYYY-MM-DD format.
        output_dir: Directory to store downloaded files.
        start_time_local: intervals.icu ``start_date_local`` of the session;
            selects the matching Garmin activity on multi-session days.

    Returns:
        Path to the downloaded FIT file.

    Raises:
        FileNotFoundError: If no activity or FIT file found.
        RuntimeError: If download fails.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    client = _get_client()

    activities = client.get_activities_by_date(startdate=date, enddate=date)
    if not activities:
        raise FileNotFoundError(f"No activities found on Garmin for date {date}")

    # Match by start time when known; otherwise the most recent of the day.
    activity = _pick_activity(activities, start_time_local)
    activity_id = str(activity["activityId"])

    zip_bytes = client.download_activity(activity_id, Garmin.ActivityDownloadFormat.ORIGINAL)

    # Extract .fit from zip
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        fit_names = [n for n in zf.namelist() if n.lower().endswith(".fit")]
        if not fit_names:
            raise FileNotFoundError(f"No .fit file in downloaded zip for activity {activity_id}")
        fit_name = fit_names[0]
        fit_path = output_dir / Path(fit_name).name
        fit_path.write_bytes(zf.read(fit_name))

    return fit_path
