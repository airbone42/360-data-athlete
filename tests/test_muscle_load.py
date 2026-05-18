"""Unit tests for app/analytics/muscle_load.py"""
import math
import pytest
from app.analytics.muscle_load import (
    brzycki_e1rm,
    epley_e1rm,
    estimate_e1rm,
    rpe_to_rir,
    rpe_to_tier,
    rpe_multiplier,
    fatigue_pct_remaining,
    decay_tau,
    next_optimal_hours,
    compute_set_fatigue,
    SetResult,
    MuscleEntry,
    ECCENTRIC_MULTIPLIER,
)


# ── e1RM ────────────────────────────────────────────────────────────────────

def test_brzycki_5_reps():
    # 100kg × 5 reps → 36/(37-5) = 36/32 = 1.125 → 112.5
    result = brzycki_e1rm(100.0, 5.0)
    assert abs(result - 112.5) < 0.5

def test_brzycki_1_rep():
    # 1 rep → Brzycki: 36/36 = 1.0 → weight itself
    result = brzycki_e1rm(100.0, 1.0)
    assert abs(result - 100.0) < 0.1

def test_epley_15_reps():
    # 50kg × 15 → 50 × (1 + 15/30) = 50 × 1.5 = 75
    result = epley_e1rm(50.0, 15.0)
    assert abs(result - 75.0) < 0.1

def test_estimate_e1rm_switches_at_10():
    # At reps=10, both formulas are used — just check routing
    r10 = estimate_e1rm(60.0, 10.0)
    r11 = estimate_e1rm(60.0, 11.0)
    # Epley(60,11) = 60*(1+11/30) = 60*1.367 = 82
    assert r11 == pytest.approx(epley_e1rm(60.0, 11.0))
    assert r10 == pytest.approx(brzycki_e1rm(60.0, 10.0))

def test_brzycki_high_reps_capped():
    # reps=36 → brzycki: 36/(37-36)=36 → 36×weight
    # reps=37 → returns weight (guard)
    result_37 = brzycki_e1rm(10.0, 37.0)
    assert result_37 == 10.0  # guard returns weight


# ── RPE utilities ────────────────────────────────────────────────────────────

def test_rpe_to_rir_linear_above_6():
    assert rpe_to_rir(10.0) == pytest.approx(0.0)
    assert rpe_to_rir(8.0) == pytest.approx(2.0)
    assert rpe_to_rir(6.0) == pytest.approx(4.0)

def test_rpe_to_rir_below_6_flattens():
    rir_5 = rpe_to_rir(5.0)
    rir_4 = rpe_to_rir(4.0)
    assert rir_5 == pytest.approx(6.0)
    assert rir_4 == pytest.approx(7.0)
    # Below 6 should give more RIR than exact linear
    assert rir_4 > rpe_to_rir(6.0)

def test_rpe_to_tier():
    assert rpe_to_tier(4.0) == "low"
    assert rpe_to_tier(5.0) == "low"
    assert rpe_to_tier(6.0) == "mid"
    assert rpe_to_tier(7.0) == "mid"
    assert rpe_to_tier(8.0) == "high"
    assert rpe_to_tier(None) == "mid"

def test_rpe_multiplier_below_6():
    assert rpe_multiplier(5.0) == pytest.approx(1.0)
    assert rpe_multiplier(6.0) == pytest.approx(1.0)

def test_rpe_multiplier_above_6():
    # RPE 8 → 1.0 + 0.15*(8-6) = 1.3
    assert rpe_multiplier(8.0) == pytest.approx(1.3)
    # RPE 9 → 1.0 + 0.15*3 = 1.45
    assert rpe_multiplier(9.0) == pytest.approx(1.45)


# ── Decay ────────────────────────────────────────────────────────────────────

def test_fatigue_at_zero_hours():
    assert fatigue_pct_remaining(0.0, 48.0) == pytest.approx(100.0)

