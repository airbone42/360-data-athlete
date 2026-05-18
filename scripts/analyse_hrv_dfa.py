"""DFA-Alpha1 HRV Analysis Script.

Calculates Detrended Fluctuation Analysis Alpha-1 coefficient from RR-interval data.
Identifies the aerobic threshold (VT1) where DFA-alpha1 ≈ 0.75.

Supported input sources:
    - FIT file with `hrv` messages (Garmin native HRV recording)
    - CSV file with columns: rr_ms (and optionally timestamp_s)
    - TXT file with one RR value per line (milliseconds)

Usage:
    python3 scripts/analyse_hrv_dfa.py --input /path/to/file.fit
    python3 scripts/analyse_hrv_dfa.py --input /path/to/rr.csv --source polar_csv
    python3 scripts/analyse_hrv_dfa.py --input /path/to/rr.txt --source txt
    python3 scripts/analyse_hrv_dfa.py --input /path/to/file.fit --window-size 60 --step 10

Output: JSON to stdout
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# RR-Interval I/O
# ---------------------------------------------------------------------------

def load_rr_from_fit(fit_path: Path) -> list[dict[str, float]]:
    """Extract RR intervals from FIT file hrv messages.

    Older ANT+ watches without native HRV-message support do NOT record a
    native `hrv` message block when paired with an external HRM strap
    (Polar H10 or equivalent) — they only store epoch-level HR in `record`
    messages.  Modern Garmin devices (e.g. Fenix 6+ / FR945+ class) do
    persist `hrv` messages even from ANT+ straps.  This function attempts
    both paths:
      1. `hrv` messages  →  cumulative time[] array → delta = RR in ms
      2. `record` messages with field `heart_rate_variability` (rare)

    Returns:
        List of {"timestamp_s": float, "rr_ms": float}
    """
    try:
        import fitparse  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("fitparse is required: pip install fitparse") from exc

    fitfile = fitparse.FitFile(str(fit_path))
    rr_records: list[dict[str, float]] = []
    cumulative_s: float = 0.0

    # Path 1 — hrv messages
    for msg in fitfile.get_messages("hrv"):
        times = msg.get_value("time")
        if times is None:
            continue
        # `time` field is a list of RR intervals in seconds (float)
        if not isinstance(times, (list, tuple)):
            times = [times]
        for interval_s in times:
            if interval_s is None:
                continue
            rr_ms = interval_s * 1000.0
            # Physiological filter: 300–2000 ms (30–200 bpm)
            if 300.0 <= rr_ms <= 2000.0:
                rr_records.append({"timestamp_s": cumulative_s, "rr_ms": rr_ms})
            cumulative_s += interval_s

    if rr_records:
        return rr_records

    # Path 2 — record messages with heart_rate_variability field (fallback)
    for msg in fitfile.get_messages("record"):
        ts = msg.get_value("timestamp")
        hrv_val = msg.get_value("heart_rate_variability")
        if hrv_val is not None and ts is not None:
            ts_s = ts.timestamp() if hasattr(ts, "timestamp") else float(ts)
            rr_ms = float(hrv_val)
            if 300.0 <= rr_ms <= 2000.0:
                rr_records.append({"timestamp_s": ts_s, "rr_ms": rr_ms})

    return rr_records


def load_rr_from_csv(csv_path: Path) -> list[dict[str, float]]:
    """Load RR intervals from CSV file.

    Expected columns (case-insensitive):
        rr_ms  — RR interval in milliseconds (required)
        timestamp_s  — cumulative seconds from start (optional)

    Polar Beat / Elite HRV / Fatmaxxer / Polar Sensor Logger export formats supported.
    Polar Sensor Logger uses semicolons and 'RR-interval [ms]' column name.
    """
    import csv
    from datetime import datetime

    rr_records: list[dict[str, float]] = []

    # Auto-detect delimiter by sniffing first line
    with open(csv_path, encoding="utf-8-sig") as fh:
        first_line = fh.readline()
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        if reader.fieldnames is None:
            return rr_records

        # Normalise field names
        fieldnames_lower = {f.lower().strip(): f for f in reader.fieldnames if f}

        rr_col = (
            fieldnames_lower.get("rr_ms")
            or fieldnames_lower.get("rr")
            or fieldnames_lower.get("rr interval (ms)")
            or fieldnames_lower.get("rr-interval [ms]")  # Polar Sensor Logger
            or fieldnames_lower.get("ibi_ms")
        )
        ts_col = (
            fieldnames_lower.get("timestamp_s")
            or fieldnames_lower.get("time")
            or fieldnames_lower.get("timestamp")
            or fieldnames_lower.get("phone timestamp")  # Polar Sensor Logger
        )

        if rr_col is None:
            raise ValueError(
                f"No RR column found in {csv_path}. "
                f"Available columns: {list(reader.fieldnames)}"
            )

        _t0_dt: datetime | None = None

        cumulative_s = 0.0
        for row in reader:
            raw = row.get(rr_col, "").strip()
            if not raw:
                continue
            try:
                rr_ms = float(raw)
            except ValueError:
                continue

            if not (300.0 <= rr_ms <= 2000.0):
                continue

            if ts_col and row.get(ts_col, "").strip():
                ts_raw = row[ts_col].strip()
                try:
                    ts_s = float(ts_raw)
                except ValueError:
                    # ISO timestamp (Polar Sensor Logger): derive elapsed seconds from first row
                    try:
                        dt = datetime.fromisoformat(ts_raw)
                        if _t0_dt is None:
                            _t0_dt = dt
                        ts_s = (dt - _t0_dt).total_seconds()
                    except ValueError:
                        ts_s = cumulative_s
            else:
                ts_s = cumulative_s

            rr_records.append({"timestamp_s": ts_s, "rr_ms": rr_ms})
            cumulative_s += rr_ms / 1000.0

    return rr_records


def load_rr_from_txt(txt_path: Path) -> list[dict[str, float]]:
    """Load RR intervals from a plain text file (one value per line, ms)."""
    rr_records: list[dict[str, float]] = []
    cumulative_s = 0.0
    with open(txt_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rr_ms = float(line)
            except ValueError:
                continue
            if 300.0 <= rr_ms <= 2000.0:
                rr_records.append({"timestamp_s": cumulative_s, "rr_ms": rr_ms})
                cumulative_s += rr_ms / 1000.0
    return rr_records


# ---------------------------------------------------------------------------
# DFA-Alpha1 — pure Python implementation (no numpy/scipy)
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
    """Remove linear trend from a segment via least-squares line fit."""
    n = len(segment)
    if n < 2:
        return segment

    # Least-squares linear fit: y = a*x + b
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
    """Root mean square."""
    return math.sqrt(sum(v * v for v in values) / len(values))


def _log2(x: float) -> float:
    return math.log(x) / math.log(2)


def _linreg_slope(xs: list[float], ys: list[float]) -> float:
    """Simple linear regression slope."""
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
    """Compute DFA-Alpha1 coefficient.

    Short-range scaling exponent over box sizes 4–16 beats.
    Standard for aerobic threshold identification (Gronwald et al.).

    Args:
        rr_values: List of RR intervals in milliseconds.
        min_box:   Minimum box size (default 4).
        max_box:   Maximum box size (default 16).

    Returns:
        Alpha1 exponent (float) or None if insufficient data.
    """
    n = len(rr_values)
    if n < max_box * 2:
        return None

    integrated = _cumsum(rr_values)

    # Box sizes: powers of 2 from min_box to max_box (inclusive)
    box_sizes: list[int] = []
    bs = min_box
    while bs <= max_box:
        box_sizes.append(bs)
        bs = bs * 2
    # Add intermediate sizes for better resolution
    all_boxes: list[int] = sorted(set(
        list(range(min_box, max_box + 1))
    ))
    # Use subset: 4,5,6,7,8,9,10,11,12,13,14,15,16
    box_sizes = all_boxes

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
# Windowed DFA analysis
# ---------------------------------------------------------------------------

def compute_windowed_dfa(
    rr_records: list[dict[str, float]],
    window_s: int = 120,
    step_s: int = 60,
    min_beats: int = 60,
) -> list[dict[str, Any]]:
    """Compute DFA-alpha1 in sliding windows over the RR time series.

    Args:
        rr_records:  List of {"timestamp_s": float, "rr_ms": float}
        window_s:    Window size in seconds (default 120 s)
        step_s:      Step size in seconds (default 60 s)
        min_beats:   Minimum number of beats required per window

    Returns:
        List of window dicts with start_s, end_s, hr_avg, dfa_alpha1, beat_count.
    """
    if not rr_records:
        return []

    t_start = rr_records[0]["timestamp_s"]
    t_end = rr_records[-1]["timestamp_s"]
    total_duration = t_end - t_start

    if total_duration < window_s:
        # Single window over all data
        rr_vals = [r["rr_ms"] for r in rr_records]
        alpha = compute_dfa_alpha1(rr_vals)
        hr_avg = 60000.0 / _mean(rr_vals) if rr_vals else None
        return [{
            "start_s": int(t_start),
            "end_s": int(t_end),
            "hr_avg": round(hr_avg, 1) if hr_avg else None,
            "dfa_alpha1": round(alpha, 4) if alpha is not None else None,
            "beat_count": len(rr_vals),
        }]

    windows: list[dict[str, Any]] = []
    cursor = t_start

    while cursor + window_s <= t_end + step_s:
        w_start = cursor
        w_end = cursor + window_s

        segment = [
            r for r in rr_records
            if w_start <= r["timestamp_s"] < w_end
        ]

        if len(segment) >= min_beats:
            rr_vals = [r["rr_ms"] for r in segment]
            alpha = compute_dfa_alpha1(rr_vals)
            hr_avg = 60000.0 / _mean(rr_vals)
            windows.append({
                "start_s": int(w_start),
                "end_s": int(w_end),
                "hr_avg": round(hr_avg, 1),
                "dfa_alpha1": round(alpha, 4) if alpha is not None else None,
                "beat_count": len(rr_vals),
            })

        cursor += step_s

    return windows


# ---------------------------------------------------------------------------
# VT1 estimation
# ---------------------------------------------------------------------------

VT1_DFA_THRESHOLD = 0.75


def estimate_vt1(windows: list[dict[str, Any]]) -> float | None:
    """Estimate VT1 as the HR where DFA-alpha1 first crosses 0.75 (descending).

    Aerobic threshold is where DFA-alpha1 drops from > 0.75 to < 0.75
    during increasing intensity.  This function finds the crossing point
    via linear interpolation between the last window above threshold and
    the first window below.

    Returns: HR in bpm at VT1, or None if threshold not crossed.
    """
    valid = [w for w in windows if w.get("dfa_alpha1") is not None and w.get("hr_avg") is not None]
    if len(valid) < 2:
        return None

    for i in range(1, len(valid)):
        prev = valid[i - 1]
        curr = valid[i]
        if prev["dfa_alpha1"] >= VT1_DFA_THRESHOLD > curr["dfa_alpha1"]:
            # Linear interpolation
            d_alpha = curr["dfa_alpha1"] - prev["dfa_alpha1"]
            d_hr = curr["hr_avg"] - prev["hr_avg"]
            if d_alpha == 0:
                return round(prev["hr_avg"], 1)
            frac = (VT1_DFA_THRESHOLD - prev["dfa_alpha1"]) / d_alpha
            return round(prev["hr_avg"] + frac * d_hr, 1)

    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def detect_source(path: Path, source_hint: str | None) -> str:
    """Determine data source type from file extension or explicit hint."""
    if source_hint:
        return source_hint.lower()
    suffix = path.suffix.lower()
    if suffix == ".fit":
        return "fit"
    if suffix == ".csv":
        return "polar_csv"
    if suffix in (".txt", ".log"):
        return "txt"
    return "fit"


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(
        description="DFA-Alpha1 HRV analysis from FIT or CSV/TXT RR data."
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to input file (.fit / .csv / .txt)"
    )
    parser.add_argument(
        "--source",
        choices=["fit", "polar_csv", "txt"],
        default=None,
        help="Override auto-detected source type"
    )
    parser.add_argument(
        "--window-size", type=int, default=120,
        help="Sliding window size in seconds (default: 120)"
    )
    parser.add_argument(
        "--step", type=int, default=60,
        help="Sliding window step in seconds (default: 60)"
    )
    parser.add_argument(
        "--min-beats", type=int, default=60,
        help="Minimum beats required per window (default: 60)"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(json.dumps({"error": f"File not found: {input_path}"}))
        sys.exit(1)

    source = detect_source(input_path, args.source)

    # Load RR data
    try:
        if source == "fit":
            rr_records = load_rr_from_fit(input_path)
            rr_source = "fit_hrv_messages"
        elif source == "polar_csv":
            rr_records = load_rr_from_csv(input_path)
            rr_source = "polar_csv"
        elif source == "txt":
            rr_records = load_rr_from_txt(input_path)
            rr_source = "txt"
        else:
            print(json.dumps({"error": f"Unknown source: {source}"}))
            sys.exit(1)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)

    if not rr_records:
        print(json.dumps({
            "error": "No RR intervals found in file.",
            "rr_source": rr_source,
            "rr_count": 0,
            "hint": (
                "FIT-file from Garmin 735XT via ANT+ does not contain hrv messages. "
                "Use Polar Beat or Fatmaxxer to export RR data as CSV."
            ),
        }))
        sys.exit(0)

    # Global DFA-alpha1 over full series
    all_rr = [r["rr_ms"] for r in rr_records]
    global_alpha = compute_dfa_alpha1(all_rr)

    # Windowed analysis
    windows = compute_windowed_dfa(
        rr_records,
        window_s=args.window_size,
        step_s=args.step,
        min_beats=args.min_beats,
    )

    # VT1 estimate
    vt1_bpm = estimate_vt1(windows)

    result: dict[str, Any] = {
        "dfa_alpha1": round(global_alpha, 4) if global_alpha is not None else None,
        "vt1_estimate_bpm": vt1_bpm,
        "rr_count": len(all_rr),
        "rr_source": rr_source,
        "windows": windows,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
