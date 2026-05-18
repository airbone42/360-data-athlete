#!/usr/bin/env python3
"""Running Dynamics aus Garmin-Streams für Video-Zeitfenster extrahieren.

Matcht Video-Aufnahme-Timestamp gegen Garmin-Activity-Streams und liefert
Context-Strings oder intelligente Sections für analyse_video.py.

Usage:
    # Automatisch via Video-Metadaten (creation_time aus MP4)
    python3 scripts/extract_run_dynamics.py --video /tmp/run.mp4 --activity-id i12345678

    # Intelligente Sections (von Endurance-Spezialist/Video-Analyst definiert)
    python3 scripts/extract_run_dynamics.py --activity-id i12345678 --video /tmp/run.mp4 \
        --find-sections "frisch,bergauf,müde" --section-duration 25

    # Nur Activity-Übersicht
    python3 scripts/extract_run_dynamics.py --activity-id i12345678 --summary
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, variance

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.api.intervals_cache import CachedIntervalsClient as IntervalsClient
from app.config import settings
from app.utils.tracing import script_span


# ─── Video-Metadata-Timestamp ────────────────────────────────────────────────

def get_video_creation_time(video_path: str) -> datetime | None:
    """Liest creation_time aus MP4-Metadaten."""
    try:
        import imageio
        reader = imageio.get_reader(video_path, plugin="pyav")
        meta = reader.get_meta_data()
        reader.close()
        ct = str(meta.get("creation_time") or meta.get("date") or "").strip()
        if ct:
            for fmt in (
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ):
                try:
                    dt = datetime.strptime(ct, fmt)
                    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
                except ValueError:
                    continue
    except Exception as e:
        print(f"  Metadata-Lesefehler: {e}", file=sys.stderr)

    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe().replace("ffmpeg", "ffprobe")
        result = subprocess.run(
            [ffmpeg, "-v", "quiet", "-print_format", "json", "-show_format", video_path],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            tags = json.loads(result.stdout).get("format", {}).get("tags", {})
            ct = tags.get("creation_time", "")
            if ct:
                dt = datetime.strptime(ct.split(".")[0].rstrip("Z"), "%Y-%m-%dT%H:%M:%S")
                return dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    return None


# ─── Stream-Hilfsfunktionen ──────────────────────────────────────────────────

FIELD_LABELS = {
    "cadence": ("Kadenz", "spm"),
    "ground_time": ("GCT", "ms"),
    "vertical_oscillation": ("VOS", "cm"),
    "stride_length": ("Stride", "m"),
    "power": ("Power", "W"),
    "heart_rate": ("HR", "bpm"),
    "pace": ("Pace", "/km"),
}


def pace_to_str(mps: float) -> str:
    if mps <= 0:
        return "—"
    spm = 1000 / mps
    return f"{int(spm // 60)}:{int(spm % 60):02d}"


def summarize_window(streams: dict, start_idx: int, end_idx: int) -> str:
    parts = []
    for field, (label, unit) in FIELD_LABELS.items():
        vals = [v for v in (streams.get(field) or [])[start_idx:end_idx]
                if v is not None and v > 0]
        if not vals:
            continue
        avg = mean(vals)
        if field == "pace":
            parts.append(f"Pace ⌀{pace_to_str(avg)}/km")
        elif field == "stride_length":
            actual = avg / 100 if avg > 10 else avg
            parts.append(f"Stride ⌀{actual:.2f}m")
        elif field == "vertical_oscillation":
            actual = avg / 10 if avg > 50 else avg
            parts.append(f"VOS ⌀{actual:.1f}cm")
        else:
            parts.append(f"{label} ⌀{avg:.0f}{unit}")
    return " | ".join(parts) if parts else "keine Dynamics verfügbar"


def find_stream_window(streams: dict, offset_sec: float, duration_sec: float) -> tuple[int, int]:
    time_stream = streams.get("time") or []
    if not time_stream:
        total = len(next(iter(streams.values()), []))
        return 0, total
    start_idx, end_idx = 0, len(time_stream)
    for i, t in enumerate(time_stream):
        if t is not None and t >= offset_sec:
            start_idx = i
            break
    for i, t in enumerate(time_stream):
        if t is not None and t >= offset_sec + duration_sec:
            end_idx = i
            break
    return start_idx, end_idx


def _valid_vals(stream: list, start: int, end: int) -> list[float]:
    return [v for v in (stream or [])[start:end] if v is not None and v > 0]


# ─── Intelligente Section-Finder ─────────────────────────────────────────────

SECTION_TYPES = {
    "frisch": "Erster stabiler Abschnitt (erste 30% der Einheit, niedrige Varianz)",
    "müde": "Letzter stabiler Abschnitt (letzte 25% der Einheit, niedrige Varianz)",
    "bergauf": "Steilste Bergauf-Passage (grade > 4%)",
    "bergab": "Steilste Bergab-Passage (grade < -4%)",
    "stabil": "Stabilster Abschnitt der gesamten Einheit (niedrigste Varianz Kadenz+Pace)",
    "tempo": "Schnellster stabiler Abschnitt",
    "easy": "Langsamster/lockerster Abschnitt",
}


def _window_variance_score(cadence: list, pace: list, start: int, end: int) -> float:
    """Niedrig = stabil. Kombiniert normalisierte Varianz von Kadenz und Pace."""
    c = _valid_vals(cadence, start, end)
    p = _valid_vals(pace, start, end)
    score = 0.0
    if len(c) >= 3:
        avg_c = mean(c)
        score += (variance(c) / (avg_c ** 2)) if avg_c > 0 else 1.0
    else:
        score += 1.0
    if len(p) >= 3:
        avg_p = mean(p)
        score += (variance(p) / (avg_p ** 2)) if avg_p > 0 else 1.0
    else:
        score += 1.0
    return score


def find_sections(
    streams: dict,
    section_types: list[str],
    duration_sec: int,
    video_offset_sec: float,
    act_total_sec: int,
) -> list[dict]:
    """Findet die besten Video-Fenster für die angeforderten Section-Typen.

    Gibt eine Liste von Dicts zurück:
    {label, type, video_start_sec, video_end_sec, garmin_offset_sec, context}
    """
    time_stream = streams.get("time") or []
    cadence = streams.get("cadence") or []
    pace = streams.get("pace") or []
    grade = streams.get("grade") or []
    total = len(time_stream)

    if total == 0:
        return []

    step = 1  # 1 Hz Garmin-Streams
    win = duration_sec  # Fenstergröße in Stream-Indizes (≈ Sekunden)

    # Hilfsfunktion: Garmin-Index → Video-Sekunde
    def garmin_idx_to_video_sec(idx: int) -> float:
        garmin_sec = time_stream[min(idx, total - 1)] if time_stream else idx
        return float(garmin_sec) - video_offset_sec

    results = []

    for stype in section_types:
        stype = stype.strip().lower()

        best_start: int | None = None
        best_score: float = float("inf")
        label_suffix = ""

        if stype == "frisch":
            search_end = int(total * 0.30)
            for i in range(0, max(1, search_end - win), step):
                score = _window_variance_score(cadence, pace, i, i + win)
                if score < best_score:
                    best_score = score
                    best_start = i
            label_suffix = "Frisch"

        elif stype == "müde":
            search_start = int(total * 0.75)
            for i in range(search_start, max(search_start + 1, total - win), step):
                score = _window_variance_score(cadence, pace, i, i + win)
                if score < best_score:
                    best_score = score
                    best_start = i
            label_suffix = "Müde"

        elif stype == "stabil":
            for i in range(0, max(1, total - win), step):
                score = _window_variance_score(cadence, pace, i, i + win)
                if score < best_score:
                    best_score = score
                    best_start = i
            label_suffix = "Stabiler Abschnitt"

        elif stype == "bergauf":
            for i in range(0, max(1, total - win), step):
                g = _valid_vals(grade, i, i + win)
                avg_g = mean(g) if g else 0.0
                if avg_g > 4.0:
                    score = -avg_g  # höher = besser
                    if score < best_score:
                        best_score = score
                        best_start = i
                        label_suffix = f"Bergauf ({avg_g:.0f}%)"
            if best_start is None:
                # Fallback: beste verfügbare Steigung
                for i in range(0, max(1, total - win), step):
                    g = _valid_vals(grade, i, i + win)
                    avg_g = mean(g) if g else 0.0
                    if -avg_g < best_score:
                        best_score = -avg_g
                        best_start = i
                        label_suffix = f"Bergauf ({avg_g:.1f}%)"

        elif stype == "bergab":
            for i in range(0, max(1, total - win), step):
                g = _valid_vals(grade, i, i + win)
                avg_g = mean(g) if g else 0.0
                if avg_g < -4.0:
                    score = avg_g  # niedriger = steiler bergab
                    if score < best_score:
                        best_score = score
                        best_start = i
                        label_suffix = f"Bergab ({avg_g:.0f}%)"
            if best_start is None:
                for i in range(0, max(1, total - win), step):
                    g = _valid_vals(grade, i, i + win)
                    avg_g = mean(g) if g else 0.0
                    if avg_g < best_score:
                        best_score = avg_g
                        best_start = i
                        label_suffix = f"Bergab ({avg_g:.1f}%)"

        elif stype == "tempo":
            for i in range(0, max(1, total - win), step):
                p = _valid_vals(pace, i, i + win)
                avg_p = mean(p) if p else 0.0
                # höhere m/s = schneller = besser
                score = -avg_p
                if score < best_score:
                    score_var = _window_variance_score(cadence, pace, i, i + win)
                    if score_var < 0.5:  # nur stabile schnelle Abschnitte
                        best_score = score
                        best_start = i
                        label_suffix = f"Tempo ({pace_to_str(avg_p)}/km)"

        elif stype == "easy":
            for i in range(0, max(1, total - win), step):
                p = _valid_vals(pace, i, i + win)
                avg_p = mean(p) if p else 0.0
                score = avg_p  # niedrigere m/s = langsamer
                if score < best_score and avg_p > 0:
                    best_score = score
                    best_start = i
                    label_suffix = f"Easy ({pace_to_str(avg_p)}/km)"

        if best_start is None:
            best_start = 0

        video_start = garmin_idx_to_video_sec(best_start)
        video_end = garmin_idx_to_video_sec(best_start + win)

        # Kontext-String für diesen Abschnitt
        ctx = summarize_window(streams, best_start, best_start + win)

        results.append({
            "label": label_suffix or stype.capitalize(),
            "type": stype,
            "video_start_sec": max(0.0, video_start),
            "video_end_sec": max(0.0, video_end),
            "garmin_offset_sec": time_stream[best_start] if time_stream else best_start,
            "context": ctx,
        })

    return results


# ─── Async Fetch ─────────────────────────────────────────────────────────────

async def fetch_streams(activity_id: str) -> tuple[dict, dict]:
    client = IntervalsClient(settings.intervals_icu_athlete_id)
    activity, streams = await asyncio.gather(
        client.get_activity(activity_id),
        client.get_streams(activity_id),
    )
    return activity, streams


# ─── Main ────────────────────────────────────────────────────────────────────

from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Running Dynamics für Video-Zeitfenster extrahieren"
    )
    parser.add_argument("--activity-id", required=True)
    parser.add_argument("--video", default="")
    parser.add_argument("--offset-sec", type=float, default=None)
    parser.add_argument("--duration-sec", type=float, default=60)
    parser.add_argument("--summary", action="store_true")
    # Section-Finder
    parser.add_argument(
        "--find-sections",
        default="",
        help="Komma-getrennte Section-Typen: frisch,bergauf,müde,stabil,bergab,tempo,easy",
    )
    parser.add_argument(
        "--section-duration", type=int, default=25,
        help="Länge pro Section in Sekunden (default: 25)",
    )
    args = parser.parse_args()

    if args.find_sections:
        sub_mode = f"sections [{args.find_sections}]"
    elif args.summary:
        sub_mode = "summary"
    else:
        sub_mode = "single window"
    display = f"Extract run dynamics — {args.activity_id} ({sub_mode})"
    with script_span(
        "extract_run_dynamics",
        display_name=display,
        activity_id=args.activity_id,
        mode=sub_mode,
    ):
        _do_main(args)


def _do_main(args: argparse.Namespace) -> None:
    activity, streams = asyncio.run(fetch_streams(args.activity_id))

    act_start_str = activity.get("start_date_local") or activity.get("start_date", "")
    act_start: datetime | None = None
    if act_start_str:
        try:
            act_start = datetime.fromisoformat(act_start_str.replace("Z", "+00:00"))
            if act_start.tzinfo is None:
                act_start = act_start.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    if args.summary:
        total_sec = activity.get("elapsed_time", 0)
        print(f"Activity: {activity.get('name', '?')}")
        print(f"Start: {act_start_str}  |  Dauer: {total_sec // 60} min")
        print(f"Streams: {', '.join(k for k in streams if streams[k])}")
        print(f"Sections verfügbar: {', '.join(SECTION_TYPES.keys())}")
        print(f"\nGesamt: {summarize_window(streams, 0, len(streams.get('time', [1]) or [1]))}")
        return

    # Section-Finder-Modus
    if args.find_sections:
        # Video-Offset bestimmen
        video_offset = 0.0
        if args.video and act_start:
            vt = get_video_creation_time(args.video)
            if vt:
                delta = (vt - act_start).total_seconds()
                elapsed = activity.get("elapsed_time", 7200)
                video_offset = delta if 0 <= delta <= elapsed + 60 else 0.0
                print(f"  Video-Offset: {video_offset:.0f}s ab Activity-Start", file=sys.stderr)

        section_types = [s.strip() for s in args.find_sections.split(",") if s.strip()]
        sections = find_sections(
            streams,
            section_types,
            args.section_duration,
            video_offset,
            activity.get("elapsed_time", 3600),
        )
        print(json.dumps(sections, ensure_ascii=False, indent=2))
        return

    # Einzelnes Zeitfenster
    offset_sec: float = args.offset_sec or 0.0

    if args.offset_sec is None and args.video and act_start:
        vt = get_video_creation_time(args.video)
        if vt:
            delta = (vt - act_start).total_seconds()
            elapsed = activity.get("elapsed_time", 7200)
            offset_sec = delta if 0 <= delta <= elapsed + 60 else 0.0
            print(f"  Offset: {offset_sec:.0f}s", file=sys.stderr)

    start_idx, end_idx = find_stream_window(streams, offset_sec, args.duration_sec)
    print(summarize_window(streams, start_idx, end_idx))


if __name__ == "__main__":
    main()
