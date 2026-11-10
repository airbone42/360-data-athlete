"""analyse_activity: compact per-lap / per-zone summary computed in code.

Coach audit 2026-11-08: /analyse dumped every stream (hundreds of KB) and had
the model pass streams between scripts via echo. These tests pin the summary
on synthetic streams (2025 dates, athlete-agnostic) and the script wiring.
"""
from __future__ import annotations

import asyncio
import json
from argparse import Namespace

import pytest

from app.analytics import activity_analysis as aa
from app.utils import garmin_client
from app.utils.windowing import build_sub_laps, lap_boundaries

RUN_SETTINGS = {"sportSettings": [
    {"types": ["Run"], "lthr": 166, "max_hr": 176, "hr_zones": [125, 139, 153, 166, 176]},
    {"types": ["Ride", "VirtualRide"], "lthr": 156, "max_hr": 168,
     "hr_zones": [118, 131, 144, 156, 168]},
]}


def _run_streams() -> tuple[dict, list[dict]]:
    """10 min WU @120, 25 min main 140→150 at 3.3 m/s, 5 min CD @125 (1 Hz)."""
    time, hr, vel = [], [], []
    for t in range(0, 2400):
        time.append(t)
        if t < 600:
            hr.append(120)
            vel.append(2.8)
        elif t < 2100:
            hr.append(140 + (t - 600) * 10 / 1500)
            vel.append(3.3)
        else:
            hr.append(125)
            vel.append(2.5)
    streams = {"time": time, "heartrate": hr, "velocity_smooth": vel,
               "cadence": [86] * 2400}
    intervals = [
        {"start_index": 0, "end_index": 599, "type": "RECOVERY", "label": "WU",
         "distance": 1680},
        {"start_index": 600, "end_index": 2099, "type": "WORK", "distance": 4950},
        {"start_index": 2100, "end_index": 2399, "type": "RECOVERY", "distance": 750},
    ]
    return streams, intervals


ACT = {"id": "i1", "type": "Run", "start_date_local": "2025-06-20T07:00:00",
       "source": "STRAVA", "moving_time": 2400, "distance": 7380,
       "average_heartrate": 137, "max_heartrate": 150, "average_speed": 3.075,
       "decoupling": 4.2}


def test_lap_hr_avg_and_max_per_lap() -> None:
    streams, intervals = _run_streams()
    out = aa.summarize_activity(ACT, streams, intervals, RUN_SETTINGS)
    assert out["data_source"] == "intervals_streams"
    wu, main, cd = out["laps"]
    assert wu["avg_hr"] == 120 and wu["max_hr"] == 120 and wu["label"] == "WU"
    assert main["type"] == "WORK" and main["duration_min"] == 25.0
    assert main["avg_hr"] == 145 and main["max_hr"] == 150
    assert main["pace"] == "5:03/km"
    assert cd["avg_hr"] == 125


def test_sub_laps_carry_hr_avg_and_max() -> None:
    streams, intervals = _run_streams()
    main = aa.summarize_activity(ACT, streams, intervals, RUN_SETTINGS)["laps"][1]
    subs = main["sub_laps"]
    assert len(subs) == 5  # 25 min lap → 5-min windows
    assert subs[0]["avg_hr"] < subs[-1]["avg_hr"]
    assert all("max_hr" in s and "pace" in s for s in subs)


def test_zone_times_use_the_activity_sport_and_sum_to_duration() -> None:
    streams, intervals = _run_streams()
    out = aa.summarize_activity(ACT, streams, intervals, RUN_SETTINGS)
    assert out["hr_zones"]["sport"] == "Run" and out["hr_zones"]["lthr"] == 166
    zt = {z["zone"]: z for z in out["hr_zone_times"]}
    assert zt["Z1 (Recovery)"]["min"] == pytest.approx(15.0, abs=0.1)  # WU + CD
    assert zt["Z3 (Aerobic)"]["min"] > 0
    assert sum(z.get("min", 0) for z in out["hr_zone_times"]) == pytest.approx(40, abs=0.1)


