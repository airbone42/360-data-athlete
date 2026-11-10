"""Compact per-activity summary for /analyse — computed in code, not by the model.

Before this module the /analyse flow dumped every stream with indent=2
(hundreds of KB, far past the tool-output limit) and asked the model to pass
streams between scripts via ``echo``. ``summarize_activity`` takes the raw
pieces (intervals.icu activity, laps, streams, optionally parsed FIT laps /
records and surface labels) and returns only what the analysis needs:

* HR avg / max, pace, power, cadence and running dynamics per lap and per
  sub-lap window,
* time in HR zones, using the zones of the activity's own sport
  (``sport_hr_settings``; a ride is not judged on run zones),
* aerobic decoupling — the intervals.icu value and our own, computed on the
  main block when one exists.

Pure functions only; ``scripts/analyse_activity.py`` does the fetching.
"""
from __future__ import annotations

from typing import Any

from app.utils.hr_zones import ZONE_NAMES, format_hr_zones, sport_hr_settings
from app.utils.windowing import build_sub_laps, lap_boundaries

RUN_TYPES = {"Run", "VirtualRun", "TrailRun"}
# A gap in the elapsed time stream longer than this is a pause, not training.
_MAX_SAMPLE_GAP_S = 5
# The block decoupling is computed on must be long enough for drift to show.
_DECOUPLING_MIN_BLOCK_S = 20 * 60


def _pace_str(speed_ms: float | None) -> str | None:
    if not speed_ms or speed_ms <= 0:
        return None
    sec = 1000 / speed_ms
    m, s = divmod(int(round(sec)), 60)
    return f"{m}:{s:02d}/km"


def _pace_from_min_km(value: float | None) -> str | None:
    """windowing reports pace as decimal minutes (5.25) — render as m:ss."""
    if not value:
        return None
    m = int(value)
    s = int(round((value - m) * 60))
    if s == 60:
        m, s = m + 1, 0
    return f"{m}:{s:02d}/km"


def _compact(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None and v != [] and v != {}}


