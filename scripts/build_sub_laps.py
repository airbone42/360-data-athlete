"""Build windowed sub-laps from streams + FIT records + surface detection.

Input: JSON via stdin with keys: streams, fit_records, laps
Output: JSON array of sub-lap windows to stdout

Usage:
    echo '{"streams": {...}, "fit_records": [...], "laps": [...]}' | \\
        python3 coach/scripts/build_sub_laps.py

    python3 coach/scripts/build_sub_laps.py --file /tmp/data.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.windowing import build_sub_laps
from app.utils.overpass_client import map_points_to_surfaces, query_surface_bbox


async def _enrich_surface(fit_records: list[dict], streams: dict, stream_len: int) -> list[str]:
    """Query Overpass for surface data and map to stream positions."""
    gps_points = [
        [r["lat"], r["lon"]]
        for r in fit_records
        if r.get("lat") is not None and r.get("lon") is not None
    ]
    if not gps_points:
        return []

    lats = [p[0] for p in gps_points]
    lons = [p[1] for p in gps_points]
    try:
        ways = await query_surface_bbox(min(lats), min(lons), max(lats), max(lons))
    except Exception:
        return []

    fit_surface_labels = map_points_to_surfaces(gps_points, ways)

    if len(fit_surface_labels) == stream_len:
        return fit_surface_labels

    # Resample to stream_len
    ratio = len(fit_surface_labels) / max(stream_len, 1)
    return [
        fit_surface_labels[min(int(i * ratio), len(fit_surface_labels) - 1)]
        for i in range(stream_len)
    ]


async def _run(data: dict) -> list[dict]:
    streams = data.get("streams", {})
    fit_records = data.get("fit_records") or data.get("records", [])
    laps = data.get("laps", [])

    stream_len = len(streams.get("time", fit_records))
    surface_labels = await _enrich_surface(fit_records, streams, stream_len)

    sub_laps = build_sub_laps(
        streams=streams,
        surface_labels=surface_labels,
        fit_records=fit_records,
        laps=laps,
    )
    return sub_laps


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Build sub-lap windows with surface enrichment")
    parser.add_argument("--file", help="Path to JSON input file (default: stdin)")
    args = parser.parse_args()

    if args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                data = json.load(f)
        except UnicodeDecodeError as e:
            sys.stderr.write(
                f"build_sub_laps.py: --file expects a JSON file (streams + fit_records "
                f"+ laps), not a binary FIT or other binary input. Decode failed: {e}. "
                f"For a FIT file, run parse_fit.py first to extract records/laps as JSON, "
                f"then wrap with {{streams, fit_records, laps}} and pipe to build_sub_laps.\n"
            )
            sys.exit(2)
        except json.JSONDecodeError as e:
            sys.stderr.write(
                f"build_sub_laps.py: --file '{args.file}' is not valid JSON: {e}\n"
            )
            sys.exit(2)
    else:
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            sys.stderr.write(
                f"build_sub_laps.py: stdin is not valid JSON: {e}\n"
            )
            sys.exit(2)

    sub_laps = asyncio.run(_run(data))
    print(json.dumps(sub_laps, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
