"""Tests for the like-for-like comparison unit in the type history.

A session average mixes warm-up, cool-down, strides and jog recoveries into one
figure, and the mixture differs between sessions — so comparing two averages
compares the structure of the sessions rather than the athlete. These helpers
expose the main continuous effort and the work intervals instead.
"""
from __future__ import annotations

from app.graphs.sub_workout_specialist.history_fetcher import (
    _extract_blocks,
    _slim_activity,
)


def _lap(seconds: int, metres: float, hr: int | None = None, type_: str = "WORK") -> dict:
    return {
        "moving_time": seconds,
        "distance": metres,
        "average_heartrate": hr,
        "type": type_,
    }


# ── main block ───────────────────────────────────────────────────────


def test_main_block_is_the_long_continuous_effort_not_the_session():
    """The real case this was built from: warm-up, drill, 33 min main block,
    six strides with jog recoveries, cool-down. The session average was
    5:13/km; the main block was 4:49/km."""
    laps = [
        _lap(481, 1474.9, 119),   # warm-up
        _lap(120, 382.3, 125),    # drill
        _lap(1980, 6840.6, 131),  # main block
        *[lap for _ in range(6) for lap in (_lap(90, 220, 127), _lap(20, 95, 127))],
        _lap(416, 1111.0, 123),   # cool-down
    ]
    main, work = _extract_blocks(laps)
    assert main is not None
    assert main["duration_min"] == 33.0
    assert main["avg_pace_min_km"] == "4:49/km"
    assert main["average_heartrate"] == 131
    # Strides (20 s) and jog recoveries (90 s) are below the work floor.
    assert all(b["duration_min"] >= 3.0 for b in work)


def test_work_blocks_keep_intervals_separate_for_a_structured_session():
    laps = [
        _lap(600, 1800, 120),   # warm-up
        _lap(300, 1150, 158),   # interval 1
        _lap(180, 450, 130),    # recovery
        _lap(300, 1160, 160),   # interval 2
        _lap(400, 1100, 120),   # cool-down
    ]
    main, work = _extract_blocks(laps)
    # Four laps clear the 180 s work floor; the longest is the warm-up here,
    # which is why work_blocks exists alongside main_block.
    assert len(work) == 5
    assert main is not None and main["duration_min"] == 10.0
    paces = [b["avg_pace_min_km"] for b in work]
    assert "4:20/km" in paces  # 300 s / 1150 m


def test_recovery_laps_are_excluded_from_work_blocks():
    laps = [_lap(600, 2000, 130), _lap(300, 700, 110, type_="RECOVERY")]
    _, work = _extract_blocks(laps)
    assert len(work) == 1


def test_short_session_yields_no_main_block():
    """Nothing long enough to be a main block — the caller must fall back to
    the session average and say so, rather than quietly promoting a stride."""
    main, work = _extract_blocks([_lap(200, 700, 140), _lap(60, 200, 120)])
    assert main is None
    assert len(work) == 1


def test_no_lap_data_is_reported_not_papered_over():
    assert _extract_blocks(None) == (None, [])
    assert _extract_blocks([]) == (None, [])


def test_lap_without_distance_is_skipped():
    main, work = _extract_blocks([{"moving_time": 900, "type": "WORK"}])
    assert main is None and work == []


# ── wiring into the payload ──────────────────────────────────────────


def test_slim_activity_marks_the_comparison_unit():
    activity = {
        "start_date_local": "2026-09-18T11:48:51",
        "name": "Easy Z2",
        "moving_time": 3654,
        "type": "Run",
        "average_heartrate": 127,
        "pace": 3.2,
        "icu_intervals": [_lap(481, 1475, 119), _lap(1980, 6840.6, 131)],
    }
    slim = _slim_activity(activity, is_endurance=True)
    assert slim["comparison_unit"] == "main_block"
    assert slim["main_block"]["avg_pace_min_km"] == "4:49/km"
    # The session average survives — volume and drift are session properties.
    assert slim["average_heartrate"] == 127


def test_slim_activity_says_so_when_only_the_session_average_is_available():
    activity = {
        "start_date_local": "2026-09-14T09:00:00",
        "name": "Easy",
        "moving_time": 4194,
        "type": "Run",
        "average_heartrate": 124,
        "pace": 2.95,
    }
    slim = _slim_activity(activity, is_endurance=True)
    assert slim["main_block"] is None
    assert slim["work_blocks"] is None
    assert "session_average" in slim["comparison_unit"]


def test_complementary_sessions_carry_no_block_fields():
    slim = _slim_activity(
        {"start_date_local": "2026-09-17T06:00:00", "name": "Schicht D", "moving_time": 2400},
        is_endurance=False,
    )
    assert "main_block" not in slim
    assert "comparison_unit" not in slim
