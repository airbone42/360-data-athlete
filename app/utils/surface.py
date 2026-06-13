"""Canonical surface vocabulary — shared by plan validator (R003) and shoe advisor.

The workout ``surface`` field drives the shoe advisor (terrain
classification and shoe recommendation). Canonical tokens follow the
workout-JSON contract: ``asphalt | forest-path | trail | track |
treadmill``. Historical plans may carry legacy spellings (e.g. the German
``forstweg``); those stay accepted on read via the alias table and map to
the same classification.
"""
from __future__ import annotations

# Canonical surface tokens (workout JSON contract).
CANONICAL_SURFACES = frozenset(
    {"asphalt", "forest-path", "trail", "track", "treadmill"}
)

# Read-aliases: legacy spellings → canonical token. New plans MUST emit
# canonical tokens; aliases keep historical workouts classifying identically.
SURFACE_ALIASES: dict[str, str] = {
    "forstweg": "forest-path",
    "weichboden": "trail",
    "bahn": "track",
}


def normalize_surface(raw: str | None) -> str | None:
    """Return the canonical surface token for ``raw``, or None if unknown.

    Accepts canonical tokens as-is (case-insensitive) and maps legacy
    aliases to their canonical equivalent. Empty/None input → None.
    """
    if not raw:
        return None
    s = raw.strip().lower()
    if s in CANONICAL_SURFACES:
        return s
    return SURFACE_ALIASES.get(s)
