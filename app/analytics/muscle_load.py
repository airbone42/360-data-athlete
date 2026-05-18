"""Muscle load analytics — pure functions for fatigue calculation.

Formulas:
- e1RM: Brzycki (reps ≤10), Epley (reps >10)
- RPE→RIR: Zourdos convention (extended below RPE 6)
- Fatigue decay: exponential with τ = regen_hours / ln(4)
- Eccentric multiplier: 1.4 for eccentric_dominant exercises

References: Bompa 6th ed., Schoenfeld 2016, Zourdos et al. 2016,
            Paulsen et al. 2012, Behringer 2014, Kreher 2016
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

# ── Regen groups (hours) ────────────────────────────────────────────────────

REGEN_HOURS: dict[str, dict[str, float]] = {
    "small_dynamic": {"low": 24.0, "mid": 48.0, "high": 72.0},
    "small_tendon":  {"low": 36.0, "mid": 60.0, "high": 96.0},
    "medium":        {"low": 36.0, "mid": 60.0, "high": 84.0},
    "large":         {"low": 48.0, "mid": 72.0, "high": 96.0},
    "core_deep":     {"low": 24.0, "mid": 36.0, "high": 60.0},
    "plyo_cns":      {"low": 48.0, "mid": 72.0, "high": 120.0},
}

RPE_TIER_BOUNDS: dict[str, float] = {"low": 5.0, "mid": 7.0, "high": 10.0}

BODYWEIGHT_KG = 75.0
ECCENTRIC_MULTIPLIER = 1.4

# RPE → intensity fallback table (for band / unknown weight)
RPE_TO_INTENSITY: dict[int, float] = {
    3: 0.50, 4: 0.55, 5: 0.60, 6: 0.70, 7: 0.78, 8: 0.85, 9: 0.92, 10: 1.00,
}

# Muscle contribution by role
CONTRIBUTION: dict[str, float] = {
    "primary": 1.0,
    "secondary": 0.5,
    "stabilizer": 0.15,
}


# ── e1RM ────────────────────────────────────────────────────────────────────

def brzycki_e1rm(weight_kg: float, reps: float) -> float:
    """Brzycki formula — most accurate for reps 2–10."""
    if reps >= 37:
        return weight_kg
    return weight_kg * 36.0 / (37.0 - reps)


def epley_e1rm(weight_kg: float, reps: float) -> float:
    """Epley formula — fallback for reps > 10."""
    return weight_kg * (1.0 + reps / 30.0)


def estimate_e1rm(weight_kg: float, reps: float) -> float:
    """Select formula by rep range (switch point at 10)."""
    if reps <= 10:
        return brzycki_e1rm(weight_kg, reps)
    return epley_e1rm(weight_kg, reps)


# ── RPE utilities ────────────────────────────────────────────────────────────

def rpe_to_rir(rpe: float) -> float:
    """Reps in Reserve from RPE (Zourdos extended).

    Zourdos linear for RPE ≥6; below 6 the relationship flattens
    (warm-up / easy sets).
    """
    if rpe >= 6.0:
        return max(0.0, 10.0 - rpe)
    return 5.0 + (6.0 - rpe)


def rpe_to_tier(rpe: float | None) -> Literal["low", "mid", "high"]:
    """Map RPE to recovery tier."""
    if rpe is None:
        return "mid"
    if rpe <= RPE_TIER_BOUNDS["low"]:
        return "low"
    if rpe <= RPE_TIER_BOUNDS["mid"]:
        return "mid"
    return "high"


def rpe_multiplier(rpe: float) -> float:
    """Volume load multiplier based on RPE (effort scaling)."""
    if rpe <= 6.0:
        return 1.0
    return 1.0 + 0.15 * (rpe - 6.0)


# ── Fatigue calculation ─────────────────────────────────────────────────────

@dataclass
class SetResult:
    exercise_key: str
    weight_kg: float | None
    reps: float | None
    duration_s: float | None
    rpe: float | None
    per_side: bool = False
    load_mode: str = "free_weight"
    lever_factor: float = 1.0
    eccentric_dominant: bool = False
    e1rm_override: float | None = None


@dataclass
class MuscleEntry:
    muscle: str
    intensity: float
    role: str = "primary"


@dataclass
class SessionMuscleLoad:
    muscle: str
    fatigue_contribution: float
    rpe_peak: float
    tier: str
    sets_count: int = 0


def effective_weight(result: SetResult) -> float | None:
    """Return effective weight in kg, accounting for bodyweight leverage."""
    if result.weight_kg is not None and result.weight_kg > 0:
        return result.weight_kg
    if result.load_mode == "bodyweight":
        return BODYWEIGHT_KG * result.lever_factor
    return None


def compute_set_fatigue(
    result: SetResult,
    muscle_entry: MuscleEntry,
    e1rm: float | None,
) -> float:
    """Compute fatigue contribution for one set on one muscle.

    Formula:
        load = effective_reps × intensity × muscle_contribution
        fatigue = load × rpe_mult × eccentric_mult
    """
    contribution = CONTRIBUTION.get(muscle_entry.role, 0.5)
    rpe = result.rpe or 6.0

    # ── Isometric (holds) ──────────────────────────────────────────────────
    if result.load_mode in ("isometric", "grip_device") and result.duration_s:
        intensity = RPE_TO_INTENSITY.get(int(min(rpe, 10)), 0.7)
        load = (result.duration_s / 30.0) * intensity * contribution
        return load * rpe_multiplier(rpe) * (ECCENTRIC_MULTIPLIER if result.eccentric_dominant else 1.0)

    # ── Endurance sessions handled in aggregate_endurance_load ─────────────
    if result.load_mode == "endurance":
        return 0.0

    if result.reps is None or result.reps == 0:
        return 0.0

    # ── Standard sets (free_weight / bodyweight / band) ───────────────────
    eff_w = effective_weight(result)

    if eff_w is not None and e1rm is not None and e1rm > 0:
        # Adjust reps by RIR for proper e1RM scaling
        rir = rpe_to_rir(rpe)
        adjusted_reps = result.reps + rir
        # Use adjusted reps for intensity calculation
        adj_e1rm = estimate_e1rm(eff_w, adjusted_reps)
        intensity = eff_w / adj_e1rm if adj_e1rm > 0 else 0.7
        intensity = min(intensity, 1.1)
    elif result.load_mode == "band" or eff_w is None:
        intensity = RPE_TO_INTENSITY.get(int(min(rpe, 10)), 0.7)
    else:
        intensity = 0.65

    effective_reps = result.reps * (2 if result.per_side else 1)
    muscle_contribution_val = muscle_entry.intensity * contribution
    load = effective_reps * intensity * muscle_contribution_val

    eccentric = ECCENTRIC_MULTIPLIER if result.eccentric_dominant else 1.0
    return load * rpe_multiplier(rpe) * eccentric


def aggregate_session_load(
    sets: list[SetResult],
    exercise_mappings: dict,
    muscle_db: dict,
) -> dict[str, SessionMuscleLoad]:
    """Aggregate fatigue from all sets across all muscles.

    Returns dict of muscle_id → SessionMuscleLoad.
    """
    muscle_loads: dict[str, SessionMuscleLoad] = {}
    e1rm_state: dict[str, float] = {}

    for result in sets:
        mapping = exercise_mappings.get(result.exercise_key)
        if mapping is None or mapping.get("_type") == "endurance":
            continue

        is_isometric = result.load_mode in ("isometric", "grip_device")

        # e1RM per exercise (not per muscle)
        if not is_isometric and result.weight_kg and result.reps:
            rir = rpe_to_rir(result.rpe or 6.0)
            adj_reps = result.reps + rir
            new_e1rm = estimate_e1rm(result.weight_kg, adj_reps)
            prev = e1rm_state.get(result.exercise_key)
            # EMA α=0.3 to smooth outliers
            e1rm_state[result.exercise_key] = (
                0.3 * new_e1rm + 0.7 * prev if prev else new_e1rm
            )

        e1rm = e1rm_state.get(result.exercise_key) or result.e1rm_override

        all_muscles: list[tuple[str, float, str]] = (
            [(m["muscle"], m["intensity"], "primary") for m in mapping.get("primary", [])] +
            [(m["muscle"], m["intensity"], "secondary") for m in mapping.get("secondary", [])] +
            [(m["muscle"], m["intensity"], "stabilizer") for m in mapping.get("stabilizer", [])]
        )

        for muscle_id, intensity, role in all_muscles:
            entry = MuscleEntry(muscle=muscle_id, intensity=intensity, role=role)
            fatigue = compute_set_fatigue(result, entry, e1rm)
            if fatigue == 0:
                continue

            rpe_val = result.rpe or 6.0
            if muscle_id not in muscle_loads:
                muscle_loads[muscle_id] = SessionMuscleLoad(
                    muscle=muscle_id,
                    fatigue_contribution=0.0,
                    rpe_peak=rpe_val,
                    tier=rpe_to_tier(result.rpe),
                    sets_count=0,
                )
            ml = muscle_loads[muscle_id]
            ml.fatigue_contribution += fatigue
            ml.rpe_peak = max(ml.rpe_peak, rpe_val)
            ml.tier = rpe_to_tier(ml.rpe_peak)
            ml.sets_count += 1

    return muscle_loads


def aggregate_endurance_load(
    zone_minutes: dict[str, float],
    modality: str,
    elevation_loss_m: float,
    exercise_mappings: dict,
) -> dict[str, SessionMuscleLoad]:
    """Aggregate cardio fatigue from zone-based endurance session.

    zone_minutes: e.g. {"Z1": 5, "Z2": 30, "Z3": 10, "Z4": 8, "Z5": 2}
    Returns dict of muscle_id → SessionMuscleLoad (cardio variant).
    """
    zone_to_key: dict[str, str] = {
        "Z1": f"{modality}_z1_z2",
        "Z2": f"{modality}_z1_z2",
        "Z3": f"{modality}_z3",
        "Z4": f"{modality}_z4_z5",
        "Z5": f"{modality}_z4_z5",
    }

    muscle_loads: dict[str, SessionMuscleLoad] = {}

    for zone, minutes in zone_minutes.items():
        if minutes <= 0:
            continue
        mapping_key = zone_to_key.get(zone)
        if not mapping_key:
            continue
        mapping = exercise_mappings.get(mapping_key)
        if not mapping:
            continue

        factor = mapping.get("effort_factor_per_min", 0.015)
        # Approximate RPE for zone
        zone_rpe: dict[str, float] = {"Z1": 4.0, "Z2": 5.0, "Z3": 6.5, "Z4": 8.0, "Z5": 9.0}
        rpe = zone_rpe.get(zone, 6.0)

        all_muscles = (
            [(m["muscle"], m["intensity"], "primary") for m in mapping.get("primary", [])] +
            [(m["muscle"], m["intensity"], "secondary") for m in mapping.get("secondary", [])] +
            [(m["muscle"], m["intensity"], "stabilizer") for m in mapping.get("stabilizer", [])]
        )
        for muscle_id, intensity, role in all_muscles:
            contribution = CONTRIBUTION.get(role, 0.5)
            load = minutes * factor * intensity * contribution

            if muscle_id not in muscle_loads:
                muscle_loads[muscle_id] = SessionMuscleLoad(
                    muscle=muscle_id,
                    fatigue_contribution=0.0,
                    rpe_peak=rpe,
                    tier=rpe_to_tier(rpe),
                    sets_count=0,
                )
            ml = muscle_loads[muscle_id]
            ml.fatigue_contribution += load
            ml.rpe_peak = max(ml.rpe_peak, rpe)
            ml.tier = rpe_to_tier(ml.rpe_peak)
            ml.sets_count += 1

    # Downhill modifier (eccentric quads)
    if elevation_loss_m > 100 and modality == "run":
        downhill_mapping = exercise_mappings.get("run_downhill")
        if downhill_mapping:
            loss_units = elevation_loss_m / 100.0
            base_factor = downhill_mapping.get("effort_factor_per_100m_loss", 0.08)
            rpe = 7.0
            for m in downhill_mapping.get("primary", []):
                muscle_id = m["muscle"]
                load = loss_units * base_factor * m["intensity"] * ECCENTRIC_MULTIPLIER
                if muscle_id not in muscle_loads:
                    muscle_loads[muscle_id] = SessionMuscleLoad(
                        muscle=muscle_id,
                        fatigue_contribution=0.0,
                        rpe_peak=rpe,
                        tier="mid",
                        sets_count=0,
                    )
                ml = muscle_loads[muscle_id]
                ml.fatigue_contribution += load
                ml.rpe_peak = max(ml.rpe_peak, rpe)

    return muscle_loads


# ── Decay / Recovery ─────────────────────────────────────────────────────────

def decay_tau(regen_hours: float) -> float:
    """Time constant τ for exponential decay.

    Chosen so that fatigue_pct(regen_hours) ≈ 25%  →  τ = regen/ln(4).
    """
    return regen_hours / math.log(4.0)


def fatigue_pct_remaining(hours_since: float, regen_hours: float) -> float:
    """Remaining fatigue percentage (0–100)."""
    tau = decay_tau(regen_hours)
    return 100.0 * math.exp(-hours_since / tau)


def next_optimal_hours(regen_hours: float, target_pct: float = 10.0) -> float:
    """Hours until fatigue drops below target_pct (superkompensation window).

    Default 10% residual = ready to train again.
    """
    tau = decay_tau(regen_hours)
    return tau * math.log(100.0 / target_pct)


def regen_hours_for_muscle(muscle_db: dict, muscle_id: str, tier: str) -> float:
    """Look up regen hours for a muscle from the DB dict."""
    regen_group = muscle_db.get(muscle_id, {}).get("regen_group", "medium")
    return REGEN_HOURS.get(regen_group, REGEN_HOURS["medium"]).get(tier, 60.0)
