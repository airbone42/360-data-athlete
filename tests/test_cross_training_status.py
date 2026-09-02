"""Cross-training visibility line in planningConstraints.

The regression this guards: a bike used to reach the planner only through
the weekly hard-stimulus balance, so on every day a hard bike stimulus was
wrong the modality vanished from the plan instead of falling back to its
easy form. The line must therefore be emitted even when nothing is overdue.
"""

from datetime import date

from app.graphs.sub_athlete_context.context_builder import (
    _compute_cross_training_status,
)


TODAY = date(2026, 9, 2)


def _act(d: str, typ: str, name: str = "") -> dict:
    return {"start_date_local": f"{d}T09:00:00", "type": typ, "name": name}


def test_emits_line_even_when_a_ride_is_recent():
    """No cadence, no threshold — the line is unconditional."""
    out = _compute_cross_training_status(
        [_act("2026-09-01", "Ride", "Rollen-Cruise")], TODAY
    )
    assert out.startswith("Aerobic cross-training")
    assert "2026-09-01" in out
    assert "Rollen-Cruise" in out
    assert "(1d ago)" in out


def test_counts_only_the_last_seven_days_in_the_weekly_tally():
    acts = [
        _act("2026-08-20", "Ride"),  # outside the 7d window
        _act("2026-08-28", "Ride"),
        _act("2026-08-31", "VirtualRide"),
    ]
    out = _compute_cross_training_status(acts, TODAY)
    assert "2 in the last 7 days" in out
    assert "2026-08-31" in out


def test_running_and_strength_do_not_count_as_cross_training():
    acts = [_act("2026-09-01", "Run"), _act("2026-08-31", "WeightTraining")]
    out = _compute_cross_training_status(acts, TODAY)
    assert "No impact-free aerobic session in the last 60 days" in out


def test_swimming_counts_too():
    out = _compute_cross_training_status([_act("2026-08-30", "Swim")], TODAY)
    assert "2026-08-30" in out


def test_sessions_older_than_the_lookback_are_ignored():
    out = _compute_cross_training_status([_act("2026-05-01", "Ride")], TODAY)
    assert "No impact-free aerobic session in the last 60 days" in out


def test_demands_an_explicit_decision_on_run_free_days():
    out = _compute_cross_training_status([_act("2026-08-23", "Ride")], TODAY)
    assert "NO run" in out
    assert "silence is not a decision" in out
