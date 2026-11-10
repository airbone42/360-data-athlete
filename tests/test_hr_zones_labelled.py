"""context.hrZones carries labelled per-sport zones; activities carry measured HR.

Coach audit 2026-11-08: the coach estimated HR values because the context gave
unlabelled run zones only and no HR per activity.
"""
from __future__ import annotations

from app.graphs.sub_athlete_context.context_builder import (
    _collect_warnings,
    _summarize_activity,
)
from app.utils.hr_zones import (
    HR_ZONES_UNAVAILABLE,
    extract_run_hr_bounds,
    format_hr_zones,
    format_sport_hr_zones,
    sport_hr_settings,
)

RUN = {"types": ["Run", "VirtualRun"], "lthr": 166, "max_hr": 176,
       "hr_zones": [125, 139, 153, 166, 176]}
RIDE = {"types": ["Ride", "VirtualRide"], "lthr": 158, "max_hr": 170,
        "hr_zones": [120, 134, 147, 158, 170]}


def test_run_line_carries_label_lthr_and_max() -> None:
    text = format_sport_hr_zones({"sportSettings": [RUN]})
    assert text.startswith("Run (LTHR 166 bpm, HRmax 176 bpm): ")
    assert "Z1 (Recovery): 1–125 bpm" in text
    assert "Z5 (VO2max): 167–176 bpm" in text
    assert "\n" not in text


def test_ride_line_follows_run_when_present() -> None:
    text = format_sport_hr_zones({"sportSettings": [RIDE, RUN]})
    lines = text.splitlines()
    assert lines[0].startswith("Run (")
    assert lines[1].startswith("Ride (LTHR 158 bpm, HRmax 170 bpm): ")
    assert "Z2 (Endurance): 121–134 bpm" in lines[1]


def test_zero_zone_is_shown_not_dropped() -> None:
    run = {**RUN, "hr_zones": [125, 0, 153, 166, 176]}
    text = format_sport_hr_zones({"sportSettings": [run]})
    assert "Z2 (Endurance): not set in intervals.icu" in text
    # Z3 keeps its name and starts after the last real bound.
    assert "Z3 (Aerobic): 126–153 bpm" in text


def test_trailing_padding_zeros_are_trimmed() -> None:
    s = sport_hr_settings({"sportSettings": [{**RUN, "hr_zones": [125, 139, 153, 166, 176, 0, 0]}]}, "Run")
    assert s["bounds"] == [125, 139, 153, 166, 176]


def test_missing_lthr_is_named() -> None:
    run = {**RUN, "lthr": None}
    assert "LTHR not set" in format_sport_hr_zones({"sportSettings": [run]})


def test_no_settings_reads_unavailable() -> None:
    assert format_sport_hr_zones({}) == HR_ZONES_UNAVAILABLE
    assert format_hr_zones([]) == HR_ZONES_UNAVAILABLE


def test_sport_lookup_by_activity_type() -> None:
    settings = {"sportSettings": [RUN, RIDE]}
    assert sport_hr_settings(settings, "VirtualRide")["lthr"] == 158
    assert sport_hr_settings(settings, "Run")["max_hr"] == 176
    assert sport_hr_settings(settings, "Swim") is None


def test_legacy_run_bounds_helper_still_works() -> None:
    assert extract_run_hr_bounds({"sportSettings": [RUN]}) == [125, 139, 153, 166, 176]


def test_incomplete_zones_raise_a_data_warning() -> None:
    text = format_sport_hr_zones({"sportSettings": [{**RUN, "max_hr": 0}]})
    warnings = _collect_warnings(50, 45, 80, 40, 40, text, {"x": 1})
    assert any("incomplete" in w for w in warnings)


def test_summarize_activity_carries_measured_hr() -> None:
    a = {"start_date_local": "2026-11-09T08:00:00", "type": "Run", "moving_time": 3000,
         "average_heartrate": 142.6, "max_heartrate": 171}
    out = _summarize_activity(a)
    assert out["avg_hr"] == 143 and out["max_hr"] == 171


def test_summarize_activity_without_hr_has_no_hr_keys() -> None:
    out = _summarize_activity({"start_date_local": "2026-11-09T08:00:00", "type": "Workout",
                               "average_heartrate": None})
    assert "avg_hr" not in out and "max_hr" not in out
