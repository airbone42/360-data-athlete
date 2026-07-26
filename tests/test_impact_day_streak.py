"""Tests for the impact-load streak signal and validator rule R022.

The pattern under test: every autonomic marker is green, every individual
rule passes, and the plan still stacks a fourth consecutive running day
with a long run and a quality session inside the streak. Neither
``lastRestDay`` (counts any activity, so a mobility block masks a rest day
and a bike day looks like a run day) nor ``daysSinceIntense``
(backward-looking, intensity rather than impact) makes that visible.

All dates are synthetic 2025 values on purpose — real training dates in a
public test suite would leak the maintainer's block schedule.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.impact_load import compute_run_day_streak  # noqa: E402


def _run(day: str, minutes: int = 60, load: int | None = 40, **kw) -> dict:
    return {
        "type": "Run",
        "start_date_local": f"{day}T07:00:00",
        "duration_min": minutes,
        "training_load": load,
        **kw,
    }


def _ride(day: str, minutes: int = 50) -> dict:
    return {
        "type": "Ride",
        "start_date_local": f"{day}T07:00:00",
        "duration_min": minutes,
        "training_load": 33,
    }


def _mobility(day: str) -> dict:
    """A load-less mobility block — the thing that masks a rest day."""
    return {
        "type": "Workout",
        "start_date_local": f"{day}T20:00:00",
        "duration_min": 12,
        "training_load": None,
    }


# ───────────────────────── streak computation ─────────────────────────

def test_no_activities_reports_no_streak():
    result = compute_run_day_streak([], date(2025, 3, 16))
    assert result["streak_days"] == 0
    assert result["prospective_days"] == 1
    assert result["run_days_7d"] == 0
    assert "No current run-day streak" in result["message"]


def test_streak_ending_yesterday_projects_today():
    """The canonical case: runs on three consecutive days, none yet today."""
    activities = [
        _run("2025-03-13", minutes=64, load=35),
        _run("2025-03-14", minutes=61, load=41),
        _run("2025-03-15", minutes=104, load=78),
    ]
    result = compute_run_day_streak(activities, date(2025, 3, 16))
    assert result["streak_days"] == 3
    assert result["includes_today"] is False
    assert result["prospective_days"] == 4
    assert result["contains_long_run"] is True
    assert result["contains_quality"] is True
    assert result["streak_dates"] == ["2025-03-13", "2025-03-14", "2025-03-15"]
    assert "a run today would make it 4" in result["message"]


def test_todays_run_is_counted_not_double_projected():
    activities = [
        _run("2025-03-14"),
        _run("2025-03-15"),
        _run("2025-03-16"),
    ]
    result = compute_run_day_streak(activities, date(2025, 3, 16))
    assert result["includes_today"] is True
    assert result["streak_days"] == 3
    assert result["prospective_days"] == 3


def test_bike_day_breaks_the_streak():
    """The whole point of the signal: cycling carries no ground impact."""
    activities = [
        _run("2025-03-13"),
        _run("2025-03-14"),
        _ride("2025-03-15"),
    ]
    result = compute_run_day_streak(activities, date(2025, 3, 16))
    assert result["streak_days"] == 0
    assert result["prospective_days"] == 1
    assert result["run_days_7d"] == 2


def test_mobility_day_breaks_the_streak_although_lastrestday_would_not():
    """A load-less mobility block is not an impact day.

    ``_find_last_rest_day`` would report "no rest day" for this history
    because it counts any logged activity. The impact streak must not.
    """
    activities = [
        _run("2025-03-13"),
        _run("2025-03-14"),
        _mobility("2025-03-15"),
    ]
    result = compute_run_day_streak(activities, date(2025, 3, 16))
    assert result["streak_days"] == 0


def test_gap_day_resets_streak_to_the_recent_run_only():
    activities = [
        _run("2025-03-10"),
        _run("2025-03-11"),
        _run("2025-03-12"),
        # 2025-03-13 off
        _run("2025-03-15"),
    ]
    result = compute_run_day_streak(activities, date(2025, 3, 16))
    assert result["streak_days"] == 1
    assert result["prospective_days"] == 2
    assert result["run_days_7d"] == 4


def test_treadmill_run_counts_as_impact():
    activities = [_run("2025-03-15"), {
        "type": "VirtualRun",
        "start_date_local": "2025-03-14T07:00:00",
        "duration_min": 45,
        "training_load": 30,
    }]
    result = compute_run_day_streak(activities, date(2025, 3, 16))
    assert result["streak_days"] == 2


def test_quality_detected_via_tag_without_high_load():
    activities = [_run("2025-03-15", minutes=50, load=20, tags=["run", "intervals"])]
    result = compute_run_day_streak(activities, date(2025, 3, 16))
    assert result["contains_quality"] is True


def test_streak_without_long_run_or_quality_is_flagged_as_plain():
    activities = [
        _run("2025-03-13", minutes=45, load=25),
        _run("2025-03-14", minutes=45, load=25),
        _run("2025-03-15", minutes=45, load=25),
    ]
    result = compute_run_day_streak(activities, date(2025, 3, 16))
    assert result["contains_long_run"] is False
    assert result["contains_quality"] is False


def _raw_run(day: str, seconds: int = 3600, load: int | None = 40) -> dict:
    """Raw intervals.icu shape: moving_time in seconds, icu_training_load."""
    return {
        "type": "Run",
        "start_date_local": f"{day}T07:00:00",
        "moving_time": seconds,
        "icu_training_load": load,
    }


def test_raw_api_activity_shape_is_understood():
    """context_builder passes raw dicts (moving_time / icu_training_load),
    the formatted summaries use duration_min / training_load. Reading only
    one shape made a long run silently invisible inside the streak."""
    activities = [
        _raw_run("2025-03-14", seconds=3660, load=41),
        _raw_run("2025-03-15", seconds=6264, load=78),   # 104 min
    ]
    result = compute_run_day_streak(activities, date(2025, 3, 16))
    assert result["streak_days"] == 2
    assert result["contains_long_run"] is True
    assert result["contains_quality"] is True


def test_both_shapes_agree_on_the_same_history():
    raw = [_raw_run("2025-03-15", seconds=6264, load=78)]
    fmt = [_run("2025-03-15", minutes=104, load=78)]
    today = date(2025, 3, 16)
    a = compute_run_day_streak(raw, today)
    b = compute_run_day_streak(fmt, today)
    for key in ("streak_days", "contains_long_run", "contains_quality",
                "prospective_days", "prospective_5d"):
        assert a[key] == b[key], key


def test_malformed_activities_do_not_raise():
    activities = [
        {"type": "Run"},                                    # no date
        {"type": "Run", "start_date_local": "not-a-date"},  # unparsable
        {"start_date_local": "2025-03-15T07:00:00"},        # no type
        _run("2025-03-15", minutes=None, load="n/a"),       # bad numerics
    ]
    result = compute_run_day_streak(activities, date(2025, 3, 16))
    assert result["streak_days"] == 1
    assert result["contains_long_run"] is False


# ───────────────────────── validator rule R022 ─────────────────────────

@pytest.fixture
def ctx_three_run_days():
    from validate_plan import Context
    return Context(
        target_date="2025-03-16",
        recent_activities=[
            _run("2025-03-13", minutes=64, load=35),
            _run("2025-03-14", minutes=61, load=41),
            _run("2025-03-15", minutes=104, load=78),
        ],
    )


def _findings(workouts, ctx):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from validate_plan import check_impact_day_streak
    return check_impact_day_streak(workouts, ctx)


def test_r022_fires_on_fourth_consecutive_run_day(ctx_three_run_days):
    workouts = [{"type": "Run", "name": "Easy Z2", "duration_min": 45,
                 "workout_type": "EASY"}]
    findings = _findings(workouts, ctx_three_run_days)
    assert len(findings) == 1
    assert findings[0].rule_id == "R022"
    assert findings[0].severity == "WARNING"
    assert "impact day 4 in a row" in findings[0].message
    assert "a long run" in findings[0].message


def test_r022_silent_when_the_day_is_cross_training(ctx_three_run_days):
    """The fix that resolved the real incident must make the rule quiet."""
    workouts = [{"type": "Ride", "name": "Recovery spin", "duration_min": 50,
                 "workout_type": "RECOVERY", "indoor": True}]
    assert _findings(workouts, ctx_three_run_days) == []


def test_r022_downgrades_to_info_when_rationale_is_documented(ctx_three_run_days):
    workouts = [{
        "type": "Run", "name": "Easy Z2", "duration_min": 45,
        "workout_type": "EASY",
        "coaching_notes": (
            "Bewusst der 4. Lauftag in Folge — Cross-Training geprüft und "
            "verworfen, weil der Rad-Slot heute nicht verfügbar ist."
        ),
    }]
    findings = _findings(workouts, ctx_three_run_days)
    assert len(findings) == 1
    assert findings[0].severity == "INFO"
    assert "Rationale documented" in findings[0].message


def test_r022_silent_below_threshold():
    from validate_plan import Context
    ctx = Context(
        target_date="2025-03-16",
        recent_activities=[_run("2025-03-14"), _run("2025-03-15")],
    )
    workouts = [{"type": "Run", "name": "Easy Z2", "duration_min": 60}]
    assert _findings(workouts, ctx) == []


# ── density axis: the one that actually caught the real incident ──

DENSITY_CONFIG = """
## Impact-Last-Toleranz
- **impact_streak_max:** 4
- **impact_density_max_5d:** 4
"""


@pytest.fixture
def ctx_dense_but_not_consecutive():
    """Runs on day-4, day-2 and day-1 — four impact days in five once today
    is added, while the consecutive streak never passes three. This is the
    pattern a strict streak counter misses and an off-day disguises."""
    from validate_plan import Context
    return Context(
        target_date="2025-03-16",
        athlete_status=DENSITY_CONFIG,
        recent_activities=[
            _run("2025-03-12", minutes=64, load=35),
            # 2025-03-13 no run
            _run("2025-03-14", minutes=61, load=41),
            _run("2025-03-15", minutes=104, load=78),
        ],
    )


def test_density_axis_fires_although_streak_is_below_threshold(
    ctx_dense_but_not_consecutive,
):
    workouts = [{"type": "Run", "name": "Easy Z2", "duration_min": 45,
                 "workout_type": "EASY"}]
    findings = _findings(workouts, ctx_dense_but_not_consecutive)
    assert len(findings) == 1
    assert findings[0].severity == "WARNING"
    assert "within 5 days" in findings[0].message
    assert "an off-day masks it" in findings[0].message


def test_density_axis_is_opt_in_via_config(ctx_dense_but_not_consecutive):
    """Without the config key the framework default stays quiet — tolerance
    is athlete-specific and a 6x/week runner must not be spammed."""
    from validate_plan import Context
    ctx = Context(
        target_date=ctx_dense_but_not_consecutive.target_date,
        athlete_status="",
        recent_activities=ctx_dense_but_not_consecutive.recent_activities,
    )
    assert _findings([{"type": "Run", "name": "Easy Z2", "duration_min": 45}], ctx) == []


def test_cross_training_resolves_the_density_case(ctx_dense_but_not_consecutive):
    workouts = [{"type": "Ride", "name": "Recovery spin", "duration_min": 50,
                 "indoor": True}]
    assert _findings(workouts, ctx_dense_but_not_consecutive) == []


def test_configured_streak_threshold_is_honoured():
    from validate_plan import Context
    ctx = Context(
        target_date="2025-03-16",
        athlete_status="- **impact_streak_max:** 3",
        recent_activities=[_run("2025-03-14"), _run("2025-03-15")],
    )
    findings = _findings([{"type": "Run", "name": "Easy", "duration_min": 60}], ctx)
    assert len(findings) == 1
    assert "impact day 3 in a row" in findings[0].message


def test_density_helper_counts_windows_independently():
    activities = [
        _run("2025-03-10"), _run("2025-03-12"), _run("2025-03-14"), _run("2025-03-15"),
    ]
    result = compute_run_day_streak(activities, date(2025, 3, 16))
    assert result["streak_days"] == 2
    assert result["run_days_5d"] == 3      # 12th, 14th, 15th
    assert result["prospective_5d"] == 4
    assert result["run_days_7d"] == 4


def test_r022_registered_in_rules():
    from validate_plan import RULES
    assert "R022" in [rid for rid, _ in RULES]


def test_r022_survives_broken_target_date():
    from validate_plan import Context
    ctx = Context(target_date="whenever", recent_activities=[_run("2025-03-15")])
    assert _findings([{"type": "Run", "name": "x"}], ctx) == []
