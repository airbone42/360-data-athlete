"""Sport registry — the single place that knows what each workout type is.

Before this module, ~15 call sites carried their own partial answer to
"which types are endurance / cardio / bike-like, and does a virtual
variant count?" (CARDIO_TYPES, ENDURANCE_TYPES, BIKE_TYPES,
_RUN_RIDE_TYPES, _ENDURANCE_TYPES, TYPE_EQUIV, …) — and they disagreed
in subtle ways (a Rønnestad 30/15 logged as VirtualRide was invisible to
the type history until its equivalence map learned about virtual types).

The registry keys on the four plannable workout types
(`app/schemas/workout.py::WorkoutType`) plus recorded-only types that
appear in the activity history (e.g. Swim). Helpers answer the recurring
questions; derived constants keep existing call sites terse.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Sport:
    """One plannable or recorded sport type."""

    type: str
    #: device/recording variants that count as this sport in histories
    virtual_types: frozenset[str] = field(default_factory=frozenset)
    #: sustained cardio work (zone distribution, CTL-relevant)
    endurance: bool = False
    #: transmits ground impact (bone/tendon load — run-streak logic)
    impact: bool = False
    #: agent that structures this workout type (None → not plannable)
    specialist: str | None = None
    #: which zone definition paces it: "run_hr" | "bike_hr" | None
    zone_source: str | None = None
    #: plannable via the daily-planner directive (WorkoutType literal)
    plannable: bool = True

    @property
    def all_types(self) -> frozenset[str]:
        """Canonical type + all virtual variants."""
        return frozenset({self.type}) | self.virtual_types


SPORTS: dict[str, Sport] = {
    s.type: s
    for s in (
        Sport(
            type="Run",
            virtual_types=frozenset({"VirtualRun", "TrailRun"}),
            endurance=True,
            impact=True,
            specialist="specialist-endurance",
            zone_source="run_hr",
        ),
        Sport(
            type="Ride",
            virtual_types=frozenset({"VirtualRide"}),
            endurance=True,
            specialist="specialist-endurance",
            zone_source="bike_hr",
        ),
        Sport(
            type="WeightTraining",
            specialist="specialist-complementary",
        ),
        Sport(
            type="Workout",
            specialist="specialist-complementary",  # ninja tag overrides
        ),
        Sport(
            type="Swim",
            virtual_types=frozenset({"OpenWaterSwim", "SwimPool"}),
            endurance=True,
            plannable=False,
        ),
    )
}


def canonical_type(activity_type: str | None) -> str | None:
    """Map a recorded type (incl. virtual variants) to its canonical sport.

    Unknown types return None — callers decide whether that is an error.
    """
    if not activity_type:
        return None
    for sport in SPORTS.values():
        if activity_type in sport.all_types:
            return sport.type
    return None


def all_types_for(canonical: str) -> frozenset[str]:
    """Canonical type + virtual variants ("Ride" → {"Ride", "VirtualRide"})."""
    sport = SPORTS.get(canonical)
    return sport.all_types if sport else frozenset({canonical})


def is_endurance(activity_type: str | None) -> bool:
    c = canonical_type(activity_type)
    return bool(c and SPORTS[c].endurance)


def is_impact(activity_type: str | None) -> bool:
    c = canonical_type(activity_type)
    return bool(c and SPORTS[c].impact)


# ── Derived constants (drop-in for the historical per-module copies) ─────────

#: plannable workout types, in the order the parser validates them
VALID_TYPES: list[str] = [s.type for s in SPORTS.values() if s.plannable]

#: canonical endurance types the planner can schedule ({"Run", "Ride"})
ENDURANCE_TYPES: frozenset[str] = frozenset(
    s.type for s in SPORTS.values() if s.endurance and s.plannable
)

#: every recorded type that counts as sustained cardio (incl. virtual + Swim)
CARDIO_TYPES: frozenset[str] = frozenset().union(
    *(s.all_types for s in SPORTS.values() if s.endurance)
)

#: bike-like recorded types ({"Ride", "VirtualRide"})
BIKE_TYPES: frozenset[str] = all_types_for("Ride")

#: run-like recorded types ({"Run", "VirtualRun"})
RUN_TYPES: frozenset[str] = all_types_for("Run")

#: recorded-type → canonical equivalence map for type histories
TYPE_EQUIV: dict[str, frozenset[str]] = {
    s.type: s.all_types for s in SPORTS.values()
}
