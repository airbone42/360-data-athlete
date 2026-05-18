"""Build sub-lap windows from merged stream + FIT record data with dynamic window sizing."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _to_timestamp(value: Any) -> float | None:
    """Convert datetime object or ISO string to Unix timestamp float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if hasattr(value, "timestamp"):
        return value.timestamp()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            return None
    return None


def _window_size_for_lap(duration_s: int) -> int:
    if duration_s > 600:
        return 300  # 5 min
    if duration_s >= 120:
        return 60   # 1 min
    return 30       # 30 s


def build_sub_laps(
    streams: dict[str, list],
    surface_labels: list[str],
    fit_records: list[dict],
    laps: list[dict],
) -> list[dict]:
    """Merge intervals.icu streams, surface labels, and FIT records into dynamic windows.

    Window size is chosen per-lap based on lap duration:
      >600s → 300s windows, >=120s → 60s windows, else → 30s windows

    Each window contains:
      window_index, lap_index, start_s, end_s, avg_pace_min_km,
      avg_hr, dominant_surface, avg_gct_ms, avg_stride_mm, avg_vo_mm, avg_cadence_spm
    """
    time_stream: list[int] = streams.get("time", [])
    hr_stream: list[float | None] = streams.get("heartrate", [])
    vel_stream: list[float | None] = streams.get("velocity_smooth", [])

    if not time_stream:
        return []

    # ── Align FIT records to stream timeline ──────────────────────────────────
    fit_by_offset: dict[int, dict] = {}
    if fit_records:
        first_ts = _to_timestamp(fit_records[0].get("timestamp"))
        if first_ts is not None:
            for rec in fit_records:
                ts = _to_timestamp(rec.get("timestamp"))
                if ts is not None:
                    offset_s = int(ts - first_ts)
                    fit_by_offset[offset_s] = rec

    # ── Lap boundaries (cumulative seconds) ───────────────────────────────────
    lap_boundaries: list[tuple[int, int, int]] = []  # (lap_idx, start_s, end_s)
    cursor = 0
    for lap in laps:
        dur = lap.get("duration_s") or 0
        lap_boundaries.append((lap.get("lap_index", 0), cursor, cursor + dur))
        cursor += dur

    # ── Build windows per-lap ─────────────────────────────────────────────────
    sub_laps: list[dict[str, Any]] = []
    window_index = 0

    for lap_idx, lap_start, lap_end in lap_boundaries:
        duration = lap_end - lap_start
        if duration <= 0:
            continue
        ws = _window_size_for_lap(duration)

        for win_start in range(lap_start, lap_end, ws):
            win_end = min(win_start + ws, lap_end)

            indices = [i for i, t in enumerate(time_stream) if win_start <= t < win_end]
            if not indices:
                continue

            # HR
            hr_vals = [hr_stream[i] for i in indices if i < len(hr_stream) and hr_stream[i] is not None]
            avg_hr = round(sum(hr_vals) / len(hr_vals)) if hr_vals else None

            # Pace
            vel_vals = [vel_stream[i] for i in indices if i < len(vel_stream) and vel_stream[i] is not None and vel_stream[i] > 0]
            if vel_vals:
                avg_vel = sum(vel_vals) / len(vel_vals)
                avg_pace = round(1000 / avg_vel / 60, 2)
            else:
                avg_pace = None

            # Dominant surface
            surf_vals = [surface_labels[i] for i in indices if i < len(surface_labels)]
            dominant_surface = max(set(surf_vals), key=surf_vals.count) if surf_vals else "unbekannt"

            # Running dynamics from FIT (match by offset)
            gct_vals, stride_vals, vo_vals, cadence_vals = [], [], [], []
            for i in indices:
                t = time_stream[i]
                rec = fit_by_offset.get(t) or fit_by_offset.get(t - 1) or fit_by_offset.get(t + 1)
                if rec:
                    if rec.get("stance_time") is not None:
                        gct_vals.append(rec["stance_time"])
                    if rec.get("step_length") is not None:
                        stride_vals.append(rec["step_length"])
                    if rec.get("vertical_oscillation") is not None:
                        vo_vals.append(rec["vertical_oscillation"])
                    if rec.get("cadence") is not None:
                        cadence_vals.append(rec["cadence"])

            avg_gct = round(sum(gct_vals) / len(gct_vals)) if gct_vals else None
            avg_stride = round(sum(stride_vals) / len(stride_vals)) if stride_vals else None
            avg_vo = round(sum(vo_vals) / len(vo_vals), 1) if vo_vals else None
            avg_cadence = round(sum(cadence_vals) / len(cadence_vals)) if cadence_vals else None

            sub_laps.append({
                "window_index": window_index,
                "lap_index": lap_idx,
                "start_s": win_start,
                "end_s": win_end,
                "avg_pace_min_km": avg_pace,
                "avg_hr": avg_hr,
                "dominant_surface": dominant_surface,
                "avg_gct_ms": avg_gct,
                "avg_stride_mm": avg_stride,
                "avg_vo_mm": avg_vo,
                "avg_cadence_spm": avg_cadence,
            })
            window_index += 1

    return sub_laps
