"""HR zone formatting utilities shared across graphs.

The context hands the coach finished, labelled zones per sport so nothing has
to be estimated: ``Run (LTHR 166 bpm, HRmax 176 bpm): Z1 (Recovery): 1–125 bpm
| …`` and, when intervals.icu carries a ride profile, a second ``Ride (…)``
line. LTHR and max HR come from the same sportSettings entry as the zones.
"""

from __future__ import annotations

ZONE_NAMES = ["Recovery", "Endurance", "Aerobic", "Threshold", "VO2max"]
HR_ZONES_UNAVAILABLE = "HR zones not available"

# Sports surfaced in context.hrZones, in display order. The key is the label,
# the value the intervals.icu activity types that select the sportSettings entry.
HR_ZONE_SPORTS: dict[str, tuple[str, ...]] = {
    "Run": ("Run", "VirtualRun", "TrailRun"),
    "Ride": ("Ride", "VirtualRide", "GravelRide", "MountainBikeRide"),
}


def _as_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def zone_name(i: int, names: list[str] | None = None) -> str:
    """Name of zone ``i`` (0-based): intervals.icu's own name when given."""
    if names and i < len(names) and str(names[i]).strip():
        return str(names[i]).strip()
    return ZONE_NAMES[i] if i < len(ZONE_NAMES) else f"Zone {i+1}"


def format_hr_zones(bounds: list[int | None], names: list[str] | None = None) -> str:
    """Format HR zones where each bound is the upper limit of that zone.

    A bound of 0 / None is shown as ``not set`` instead of being dropped: a
    silently missing zone shifts every later zone name by one. ``names`` are
    the sport's ``hr_zone_names`` from intervals.icu (a 7-zone ride model does
    not fit the 5 default names).
    """
    if len(bounds) < 1:
        return HR_ZONES_UNAVAILABLE
    parts = []
    prev: int | None = None
    for i, raw in enumerate(bounds):
        name = zone_name(i, names)
        upper = _as_int(raw)
        if not upper:
            parts.append(f"Z{i+1} ({name}): not set in intervals.icu")
            continue
        lower = prev + 1 if prev else 1
        parts.append(f"Z{i+1} ({name}): {lower}–{upper} bpm")
        prev = upper
    return " | ".join(parts)


def sport_hr_settings(athlete_settings: dict | None, sport: str) -> dict | None:
    """``{"lthr", "max_hr", "bounds", "names"}`` for one sport, or None.

    ``sport`` is an intervals.icu activity type ("Run", "VirtualRide", …) or a
    key of ``HR_ZONE_SPORTS``. ``bounds`` keeps 0 entries (see format_hr_zones);
    trailing zeros are trimmed because intervals.icu pads unused zones.
    """
    types = set(HR_ZONE_SPORTS.get(sport, (sport,)))
    for entry in (athlete_settings or {}).get("sportSettings") or []:
        if not types & set(entry.get("types") or []):
            continue
        bounds = [_as_int(z) or 0 for z in (entry.get("hr_zones") or [])]
        while bounds and bounds[-1] == 0:
            bounds.pop()
        names = [str(n) for n in (entry.get("hr_zone_names") or [])]
        return {
            "lthr": _as_int(entry.get("lthr")),
            "max_hr": _as_int(entry.get("max_hr")),
            "bounds": bounds,
            "names": names if len(names) >= len(bounds) else None,
        }
    return None


def format_sport_hr_zones(athlete_settings: dict | None) -> str:
    """One labelled line per sport with HR zones in intervals.icu (Run first)."""
    lines: list[str] = []
    for label in HR_ZONE_SPORTS:
        s = sport_hr_settings(athlete_settings, label)
        if not s or not any(s["bounds"]):
            continue
        meta = [
            f"LTHR {s['lthr']} bpm" if s["lthr"] else "LTHR not set",
            f"HRmax {s['max_hr']} bpm" if s["max_hr"] else "HRmax not set",
        ]
        lines.append(
            f"{label} ({', '.join(meta)}): {format_hr_zones(s['bounds'], s['names'])}"
        )
    return "\n".join(lines) if lines else HR_ZONES_UNAVAILABLE


def extract_run_hr_bounds(athlete_settings: dict) -> list[int]:
    """Run zone upper bounds (legacy helper; zero entries are dropped here)."""
    s = sport_hr_settings(athlete_settings, "Run")
    return [b for b in (s["bounds"] if s else []) if b]