def test_fatigue_at_regen_hours():
    # At t=regen_hours: exp(-regen/(regen/ln4)) = exp(-ln4) = 1/4 = 25%
    pct = fatigue_pct_remaining(48.0, 48.0)
    assert abs(pct - 25.0) < 0.5

def test_fatigue_long_decay():
    # After 3× regen hours very little remains
    pct = fatigue_pct_remaining(144.0, 48.0)
    assert pct < 5.0

def test_decay_tau_positive():
    tau = decay_tau(48.0)
    assert tau > 0

def test_next_optimal_hours_default():
    # 10% residual target: should be > regen_hours
    hours = next_optimal_hours(48.0, target_pct=10.0)
    pct_at_that_time = fatigue_pct_remaining(hours, 48.0)
    assert abs(pct_at_that_time - 10.0) < 1.0


# ── compute_set_fatigue ───────────────────────────────────────────────────────

def test_fatigue_increases_with_rpe():
    entry = MuscleEntry(muscle="biceps_brachii", intensity=1.0, role="primary")
    low_rpe = SetResult(
        exercise_key="kurzhantel_curl", weight_kg=20.0, reps=10.0,
        duration_s=None, rpe=5.0, load_mode="free_weight"
    )
    high_rpe = SetResult(
        exercise_key="kurzhantel_curl", weight_kg=20.0, reps=10.0,
        duration_s=None, rpe=9.0, load_mode="free_weight"
    )
    e1rm = estimate_e1rm(20.0, 10.0)
    fat_low = compute_set_fatigue(low_rpe, entry, e1rm)
    fat_high = compute_set_fatigue(high_rpe, entry, e1rm)
    assert fat_high > fat_low

def test_eccentric_multiplier_applied():
    entry = MuscleEntry(muscle="biceps_femoris_long", intensity=1.0, role="primary")
    base = SetResult(
        exercise_key="single_leg_rdl", weight_kg=15.0, reps=8.0,
        duration_s=None, rpe=7.0, load_mode="free_weight", eccentric_dominant=False
    )
    eccentric = SetResult(
        exercise_key="single_leg_rdl", weight_kg=15.0, reps=8.0,
        duration_s=None, rpe=7.0, load_mode="free_weight", eccentric_dominant=True
    )
    e1rm = estimate_e1rm(15.0, 8.0)
    fat_base = compute_set_fatigue(base, entry, e1rm)
    fat_ecc = compute_set_fatigue(eccentric, entry, e1rm)
    assert abs(fat_ecc / fat_base - ECCENTRIC_MULTIPLIER) < 0.01

def test_isometric_non_zero():
    entry = MuscleEntry(muscle="flexor_digitorum_superficialis", intensity=1.0, role="primary")
    result = SetResult(
        exercise_key="farmer_hold_kb", weight_kg=25.0, reps=None,
        duration_s=45.0, rpe=7.0, load_mode="isometric"
    )
    fat = compute_set_fatigue(result, entry, None)
    assert fat > 0

def test_band_uses_rpe_intensity():
    entry = MuscleEntry(muscle="extensor_digitorum", intensity=1.0, role="primary")
    result = SetResult(
        exercise_key="finger_extensor_band", weight_kg=None, reps=15.0,
        duration_s=None, rpe=6.0, load_mode="band"
    )
    fat = compute_set_fatigue(result, entry, None)
    assert fat > 0

def test_secondary_less_than_primary():
    primary = MuscleEntry(muscle="biceps_brachii", intensity=1.0, role="primary")
    secondary = MuscleEntry(muscle="brachioradialis", intensity=1.0, role="secondary")
    result = SetResult(
        exercise_key="kurzhantel_curl", weight_kg=15.0, reps=10.0,
        duration_s=None, rpe=7.0, load_mode="free_weight"
    )
    e1rm = estimate_e1rm(15.0, 10.0)
    fat_p = compute_set_fatigue(result, primary, e1rm)
    fat_s = compute_set_fatigue(result, secondary, e1rm)
    assert fat_p > fat_s
