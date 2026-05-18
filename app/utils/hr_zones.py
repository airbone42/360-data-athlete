"""HR zone formatting utilities shared across graphs."""

from __future__ import annotations

ZONE_NAMES = ["Recovery", "Endurance", "Aerobic", "Threshold", "VO2max"]


def format_hr_zones(bounds: list[int]) -> str:
    """Format HR zones where each bound is the upper limit of that zone."""
    if len(bounds) < 1:
        return "HR zones not available"
    parts = []
    for i, upper in enumerate(bounds):
        name = ZONE_NAMES[i] if i < len(ZONE_NAMES) else f"Zone {i+1}"
        lower = bounds[i - 1] + 1 if i > 0 else 1
        parts.append(f"Z{i+1} ({name}): {lower}–{upper} bpm")
    return " | ".join(parts)


def extract_run_hr_bounds(athlete_settings: dict) -> list[int]:
    for sport in (athlete_settings.get("sportSettings") or []):
        if "Run" in (sport.get("types") or []):
            return [int(z) for z in (sport.get("hr_zones") or []) if z]
    return []