def test_ride_is_judged_on_ride_zones() -> None:
    streams, intervals = _run_streams()
    streams["watts"] = [200] * 2400
    ride = {**ACT, "type": "VirtualRide", "source": "WAHOO"}
    out = aa.summarize_activity(ride, streams, intervals, RUN_SETTINGS)
    assert out["hr_zones"]["sport"] == "Ride" and out["hr_zones"]["max_hr"] == 168
    # 120 bpm is Z2 on the ride zones (Z1 ends at 118), Z1 on the run zones.
    assert out["hr_zone_times"][1]["min"] > 0
    main = out["laps"][1]
    assert main["avg_watts"] == 200 and "pace" not in main


def test_unknown_sport_falls_back_to_run_zones_labelled() -> None:
    streams, intervals = _run_streams()
    out = aa.summarize_activity({**ACT, "type": "Rowing"}, streams, intervals,
                                {"sportSettings": RUN_SETTINGS["sportSettings"][:1]})
    assert out["hr_zones"]["sport"].startswith("Run (no HR zones for Rowing")


def test_zero_zone_is_reported_not_merged() -> None:
    streams, _ = _run_streams()
    zt = aa.hr_zone_times(streams, [125, 0, 153, 166, 176])
    assert zt[1] == {"zone": "Z2 (Endurance)", "range": "not set in intervals.icu"}
    assert zt[2]["range"] == "126–153 bpm"


def test_pause_gaps_are_not_counted_as_zone_time() -> None:
    streams = {"time": [0, 1, 2, 600, 601], "heartrate": [130, 130, 130, 130, 130]}
    zt = aa.hr_zone_times(streams, [125, 139])
    # 3 s of samples; the 598 s pause would read as ~10 min otherwise.
    assert zt[1]["min"] <= 0.1


def test_decoupling_main_block_and_intervals_value() -> None:
    streams, intervals = _run_streams()
    dec = aa.summarize_activity(ACT, streams, intervals, RUN_SETTINGS)["decoupling"]
    assert dec["intervals_icu_pct"] == 4.2
    assert dec["main_block"]["lap"] == 2 and dec["main_block"]["basis"] == "pace:HR"
    # HR rose ~140→150 at constant pace: EF fell ≈3.5 %.
    assert 2.5 < dec["main_block"]["pct"] < 4.5


def test_manual_activity_without_streams() -> None:
    out = aa.summarize_activity({**ACT, "source": "MANUAL"}, {}, [], RUN_SETTINGS)
    assert out["data_source"] == "none"
    assert "laps" not in out
    assert any("description" in n for n in out["notes"])


def test_no_laps_means_one_whole_session_lap() -> None:
    streams, _ = _run_streams()
    out = aa.summarize_activity(ACT, streams, [], RUN_SETTINGS)
    assert len(out["laps"]) == 1
    assert any("no laps" in n for n in out["notes"])


def test_fit_path_uses_fit_laps_and_dynamics() -> None:
    streams, _ = _run_streams()
    fit_laps = [
        {"lap_index": 1, "start_time": "2025-06-20T07:00:00", "elapsed_s": 600,
         "duration_s": 600, "distance_m": 1680.0, "avg_step_length": 1050.0},
        {"lap_index": 2, "start_time": "2025-06-20T07:10:00", "elapsed_s": 1800,
         "duration_s": 1800, "distance_m": 5700.0, "avg_vertical_osc": 82.0},
    ]
    records = [{"timestamp": f"2025-06-20T07:{m:02d}:{s:02d}", "stance_time": 240,
                "step_length": 1100} for m in range(0, 40) for s in range(0, 60)]
    out = aa.summarize_activity({**ACT, "source": "GARMIN_CONNECT"}, streams, None,
                                RUN_SETTINGS, fit_laps=fit_laps, fit_records=records)
    assert out["data_source"] == "fit"
    assert out["laps"][0]["avg_step_length_mm"] == 1050.0
    assert out["laps"][1]["avg_vo_mm"] == 82.0
    assert out["laps"][1]["sub_laps"][0]["avg_gct_ms"] == 240


def test_output_is_compact() -> None:
    streams, intervals = _run_streams()
    out = aa.summarize_activity(ACT, streams, intervals, RUN_SETTINGS)
    raw = json.dumps(streams)
    assert len(json.dumps(out)) < len(raw) / 10


