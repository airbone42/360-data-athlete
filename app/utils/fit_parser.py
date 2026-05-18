"""Parse FIT files using fitparse and extract lap metrics."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_fit_laps(fit_path: Path) -> list[dict[str, Any]]:
    """Parse a FIT file and extract lap data with metrics.

    Returns a list of dicts with one entry per lap.
    """
    try:
        import fitparse  # type: ignore[import]
    except ImportError as e:
        raise ImportError("fitparse is required: pip install fitparse") from e

    fitfile = fitparse.FitFile(str(fit_path))
    laps: list[dict[str, Any]] = []

    for i, record in enumerate(fitfile.get_messages("lap")):
        data: dict[str, Any] = {"lap_index": i + 1}

        for field in record:
            name = field.name
            value = field.value

            if name == "total_timer_time":
                data["duration_s"] = round(value) if value is not None else None
            elif name == "total_distance":
                data["distance_m"] = round(value, 1) if value is not None else None
            elif name == "enhanced_avg_speed":
                data["avg_speed"] = value  # m/s
            elif name == "enhanced_max_speed":
                data["max_speed"] = value  # m/s
            elif name == "avg_heart_rate":
                data["avg_heart_rate"] = value
            elif name == "min_heart_rate":
                data["min_heart_rate"] = value
            elif name == "max_heart_rate":
                data["max_heart_rate"] = value
            elif name == "avg_cadence":
                # FIT cadence is steps/min for one foot → multiply by 2 for spm
                data["avg_cadence"] = value * 2 if value is not None else None
            elif name == "avg_stance_time_balance":
                data["avg_stance_balance"] = round(value, 1) if value is not None else None
            elif name == "avg_vertical_oscillation":
                # FIT stores in mm
                data["avg_vertical_osc"] = round(value, 1) if value is not None else None
            elif name == "avg_step_length":
                data["avg_step_length"] = round(value, 1) if value is not None else None
            elif name == "total_ascent":
                data["total_ascent"] = value
            elif name == "start_position_lat":
                data["start_lat"] = _semicircles_to_degrees(value)
            elif name == "start_position_long":
                data["start_lon"] = _semicircles_to_degrees(value)
            elif name == "end_position_lat":
                data["end_lat"] = _semicircles_to_degrees(value)
            elif name == "end_position_long":
                data["end_lon"] = _semicircles_to_degrees(value)

        # Calculate pace min/km from avg_speed (m/s)
        avg_speed = data.get("avg_speed")
        if avg_speed and avg_speed > 0:
            data["pace_min_km"] = round(1000 / avg_speed / 60, 2)
        else:
            data["pace_min_km"] = None

        # Calculate midpoint for overpass query
        start_lat = data.get("start_lat")
        start_lon = data.get("start_lon")
        end_lat = data.get("end_lat")
        end_lon = data.get("end_lon")
        if start_lat and start_lon and end_lat and end_lon:
            data["mid_lat"] = (start_lat + end_lat) / 2
            data["mid_lon"] = (start_lon + end_lon) / 2
        elif start_lat and start_lon:
            data["mid_lat"] = start_lat
            data["mid_lon"] = start_lon

        laps.append(data)

    return laps


def parse_fit_records(fit_path: Path) -> list[dict]:
    """Parse per-second FIT records with running dynamics.

    Returns list of dicts with: timestamp, heart_rate, speed, cadence,
    lat, lon, stance_time, vertical_oscillation, step_length.
    """
    try:
        import fitparse  # type: ignore[import]
    except ImportError as e:
        raise ImportError("fitparse is required: pip install fitparse") from e

    fitfile = fitparse.FitFile(str(fit_path))
    records: list[dict] = []

    for record in fitfile.get_messages("record"):
        data: dict = {}
        for field in record:
            name = field.name
            value = field.value
            if name == "timestamp":
                data["timestamp"] = value
            elif name == "heart_rate":
                data["heart_rate"] = value
            elif name == "enhanced_speed":
                data["speed"] = value  # m/s
            elif name == "cadence":
                data["cadence"] = value * 2 if value is not None else None
            elif name == "position_lat":
                data["lat"] = _semicircles_to_degrees(value)
            elif name == "position_long":
                data["lon"] = _semicircles_to_degrees(value)
            elif name == "stance_time":
                data["stance_time"] = value  # ms
            elif name == "vertical_oscillation":
                data["vertical_oscillation"] = value  # mm
            elif name == "step_length":
                data["step_length"] = value  # mm
        if data.get("timestamp") is not None:
            records.append(data)

    return records


def extract_rr_intervals(fit_path: Path) -> list[dict[str, float]]:
    """Extract RR intervals from a FIT file.

    Checks two sources in order:
      1. `hrv` messages — cumulative `time[]` array converted to delta RR in ms.
         Present on devices that record beat-to-beat data (modern Garmin watches
         with native HRV-message support, e.g. Fenix 6+ / FR945+ class).
      2. `record` messages with a `heart_rate_variability` field (rare fallback,
         used by some third-party ANT+ bridges).

    Older ANT+ watches without native HRV-message support typically do NOT
    store `hrv` messages even when paired with an external HRM strap — only
    epoch-level HR in `record` messages. In that case an empty list is
    returned and RR data must be sourced from the chest strap directly
    (Polar H10 or equivalent via Polar Beat, Fatmaxxer, Elite HRV, …).

    Args:
        fit_path: Path to the .fit file.

    Returns:
        List of {"timestamp_s": float, "rr_ms": float}, sorted by timestamp.
        Returns empty list if no RR data is present.
    """
    try:
        import fitparse  # type: ignore[import]
    except ImportError as e:
        raise ImportError("fitparse is required: pip install fitparse") from e

    fitfile = fitparse.FitFile(str(fit_path))
    rr_records: list[dict[str, float]] = []
    cumulative_s: float = 0.0

    # Source 1: hrv messages
    for msg in fitfile.get_messages("hrv"):
        times = msg.get_value("time")
        if times is None:
            continue
        if not isinstance(times, (list, tuple)):
            times = [times]
        for interval_s in times:
            if interval_s is None:
                continue
            rr_ms = interval_s * 1000.0
            # Physiological plausibility filter: 300–2000 ms (30–200 bpm)
            if 300.0 <= rr_ms <= 2000.0:
                rr_records.append({"timestamp_s": cumulative_s, "rr_ms": round(rr_ms, 2)})
            cumulative_s += interval_s

    if rr_records:
        return rr_records

    # Source 2: record messages with heart_rate_variability field
    for msg in fitfile.get_messages("record"):
        ts = msg.get_value("timestamp")
        hrv_val = msg.get_value("heart_rate_variability")
        if hrv_val is not None and ts is not None:
            ts_s = ts.timestamp() if hasattr(ts, "timestamp") else float(ts)
            rr_ms = float(hrv_val)
            if 300.0 <= rr_ms <= 2000.0:
                rr_records.append({"timestamp_s": ts_s, "rr_ms": round(rr_ms, 2)})

    return rr_records


def _semicircles_to_degrees(value: int | None) -> float | None:
    if value is None:
        return None
    return value * (180.0 / 2**31)
