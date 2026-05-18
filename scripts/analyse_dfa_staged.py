"""DFA-Alpha1 Staged Step Test Analysis.

Analyzes a Polar RR CSV file against Garmin HR streams from intervals.icu
to produce per-stage DFA-alpha1 values for a treadmill lactate/VT1 step test.

Workflow:
    1. Load & clean Polar RR data (hard bounds + rolling median filter)
    2. Fetch Garmin HR stream via intervals.icu API
    3. Cross-correlate Polar HR vs Garmin HR to find time offset
    4. Extract per-stage RR windows using Garmin lap boundaries
    5. Compute DFA-alpha1 per stage (identical algorithm to analyse_hrv_dfa.py)
    6. Estimate VT1 via linear interpolation at DFA-alpha1 = 0.75

Usage:
    python3 scripts/analyse_dfa_staged.py \\
        --rr-file /path/to/polar_rr.bin \\
        --activity-id i12345678

Output: JSON to stdout
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

# Allow app/ imports — resolve repo root from this file's location
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.api.intervals_cache import CachedIntervalsClient  # noqa: E402


# ---------------------------------------------------------------------------
# DFA-Alpha1 — pure Python, identical to analyse_hrv_dfa.py
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _cumsum(values: list[float]) -> list[float]:
    """Cumulative sum after mean subtraction (integrated RR series)."""
    mu = _mean(values)
    result: list[float] = []
    total = 0.0
    for v in values:
        total += v - mu
        result.append(total)
    return result


def _detrend_segment(segment: list[float]) -> list[float]:
    """Remove linear trend from a segment via least-squares fit."""
    n = len(segment)
    if n < 2:
        return segment
    x_mean = (n - 1) / 2.0
    y_mean = _mean(segment)
    ss_xx = sum((i - x_mean) ** 2 for i in range(n))
    ss_xy = sum((i - x_mean) * (segment[i] - y_mean) for i in range(n))
    if ss_xx == 0:
        return [v - y_mean for v in segment]
    a = ss_xy / ss_xx
    b = y_mean - a * x_mean
    return [segment[i] - (a * i + b) for i in range(n)]


def _rms(values: list[float]) -> float:
    return math.sqrt(sum(v * v for v in values) / len(values))


def _log2(x: float) -> float:
    return math.log(x) / math.log(2)


def _linreg_slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    x_mean = _mean(xs)
    y_mean = _mean(ys)
    ss_xx = sum((x - x_mean) ** 2 for x in xs)
    ss_xy = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    if ss_xx == 0:
        return 0.0
    return ss_xy / ss_xx


def compute_dfa_alpha1(
    rr_values: list[float],
    min_box: int = 4,
    max_box: int = 16,
) -> float | None:
    """DFA-Alpha1 coefficient over box sizes 4–16 beats.

    Identical implementation to analyse_hrv_dfa.py.
    """
    n = len(rr_values)
    if n < max_box * 2:
        return None

    integrated = _cumsum(rr_values)
    box_sizes: list[int] = list(range(min_box, max_box + 1))

    log_n: list[float] = []
    log_f: list[float] = []

    for box in box_sizes:
        if box < 2 or n < box * 2:
            continue
        num_boxes = n // box
        if num_boxes < 2:
            continue
        fluctuations: list[float] = []
        for b in range(num_boxes):
            segment = integrated[b * box : (b + 1) * box]
            detrended = _detrend_segment(segment)
            fluctuations.append(_rms(detrended))
        if not fluctuations:
            continue
        f_n = _rms(fluctuations)
        if f_n > 0:
            log_n.append(_log2(box))
            log_f.append(_log2(f_n))

    if len(log_n) < 2:
        return None

    return _linreg_slope(log_n, log_f)


# ---------------------------------------------------------------------------
# Polar RR loading & cleaning
# ---------------------------------------------------------------------------

def load_and_clean_polar_rr(
    rr_path: Path,
) -> tuple[list[float], list[float], dict[str, int], float | None]:
    """Load Polar Sensor Logger CSV, apply artifact filtering, build time axis.

    Format: semicolon-delimited CSV with columns:
        Phone timestamp;RR-interval [ms]

    Time axis strategy (in order of preference):
      1. Phone timestamps — parsed directly, no drift from artifact removal.
         A linear drift correction is applied between first and last timestamps
         vs. cumulative RR total to handle phone clock drift.
      2. Cumulative RR sum — fallback when no phone timestamps found.

    Returns:
        cum_times         — time in seconds for each valid beat (relative to first beat)
        rr_values         — corresponding RR values in ms
        stats             — artifact statistics dict
        polar_start_epoch — Unix timestamp of first polar beat (or None if unavailable)
    """
    import csv
    from datetime import datetime, timezone

    # --- Read raw data -------------------------------------------------------
    raw_rr: list[float] = []
    raw_ts: list[float] = []  # phone timestamps as seconds since first beat

    with open(rr_path, newline="", encoding="utf-8-sig") as fh:
        first_line = fh.readline()
        delimiter = ";" if first_line.count(";") >= first_line.count(",") else ","
        fh.seek(0)
        reader = csv.DictReader(fh, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError("Empty CSV or no header row found")

        fieldnames_lower = {f.lower().strip(): f for f in reader.fieldnames if f}
        rr_col = (
            fieldnames_lower.get("rr-interval [ms]")
            or fieldnames_lower.get("rr_ms")
            or fieldnames_lower.get("rr interval (ms)")
            or fieldnames_lower.get("rr")
            or fieldnames_lower.get("ibi_ms")
        )
        ts_col = (
            fieldnames_lower.get("phone timestamp")
            or fieldnames_lower.get("timestamp")
            or fieldnames_lower.get("time")
        )
        if rr_col is None:
            raise ValueError(
                f"No RR column found. Available columns: {list(reader.fieldnames)}"
            )

        first_epoch: float | None = None
        for row in reader:
            raw = (row.get(rr_col) or "").strip()
            if not raw:
                continue
            try:
                rr_val = float(raw)
            except ValueError:
                continue
            raw_rr.append(rr_val)

            # Parse phone timestamp if available
            if ts_col:
                ts_str = (row.get(ts_col) or "").strip()
                try:
                    # ISO 8601 with or without timezone
                    ts_str_clean = ts_str.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(ts_str_clean)
                    epoch = dt.timestamp()
                    if first_epoch is None:
                        first_epoch = epoch
                    raw_ts.append(epoch - first_epoch)
                except (ValueError, AttributeError):
                    raw_ts.append(float("nan"))

    raw_count = len(raw_rr)
    polar_start_epoch = first_epoch if raw_ts else None

    # --- Hard bounds: 300–2000 ms -------------------------------------------
    after_hard_rr: list[float] = []
    after_hard_ts: list[float | None] = []
    hard_removed = 0
    for i, rr in enumerate(raw_rr):
        if 300.0 <= rr <= 2000.0:
            after_hard_rr.append(rr)
            after_hard_ts.append(raw_ts[i] if raw_ts else None)
        else:
            hard_removed += 1

    # --- Rolling median filter: window=11, threshold 25% -------------------
    rolling_window = 11
    half = rolling_window // 2
    after_rolling_rr: list[float] = []
    after_rolling_ts: list[float | None] = []
    rolling_removed = 0

    for i, rr in enumerate(after_hard_rr):
        lo = max(0, i - half)
        hi = min(len(after_hard_rr), i + half + 1)
        window_vals = sorted(after_hard_rr[lo:hi])
        median = window_vals[len(window_vals) // 2]
        if median == 0 or abs(rr - median) / median > 0.25:
            rolling_removed += 1
        else:
            after_rolling_rr.append(rr)
            after_rolling_ts.append(after_hard_ts[i])

    valid_count = len(after_rolling_rr)

    # --- Time axis: phone timestamps preferred over cumulative RR sum --------
    # Phone timestamps avoid drift caused by artifact removal. A linear drift
    # correction aligns the phone clock against the cumulative RR total.
    has_phone_ts = (
        bool(after_rolling_ts)
        and after_rolling_ts[0] is not None
        and after_rolling_ts[-1] is not None
        and not math.isnan(after_rolling_ts[0])  # type: ignore[arg-type]
        and not math.isnan(after_rolling_ts[-1])  # type: ignore[arg-type]
    )

    if has_phone_ts:
        # Linear drift correction: scale phone timestamps so that the total
        # span matches the cumulative RR duration (beats don't disappear, the
        # phone clock just ticks slightly fast/slow).
        cum_rr_total = sum(rr / 1000.0 for rr in after_rolling_rr)
        phone_total = after_rolling_ts[-1]  # type: ignore[index]
        if phone_total and phone_total > 0:
            scale = cum_rr_total / phone_total
        else:
            scale = 1.0
        cum_times = [
            (ts * scale) if (ts is not None and not math.isnan(ts)) else 0.0
            for ts in after_rolling_ts
        ]
    else:
        # Fallback: cumulative RR sum
        cum_times = []
        t = 0.0
        for rr in after_rolling_rr:
            cum_times.append(t)
            t += rr / 1000.0

    artifact_rate = 0.0
    if raw_count > 0:
        artifact_rate = round((raw_count - valid_count) / raw_count * 100, 2)

    stats: dict[str, int] = {
        "raw_beats": raw_count,
        "hard_bounds_removed": hard_removed,
        "rolling_median_removed": rolling_removed,
        "valid_beats": valid_count,
    }

    return cum_times, after_rolling_rr, stats, polar_start_epoch


# ---------------------------------------------------------------------------
# Garmin HR stream loading
# ---------------------------------------------------------------------------

async def fetch_garmin_hr(activity_id: str) -> dict[int, float]:
    """Fetch Garmin HR stream from intervals.icu. Returns {t_sec: hr_bpm}."""
    client = CachedIntervalsClient()
    streams = await client.get_streams(activity_id, types="time,heartrate")

    time_list: list[int] = streams.get("time") or []
    hr_list: list[float | None] = streams.get("heartrate") or []

    if not time_list or not hr_list:
        raise ValueError(
            f"No heartrate stream data for activity {activity_id}. "
            f"Available stream keys: {list(streams.keys())}"
        )

    garmin_hr: dict[int, float] = {}
    for t, hr in zip(time_list, hr_list):
        if hr is not None and t is not None:
            garmin_hr[int(t)] = float(hr)

    # Fill gaps via forward-fill for 1s grid interpolation
    if garmin_hr:
        max_t = max(garmin_hr.keys())
        last_hr = garmin_hr.get(0, next(iter(garmin_hr.values())))
        for t in range(max_t + 1):
            if t in garmin_hr:
                last_hr = garmin_hr[t]
            else:
                garmin_hr[t] = last_hr

    return garmin_hr


# ---------------------------------------------------------------------------
# Cross-correlation: Polar cumulative time vs Garmin time
# ---------------------------------------------------------------------------

def compute_polar_to_garmin_offset(
    polar_cum_times: list[float],
    polar_rr: list[float],
    garmin_hr: dict[int, float],
    search_range_s: int = 120,
) -> tuple[float, float]:
    """Find time offset between Polar cumulative time and Garmin time axis.

    Method:
        1. Compute instantaneous Polar HR (60000/rr_ms) per beat
        2. Aggregate to 1s grid via 30s rolling median
        3. Cross-correlate over stable stage region only (Garmin t > 600s)
           This avoids the Polar Phone-Timestamp drift in the first ~17 minutes.
           The RR cumulative time is correct throughout — only the phone timestamps
           have a drift; we use cumulative time exclusively, not phone timestamps.
        4. Offset = argmax of Pearson correlation

    Returns:
        (offset_s, correlation_r) where garmin_t = polar_cum_t + offset_s
    """
    if not polar_cum_times or not garmin_hr:
        return 0.0, 0.0

    # --- Build Polar 1s HR grid via 30s rolling median ----------------------
    max_polar_t = int(polar_cum_times[-1]) + 1
    polar_instant: dict[int, list[float]] = {}
    for ct, rr in zip(polar_cum_times, polar_rr):
        t_sec = int(ct)
        hr_inst = 60000.0 / rr
        if t_sec not in polar_instant:
            polar_instant[t_sec] = []
        polar_instant[t_sec].append(hr_inst)

    polar_1s: dict[int, float] = {}
    for t in range(max_polar_t + 1):
        vals: list[float] = []
        for dt in range(-15, 16):
            bucket = polar_instant.get(t + dt)
            if bucket:
                vals.extend(bucket)
        if vals:
            vals_sorted = sorted(vals)
            polar_1s[t] = vals_sorted[len(vals_sorted) // 2]

    garmin_max_t = max(garmin_hr.keys())

    # --- Restricted cross-correlation: only stable stage region --------------
    # Polar phone timestamps have drift in first ~17 min (t < ~600s in Polar
    # cumulative time). Correlation restricted to Garmin t > 600s avoids this.
    # Warm-up typically ends around t=596s, so stages start at ~600s+.
    STABLE_START_GARMIN = 600
    STABLE_START_POLAR = 600

    best_offset = 0
    best_corr = -1.0

    for offset in range(-search_range_s, search_range_s + 1):
        paired_g: list[float] = []
        paired_p: list[float] = []

        for t_g in range(STABLE_START_GARMIN, min(garmin_max_t, 3400) + 1):
            t_p = t_g - offset
            if t_p < STABLE_START_POLAR or t_p > max_polar_t:
                continue
            if t_g in garmin_hr and t_p in polar_1s:
                paired_g.append(garmin_hr[t_g])
                paired_p.append(polar_1s[t_p])

        if len(paired_g) < 30:
            continue

        n = len(paired_g)
        mean_g = sum(paired_g) / n
        mean_p = sum(paired_p) / n
        cov = sum((paired_g[i] - mean_g) * (paired_p[i] - mean_p) for i in range(n))
        std_g = math.sqrt(sum((v - mean_g) ** 2 for v in paired_g))
        std_p = math.sqrt(sum((v - mean_p) ** 2 for v in paired_p))

        if std_g == 0 or std_p == 0:
            continue

        corr = cov / (std_g * std_p)
        if corr > best_corr:
            best_corr = corr
            best_offset = offset

    return float(best_offset), round(best_corr, 4)


# ---------------------------------------------------------------------------
# Stage analysis
# ---------------------------------------------------------------------------

def analyze_stage(
    stage_num: int,
    target_hr_bpm: int,
    stage_start_garmin_s: int,
    dfa_window_start_s: int,
    dfa_window_end_s: int,
    polar_cum_times: list[float],
    polar_rr: list[float],
    garmin_hr: dict[int, float],
    polar_to_garmin_offset: float,
    same_sensor: bool = False,
) -> dict[str, Any]:
    """Compute DFA-alpha1 for one stage window.

    Polar time = Garmin time - offset  →  polar_t = garmin_t - offset
    """
    garmin_window = [dfa_window_start_s, dfa_window_end_s]

    # Convert Garmin window to Polar cumulative time
    polar_start = dfa_window_start_s - polar_to_garmin_offset
    polar_end = dfa_window_end_s - polar_to_garmin_offset

    # Extract beats in Polar window
    window_rr: list[float] = []
    for ct, rr in zip(polar_cum_times, polar_rr):
        if polar_start <= ct < polar_end:
            window_rr.append(rr)

    beats_in_window = len(window_rr)

    # Window artifact rate: compare beats in polar window before filtering
    # (post-filter beats vs expected beats at avg HR)
    warning: str | None = None
    if beats_in_window < 100:
        warning = f"Wenige Beats ({beats_in_window}) — Ergebnis unsicher"

    # DFA-alpha1
    dfa_alpha1: float | None = None
    if beats_in_window >= 2 * 16:  # need at least max_box * 2 beats
        alpha = compute_dfa_alpha1(window_rr)
        dfa_alpha1 = round(alpha, 4) if alpha is not None else None

    if dfa_alpha1 is None and warning is None:
        warning = f"Nicht genug Beats für DFA ({beats_in_window} < 32)"

    # Polar HR average in window
    polar_hr_avg: float | None = None
    if window_rr:
        polar_hr_avg = round(_mean([60000.0 / rr for rr in window_rr]), 1)

    # Garmin HR average in same Garmin window
    garmin_hrs_in_window: list[float] = [
        garmin_hr[t]
        for t in range(dfa_window_start_s, dfa_window_end_s)
        if t in garmin_hr
    ]
    garmin_hr_avg: float | None = None
    if garmin_hrs_in_window:
        garmin_hr_avg = round(_mean(garmin_hrs_in_window), 1)

    hr_diff: float | None = None
    if polar_hr_avg is not None and garmin_hr_avg is not None:
        hr_diff = round(polar_hr_avg - garmin_hr_avg, 1)

    # Sanity check: same physical sensor → HR streams must agree within 2 bpm
    SAME_SENSOR_MAX_DIFF = 2.0
    if same_sensor and hr_diff is not None and abs(hr_diff) > SAME_SENSOR_MAX_DIFF:
        sync_warn = f"Sync-Fehler: Polar/Garmin aus gleicher Quelle, aber Diff={hr_diff:+.1f} bpm (max ±{SAME_SENSOR_MAX_DIFF})"
        warning = (warning + " | " + sync_warn) if warning else sync_warn

    # Artifact rate in this window: compare to raw beats in same polar time
    # We only have post-filter data, so estimate from window density
    window_duration_s = polar_end - polar_start
    expected_beats = (window_duration_s / 60.0) * (polar_hr_avg or 120.0)
    window_artifact_rate = 0.0
    if expected_beats > 0 and beats_in_window < expected_beats:
        window_artifact_rate = round(
            max(0.0, (expected_beats - beats_in_window) / expected_beats * 100), 1
        )

    valid = dfa_alpha1 is not None

    return {
        "stage_num": stage_num,
        "target_hr_bpm": target_hr_bpm,
        "stage_start_garmin_s": stage_start_garmin_s,
        "dfa_window_garmin": garmin_window,
        "beats_in_window": beats_in_window,
        "window_artifact_rate_pct": window_artifact_rate,
        "polar_hr_avg_bpm": polar_hr_avg,
        "garmin_hr_avg_bpm": garmin_hr_avg,
        "hr_diff_bpm": hr_diff,
        "dfa_alpha1": dfa_alpha1,
        "valid": valid,
        "warning": warning,
    }


# ---------------------------------------------------------------------------
# VT1 estimation
# ---------------------------------------------------------------------------

VT1_DFA_THRESHOLD = 0.75


def estimate_vt1(stages: list[dict[str, Any]]) -> tuple[float | None, str]:
    """Linear interpolation of HR where DFA-alpha1 crosses 0.75 (descending)."""
    valid = [
        s for s in stages
        if s.get("valid") and s.get("dfa_alpha1") is not None
        and s.get("polar_hr_avg_bpm") is not None
    ]
    if len(valid) < 2:
        return None, "Weniger als 2 valide Stufen — kein Crossing berechenbar"

    for i in range(1, len(valid)):
        prev = valid[i - 1]
        curr = valid[i]
        alpha_prev: float = prev["dfa_alpha1"]
        alpha_curr: float = curr["dfa_alpha1"]
        hr_prev: float = prev["polar_hr_avg_bpm"]
        hr_curr: float = curr["polar_hr_avg_bpm"]

        if alpha_prev >= VT1_DFA_THRESHOLD > alpha_curr:
            d_alpha = alpha_curr - alpha_prev
            d_hr = hr_curr - hr_prev
            if d_alpha == 0:
                return round(hr_prev, 1), "linear_interpolation_at_0.75"
            frac = (VT1_DFA_THRESHOLD - alpha_prev) / d_alpha
            vt1 = round(hr_prev + frac * d_hr, 1)
            return vt1, "linear_interpolation_at_0.75"

    # Check if all stages already below threshold
    if all(s["dfa_alpha1"] < VT1_DFA_THRESHOLD for s in valid if s.get("dfa_alpha1") is not None):
        return None, "Alle Stufen bereits unter 0.75 — VT1 unterhalb Testbereich"

    # All above threshold
    return None, "Keine Stufe unter 0.75 — VT1 oberhalb Testbereich"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(args: argparse.Namespace) -> dict[str, Any]:
    rr_path = Path(args.rr_file)
    if not rr_path.exists():
        return {"error": f"RR-Datei nicht gefunden: {rr_path}"}

    stage_targets: list[int] = [int(x) for x in args.stage_targets.split(",")]
    num_stages = args.num_stages
    if len(stage_targets) != num_stages:
        return {
            "error": (
                f"stage_targets ({len(stage_targets)} Werte) stimmt nicht "
                f"mit num_stages ({num_stages}) überein"
            )
        }

    # 1. Load & clean Polar RR
    print("Lade Polar RR-Daten...", file=sys.stderr)
    cum_times, rr_values, artifact_stats, polar_start_epoch = load_and_clean_polar_rr(rr_path)

    artifact_rate_pct = 0.0
    if artifact_stats["raw_beats"] > 0:
        artifact_rate_pct = round(
            (artifact_stats["raw_beats"] - artifact_stats["valid_beats"])
            / artifact_stats["raw_beats"] * 100,
            2,
        )

    print(
        f"  Roh: {artifact_stats['raw_beats']} Beats | "
        f"Hard-bounds entfernt: {artifact_stats['hard_bounds_removed']} | "
        f"Rolling-Median entfernt: {artifact_stats['rolling_median_removed']} | "
        f"Valide: {artifact_stats['valid_beats']} ({100 - artifact_rate_pct:.1f}%)",
        file=sys.stderr,
    )

    # 2. Fetch Garmin HR
    print(f"Lade Garmin HR-Stream für {args.activity_id}...", file=sys.stderr)
    try:
        garmin_hr = await fetch_garmin_hr(args.activity_id)
    except Exception as exc:
        return {"error": f"Garmin HR-Stream Fehler: {exc}"}

    print(f"  Garmin HR: {len(garmin_hr)} Sekunden-Datenpunkte", file=sys.stderr)

    # 3. Determine Polar→Garmin time offset
    offset_method: str
    corr_r: float = 0.0

    if args.garmin_start_ts and polar_start_epoch is not None:
        # Deterministic offset from known start timestamps — no cross-correlation.
        # garmin_t = polar_time_relative_to_start + offset_s
        # offset_s = garmin_start - polar_start  (both in Unix epoch seconds)
        from datetime import datetime
        garmin_epoch = datetime.fromisoformat(
            args.garmin_start_ts.replace("Z", "+00:00")
        ).timestamp()
        offset_s = garmin_epoch - polar_start_epoch
        offset_method = "timestamp_delta"
        print(
            f"  Zeitversatz: {offset_s:+.1f}s (aus Timestamps: Garmin={args.garmin_start_ts}, "
            f"Polar-Start={datetime.fromtimestamp(polar_start_epoch).isoformat()})",
            file=sys.stderr,
        )
    else:
        # Fallback: cross-correlation
        print("Berechne Polar→Garmin Zeitversatz (Cross-Korrelation)...", file=sys.stderr)
        offset_s, corr_r = compute_polar_to_garmin_offset(
            cum_times, rr_values, garmin_hr, search_range_s=60
        )
        offset_method = "cross_correlation"
        print(
            f"  Zeitversatz: {offset_s:+.0f}s | Korrelation: r={corr_r:.4f}",
            file=sys.stderr,
        )

    print(
        f"  Interpretation: Polar läuft {abs(offset_s):.1f}s "
        f"{'früher' if offset_s > 0 else 'später'} als Garmin | Methode: {offset_method}",
        file=sys.stderr,
    )

    same_sensor = args.same_sensor

    # 4. Compute stage windows & DFA-alpha1
    stages: list[dict[str, Any]] = []
    for n in range(num_stages):
        stage_start = args.warm_up_secs + n * args.stage_secs
        dfa_win_start = stage_start + args.dfa_window_start
        dfa_win_end = stage_start + args.dfa_window_end

        print(
            f"  Stufe {n + 1} (Ziel {stage_targets[n]} bpm) | "
            f"Garmin {dfa_win_start}–{dfa_win_end}s | "
            f"Polar {dfa_win_start - offset_s:.0f}–{dfa_win_end - offset_s:.0f}s",
            file=sys.stderr,
        )

        stage_result = analyze_stage(
            stage_num=n + 1,
            target_hr_bpm=stage_targets[n],
            stage_start_garmin_s=stage_start,
            dfa_window_start_s=dfa_win_start,
            dfa_window_end_s=dfa_win_end,
            polar_cum_times=cum_times,
            polar_rr=rr_values,
            garmin_hr=garmin_hr,
            polar_to_garmin_offset=offset_s,
            same_sensor=same_sensor,
        )
        stages.append(stage_result)

        status = f"DFA-α1={stage_result['dfa_alpha1']}" if stage_result["valid"] else "UNGÜLTIG"
        warn = f" | ⚠️  {stage_result['warning']}" if stage_result.get("warning") else ""
        print(
            f"    → {stage_result['beats_in_window']} Beats | "
            f"Polar HR={stage_result['polar_hr_avg_bpm']} bpm | "
            f"Garmin HR={stage_result['garmin_hr_avg_bpm']} bpm | "
            f"Diff={stage_result['hr_diff_bpm']} bpm | {status}{warn}",
            file=sys.stderr,
        )

    # 5. VT1 estimation
    vt1_bpm, vt1_method = estimate_vt1(stages)
    if vt1_bpm is not None:
        print(f"\nVT1-Schätzung: {vt1_bpm} bpm ({vt1_method})", file=sys.stderr)
    else:
        print(f"\nVT1-Schätzung: nicht möglich — {vt1_method}", file=sys.stderr)

    # Garmin start from args or activity data
    garmin_start_local = args.garmin_start_ts or "unbekannt"

    return {
        "activity_id": args.activity_id,
        "garmin_start_local": garmin_start_local,
        "polar_to_garmin_offset_s": offset_s,
        "offset_method": offset_method,
        "cross_correlation_r": corr_r,
        "same_sensor": same_sensor,
        "warm_up_secs": args.warm_up_secs,
        "stage_secs": args.stage_secs,
        "artifact_stats": {
            **artifact_stats,
            "artifact_rate_pct": artifact_rate_pct,
        },
        "stages": stages,
        "vt1_estimate_bpm": vt1_bpm,
        "vt1_method": vt1_method,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DFA-Alpha1 Stufentest-Analyse (Polar RR + Garmin HR)"
    )
    parser.add_argument("--rr-file", required=True, help="Polar Sensor Logger CSV/BIN Datei")
    parser.add_argument("--activity-id", required=True, help="intervals.icu Activity ID (z.B. i12345678)")
    # Demo defaults below — pass actual stage targets / durations via CLI for your
    # own stepped-test protocol (athlete-specific watt ranges / step lengths).
    parser.add_argument(
        "--stage-targets",
        default="100,120,140,160,180,200,220",
        help="Komma-getrennte Ziel-Werte der Stufen (Watt oder HR, demo-default)",
    )
    parser.add_argument("--warm-up-secs", type=int, default=600, help="Warm-up-Dauer in Sekunden (demo-default: 600)")
    parser.add_argument("--stage-secs", type=int, default=300, help="Stufendauer in Sekunden (demo-default: 300)")
    parser.add_argument("--num-stages", type=int, default=7, help="Anzahl Teststufen (demo-default: 7)")
    parser.add_argument("--dfa-window-start", type=int, default=120, help="DFA-Fenster-Start ab Stufenanfang in Sekunden (default: 120)")
    parser.add_argument("--dfa-window-end", type=int, default=420, help="DFA-Fenster-Ende ab Stufenanfang in Sekunden (default: 420)")
    parser.add_argument(
        "--garmin-start-ts",
        default=None,
        help="Aktivitäts-Start als ISO-Timestamp (z.B. 2025-04-22T08:57:21). "
             "Wenn angegeben wird der Offset deterministisch aus Timestamps berechnet "
             "statt per Cross-Korrelation.",
    )
    parser.add_argument(
        "--same-sensor",
        action="store_true",
        default=False,
        help="Externer HRM-Gurt und Watch nutzen dieselbe physische Sensorquelle "
             "(z.B. Polar H10 gleichzeitig zur Watch und zur Logger-App gestreamt). "
             "Aktiviert HR-Matching-Sanity-Check (max ±2 bpm Diff pro Stufe).",
    )
    args = parser.parse_args()

    result = asyncio.run(run(args))
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
