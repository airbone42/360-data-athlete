"""Zone distribution: 7-zone models keep Z6/Z7, mixed windows get a per-sport split."""
from app.analytics.zones import _compute_zone_distribution


def _act(t, zones, d="2026-01-05"):
    return {"type": t, "icu_hr_zone_times": zones, "moving_time": sum(zones),
            "start_date_local": f"{d}T08:00:00"}


def test_seven_zone_ride_folds_z6_z7_into_top_bucket():
    out = _compute_zone_distribution([_act("Ride", [0, 600, 0, 0, 0, 300, 300])])
    assert "Z5+: 50%" in out
    assert "Z2: 50%" in out


def test_five_zone_data_keeps_plain_z5_label():
    out = _compute_zone_distribution([_act("Run", [600, 600, 0, 0, 0])])
    assert "Z5:" in out and "Z5+" not in out
    assert "Run:" not in out  # single sport: unchanged


def test_ride_time_stays_in_ride_zone_in_mixed_window():
    # Ride HR is Z2 on ride zones (intervals.icu already classified it);
    # it must not be re-bucketed as Run Z1.
    out = _compute_zone_distribution([
        _act("Run", [1200, 0, 0, 0, 0]),
        _act("VirtualRide", [0, 1200, 0, 0, 0]),
    ])
    assert out.startswith("Z1: 50% | Z2: 50%")
    assert "| Run: Z1: 100% Z2: 0%" in out
    assert "| Ride: Z1: 0% Z2: 100%" in out