def _mean(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _indices(time: list, start_s: int, end_s: int) -> list[int]:
    return [i for i, t in enumerate(time) if t is not None and start_s <= t < end_s]


def _series(streams: dict, key: str, idx: list[int]) -> list[float]:
    data = streams.get(key) or []
    return [data[i] for i in idx if i < len(data) and data[i] is not None]


def _window_stats(streams: dict, idx: list[int], is_run: bool) -> dict:
    hr = _series(streams, "heartrate", idx)
    watts = _series(streams, "watts", idx)
    vel = [v for v in _series(streams, "velocity_smooth", idx) if v > 0.3]
    cad = [c for c in _series(streams, "cadence", idx) if c > 0]
    return _compact({
        "avg_hr": round(_mean(hr)) if hr else None,
        "max_hr": round(max(hr)) if hr else None,
        "avg_watts": round(_mean(watts)) if watts else None,
        "max_watts": round(max(watts)) if watts else None,
        "pace": _pace_str(_mean(vel)) if is_run and vel else None,
        "speed_kmh": round(_mean(vel) * 3.6, 1) if not is_run and vel else None,
        "avg_cadence": round(_mean(cad)) if cad else None,
    })


def zones_for(athlete_settings: dict | None, activity_type: str | None) -> dict | None:
    """HR zones of the activity's sport, falling back to Run (labelled as such)."""
    sport = activity_type or ""
    s = sport_hr_settings(athlete_settings, sport) if sport else None
    label = "Ride" if sport and sport not in RUN_TYPES else "Run"
    fallback = False
    if not s or not any(s["bounds"]):
        s = sport_hr_settings(athlete_settings, "Run")
        label, fallback = "Run", bool(sport and sport not in RUN_TYPES)
    if not s or not any(s["bounds"]):
        return None
    out = {
        "sport": label if not fallback else f"Run (no HR zones for {sport})",
        "lthr": s["lthr"],
        "max_hr": s["max_hr"],
        "bounds": s["bounds"],
        "line": format_hr_zones(s["bounds"]),
    }
    return out


def hr_zone_times(streams: dict, bounds: list[int]) -> list[dict]:
    """Minutes per HR zone; a 0 bound is reported as ``not set``, never merged."""
    time = streams.get("time") or []
    hr = streams.get("heartrate") or []
    secs = [0.0] * len(bounds)
    above = 0.0
    for i in range(min(len(time), len(hr)) - 1):
        h = hr[i]
        if h is None or time[i] is None or time[i + 1] is None:
            continue
        dt = time[i + 1] - time[i]
        if dt <= 0 or dt > _MAX_SAMPLE_GAP_S:
            continue
        for z, upper in enumerate(bounds):
            if upper and h <= upper:
                secs[z] += dt
                break
        else:
            above += dt
    total = sum(secs) + above
    out: list[dict] = []
    prev = 0
    for z, upper in enumerate(bounds):
        name = ZONE_NAMES[z] if z < len(ZONE_NAMES) else f"Zone {z + 1}"
        if not upper:
            out.append({"zone": f"Z{z + 1} ({name})", "range": "not set in intervals.icu"})
            continue
        out.append({
            "zone": f"Z{z + 1} ({name})",
            "range": f"{prev + 1}–{upper} bpm",
            "min": round(secs[z] / 60, 1),
            "pct": round(100 * secs[z] / total) if total else 0,
        })
        prev = upper
    if above:
        out.append({"zone": "above top bound", "range": f">{prev} bpm",
                    "min": round(above / 60, 1),
                    "pct": round(100 * above / total) if total else 0})
    return out


def decoupling(streams: dict, start_s: int, end_s: int, is_run: bool) -> dict | None:
    """Aerobic decoupling (Pa:HR for runs, Pw:HR otherwise) over [start_s, end_s).

    Efficiency = output / HR per half; decoupling % = (EF1 - EF2) / EF1 * 100.
    Positive = HR drifted up relative to output.
    """
    idx = _indices(streams.get("time") or [], start_s, end_s)
    if len(idx) < 60:
        return None
    key = "velocity_smooth" if is_run else "watts"
    out_s = streams.get(key) or []
    hr_s = streams.get("heartrate") or []
    pairs = [(out_s[i], hr_s[i]) for i in idx
             if i < len(out_s) and i < len(hr_s) and out_s[i] and hr_s[i]]
    if len(pairs) < 60:
        return None
    half = len(pairs) // 2

    def ef(chunk: list[tuple[float, float]]) -> float:
        return sum(o for o, _ in chunk) / sum(h for _, h in chunk)

    ef1, ef2 = ef(pairs[:half]), ef(pairs[half:])
    if not ef1:
        return None
    return {"pct": round((ef1 - ef2) / ef1 * 100, 1),
            "basis": "pace:HR" if is_run else "power:HR"}


def laps_from_intervals(intervals: list[dict], time: list) -> list[dict]:
    """intervals.icu ``icu_intervals`` → laps on the stream time axis."""
    laps: list[dict] = []
    for n, iv in enumerate(intervals or []):
        si, ei = iv.get("start_index"), iv.get("end_index")
        if si is None or ei is None or not time:
            continue
        si = max(0, min(int(si), len(time) - 1))
        ei = max(0, min(int(ei), len(time) - 1))
        if time[si] is None or time[ei] is None:
            continue
        laps.append({
            "lap_index": n + 1,
            "start_s": int(time[si]),
            "end_s": int(time[ei]) + 1,
            "type": iv.get("type"),
            "label": iv.get("label"),
            "distance_m": iv.get("distance"),
            "moving_s": iv.get("moving_time"),
        })
    return laps


def _fit_dynamics(lap: dict) -> dict:
    return _compact({
        "avg_gct_ms": lap.get("avg_stance_time"),
        "avg_step_length_mm": lap.get("avg_step_length"),
        "avg_vo_mm": lap.get("avg_vertical_osc"),
        "gct_balance_left_pct": lap.get("avg_stance_balance"),
        "ascent_m": lap.get("total_ascent"),
    })


def summarize_activity(
    activity: dict,
    streams: dict | None,
    intervals: list[dict] | None,
    athlete_settings: dict | None,
    *,
    fit_laps: list[dict] | None = None,
    fit_records: list[dict] | None = None,
    surface_labels: list[str] | None = None,
    data_note: str | None = None,
) -> dict:
    """Build the compact analysis payload (see module docstring)."""
    streams = streams or {}
    a_type = activity.get("type") or ""
    is_run = a_type in RUN_TYPES
    time = streams.get("time") or []
    notes: list[str] = [data_note] if data_note else []

    zones = zones_for(athlete_settings, a_type)
    head = _compact({
        "id": activity.get("id"),
        "date": (activity.get("start_date_local") or "")[:16],
        "type": a_type,
        "name": activity.get("name"),
        "source": activity.get("source"),
        "trainer": activity.get("trainer") or None,
        "duration_min": round((activity.get("moving_time") or 0) / 60, 1) or None,
        "distance_km": round((activity.get("distance") or 0) / 1000, 2) or None,
        "session_avg_hr": activity.get("average_heartrate"),
        "session_max_hr": activity.get("max_heartrate"),
        "avg_watts": activity.get("icu_average_watts") or activity.get("average_watts"),
        "weighted_avg_watts": activity.get("icu_weighted_avg_watts"),
        "pace": _pace_str(activity.get("average_speed")) if is_run else None,
        "gap_pace": _pace_str(activity.get("gap")) if is_run else None,
        "elevation_gain_m": activity.get("total_elevation_gain"),
        "elevation_loss_m": activity.get("total_elevation_loss"),
        "avg_cadence": activity.get("average_cadence"),
        "training_load": activity.get("icu_training_load"),
        "lthr_on_activity": activity.get("lthr"),
    })

    result: dict[str, Any] = {"activity": head}

    if not time:
        notes.append("no streams on this activity (manual entry?) — work from the description")
        result["data_source"] = "none"
        result["notes"] = notes
        if activity.get("decoupling") is not None:
            result["decoupling"] = {"intervals_icu_pct": activity.get("decoupling")}
        return result

    if fit_laps:
        laps = fit_laps
        result["data_source"] = "fit"
    else:
        laps = laps_from_intervals(intervals or [], time)
        result["data_source"] = "intervals_streams"
        if not laps:
            laps = [{"lap_index": 1, "start_s": int(time[0] or 0), "end_s": int(time[-1] or 0) + 1}]
            notes.append("no laps recorded — whole session treated as one lap")

    windows = build_sub_laps(
        streams=streams,
        surface_labels=surface_labels or [],
        fit_records=fit_records or [],
        laps=laps,
    )
    by_lap: dict[int, list[dict]] = {}
    for w in windows:
        by_lap.setdefault(w["lap_index"], []).append(w)

    meta_by_idx = {lap.get("lap_index", n + 1): lap for n, lap in enumerate(laps)}
    lap_out: list[dict] = []
    longest_work: tuple[int, int, int] | None = None
    for lap_idx, start_s, end_s in lap_boundaries(laps):
        if end_s <= start_s:
            continue
        idx = _indices(time, start_s, end_s)
        meta = meta_by_idx.get(lap_idx, {})
        stats = _window_stats(streams, idx, is_run)
        dist = meta.get("distance_m")
        entry = _compact({
            "lap": lap_idx,
            "type": meta.get("type"),
            "label": meta.get("label"),
            "start_min": round(start_s / 60, 1),
            "duration_min": round((end_s - start_s) / 60, 1),
            "distance_km": round(dist / 1000, 2) if dist else None,
            **stats,
            **_fit_dynamics(meta),
        })
        subs = by_lap.get(lap_idx, [])
        if len(subs) > 1:
            entry["sub_laps"] = [
                _compact({
                    "start_min": round(w["start_s"] / 60, 1),
                    "end_min": round(w["end_s"] / 60, 1),
                    "avg_hr": w.get("avg_hr"),
                    "max_hr": w.get("max_hr"),
                    "avg_watts": w.get("avg_watts"),
                    "pace": _pace_from_min_km(w.get("avg_pace_min_km")) if is_run else None,
                    "avg_cadence_spm": w.get("avg_cadence_spm"),
                    "avg_gct_ms": w.get("avg_gct_ms"),
                    "avg_step_length_mm": w.get("avg_stride_mm"),
                    "avg_vo_mm": w.get("avg_vo_mm"),
                    "gct_balance_left_pct": w.get("avg_gct_balance_pct"),
                    "surface": w.get("dominant_surface")
                    if w.get("dominant_surface") not in (None, "unbekannt") else None,
                })
                for w in subs
            ]
        lap_out.append(entry)
        is_work = (meta.get("type") or "WORK").upper() == "WORK"
        if is_work and (longest_work is None
                        or end_s - start_s > longest_work[2] - longest_work[1]):
            longest_work = (lap_idx, start_s, end_s)
    result["laps"] = lap_out

    if zones:
        result["hr_zones"] = _compact({
            "sport": zones["sport"],
            "lthr": zones["lthr"],
            "max_hr": zones["max_hr"],
            "line": zones["line"],
        })
        if streams.get("heartrate"):
            result["hr_zone_times"] = hr_zone_times(streams, zones["bounds"])
    else:
        notes.append("no HR zones in intervals.icu sport settings — zone times omitted")

    dec: dict[str, Any] = {}
    if activity.get("decoupling") is not None:
        dec["intervals_icu_pct"] = activity.get("decoupling")
    if longest_work and longest_work[2] - longest_work[1] >= _DECOUPLING_MIN_BLOCK_S:
        block = decoupling(streams, longest_work[1], longest_work[2], is_run)
        if block:
            dec["main_block"] = {"lap": longest_work[0], **block}
    whole = decoupling(streams, int(time[0] or 0), int(time[-1] or 0) + 1, is_run)
    if whole:
        dec["session"] = whole
    if dec:
        result["decoupling"] = dec
    if notes:
        result["notes"] = notes
    return result