# ── windowing additions ─────────────────────────────────────────────────


def test_lap_boundaries_accept_explicit_offsets() -> None:
    laps = [{"lap_index": 1, "start_s": 5, "end_s": 65}]
    assert lap_boundaries(laps) == [(1, 5, 65)]


def test_windows_carry_max_hr_and_watts() -> None:
    streams = {"time": list(range(60)), "heartrate": [100 + i for i in range(60)],
               "watts": [150] * 60}
    win = build_sub_laps(streams, [], [], [{"lap_index": 1, "start_s": 0, "end_s": 60}])
    assert win[0]["max_hr"] == 129 and win[0]["avg_watts"] == 150


# ── Garmin activity matching ────────────────────────────────────────────


def test_garmin_pick_matches_start_time() -> None:
    acts = [{"activityId": 2, "startTimeLocal": "2025-06-20 18:00:00"},
            {"activityId": 1, "startTimeLocal": "2025-06-20 07:01:00"}]
    assert garmin_client._pick_activity(acts, "2025-06-20T07:00:00")["activityId"] == 1
    assert garmin_client._pick_activity(acts, None)["activityId"] == 2
    with pytest.raises(FileNotFoundError):
        garmin_client._pick_activity(acts, "2025-06-20T12:00:00")


# ── script wiring ───────────────────────────────────────────────────────


def test_script_falls_back_to_streams_for_non_garmin_sources() -> None:
    from scripts import analyse_activity as script

    ok, note = script._wants_fit({"source": "WAHOO"}, no_fit=False)
    assert not ok and "WAHOO" in note
    ok, note = script._wants_fit({"source": "GARMIN_CONNECT"}, no_fit=False)
    assert ok and note is None


def test_script_fit_failure_is_a_note_not_an_error(monkeypatch, tmp_path) -> None:
    from scripts import analyse_activity as script

    laps, records, note = script._load_fit({"start_date_local": "2025-06-20T07:00:00"},
                                           str(tmp_path / "missing.fit"))
    assert laps == [] and records == [] and "FIT unavailable" in note


def test_script_gather_end_to_end(monkeypatch) -> None:
    from app.api import intervals_cache
    from scripts import analyse_activity as script

    streams, intervals = _run_streams()

    class _Client:
        def __init__(self, *_a, **_k) -> None:
            pass

        async def get_activity(self, _id):
            return {**ACT, "source": "WAHOO", "paired_event_id": 7,
                    "description": "Feedback: RPE 4"}

        async def get_activity_intervals(self, _id):
            return intervals

        async def get_streams(self, _id):
            return streams

        async def get_athlete_settings(self):
            return RUN_SETTINGS

        async def get_event(self, _id):
            return {"name": "Easy 40", "description": "40min Z2"}

        async def get_wellness(self, _day):
            return {"hrv": 55, "restingHR": 44, "kcal": 1}

    monkeypatch.setattr(intervals_cache, "CachedIntervalsClient", _Client)
    args = Namespace(no_fit=False, fit_path=None, no_surface=True)
    out = asyncio.run(script._gather("i1", args))
    assert out["planned_workout"]["name"] == "Easy 40"
    assert out["wellness"] == {"hrv": 55, "restingHR": 44}
    assert out["activity"]["description"].startswith("Feedback")
    assert any("WAHOO" in n for n in out["notes"])
    assert "streams" not in out


def test_fetch_activity_leaves_streams_out_by_default(monkeypatch) -> None:
    from scripts import fetch_activity as fa

    calls: list[str] = []

    class _Client:
        def __init__(self, *_a, **_k) -> None:
            pass

        async def get_activity(self, _id):
            return {"id": "i1", "start_date_local": "2025-06-20T07:00:00"}

        async def get_streams(self, _id):
            calls.append("streams")
            return {"time": [0]}

        async def get_wellness(self, _day):
            return {}

    monkeypatch.setattr(fa, "IntervalsClient", _Client)
    lean = asyncio.run(fa._fetch("i0", "i1"))
    assert "streams" not in lean and calls == []
    full = asyncio.run(fa._fetch("i0", "i1", with_streams=True))
    assert full["streams"] == {"time": [0]}
