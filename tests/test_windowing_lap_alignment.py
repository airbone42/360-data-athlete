"""Sub-lap windows must sit on the elapsed timeline, not on timer time.

`build_sub_laps` matches its windows against the intervals.icu `time` stream,
which counts *elapsed* seconds and contains gaps wherever recording was
paused. Lap boundaries derived by cumulating `duration_s` (timer time, which
excludes stopped time) drift earlier by the accumulated pause on every lap
after the first stop.

That failure is silent and worse than missing data: the window keeps the
label of one lap while carrying another lap's samples, so a stride window
reports jogging dynamics and reads as a perfectly valid measurement.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.windowing import build_sub_laps  # noqa: E402

# Three laps: 60 s jog, a 120 s pause, then 60 s of "stride" (high cadence).
# Timer time knows nothing about the pause, elapsed time does.
_PAUSE_S = 120
_LAPS = [
    {
        "lap_index": 1,
        "duration_s": 60,
        "elapsed_s": 60,
        "start_time": "2026-08-02T10:00:00",
    },
    {
        "lap_index": 2,
        "duration_s": 60,
        "elapsed_s": 60,
        # Starts 60 s of running + 120 s of pause after the activity began.
        "start_time": "2026-08-02T10:03:00",
    },
]


def _fixture() -> tuple[dict, list[dict], list[str]]:
    """Streams and FIT records with a recording gap between the two laps."""
    times = list(range(0, 60)) + list(range(60 + _PAUSE_S, 120 + _PAUSE_S))
    streams = {
        "time": times,
        "heartrate": [130] * len(times),
        "velocity_smooth": [3.0] * len(times),
    }
    records = []
    for t in times:
        is_stride = t >= 60 + _PAUSE_S
        records.append({
            "timestamp": f"2026-08-02T{10 + (t // 3600):02d}:{(t // 60) % 60:02d}:{t % 60:02d}",
            "cadence": 200 if is_stride else 160,
            "stance_time": 190 if is_stride else 260,
        })
    return streams, records, ["unknown"] * len(times)


def test_stride_lap_carries_stride_samples_across_a_pause():
    """The lap-2 window must report the high-cadence samples, not lap 1's."""
    streams, records, surfaces = _fixture()
    windows = build_sub_laps(streams, surfaces, records, _LAPS)

    lap2 = [w for w in windows if w["lap_index"] == 2]
    assert lap2, "lap 2 produced no window at all"
    assert all(w["avg_cadence_spm"] == 200 for w in lap2), (
        f"lap-2 windows carry lap-1 (jog) samples: {[w['avg_cadence_spm'] for w in lap2]}"
    )

    lap1 = [w for w in windows if w["lap_index"] == 1]
    assert lap1 and all(w["avg_cadence_spm"] == 160 for w in lap1), (
        f"lap-1 windows contaminated: {[w['avg_cadence_spm'] for w in lap1]}"
    )


def test_falls_back_to_cumulative_duration_without_timestamps():
    """Laps without `start_time` keep the legacy behaviour on a gapless run.

    Callers that synthesise laps by hand never had timestamps. Without a
    recording pause timer time and elapsed time coincide, so the cumulative
    fallback is exact and must keep producing both laps' windows.

    Note this fixture deliberately has *no* gap: with one, the fallback cannot
    place the later lap at all — that is the defect the timestamp path exists
    to fix, not behaviour worth pinning down in a test.
    """
    times = list(range(0, 120))
    streams = {
        "time": times,
        "heartrate": [130] * len(times),
        "velocity_smooth": [3.0] * len(times),
    }
    records = [
        {
            "timestamp": f"2026-08-02T10:{t // 60:02d}:{t % 60:02d}",
            "cadence": 200 if t >= 60 else 160,
            "stance_time": 190 if t >= 60 else 260,
        }
        for t in times
    ]
    bare = [{"lap_index": 1, "duration_s": 60}, {"lap_index": 2, "duration_s": 60}]
    windows = build_sub_laps(streams, ["unknown"] * len(times), records, bare)

    assert {w["lap_index"] for w in windows} == {1, 2}, "fallback lost a lap"
    assert all(w["avg_cadence_spm"] == 160 for w in windows if w["lap_index"] == 1)
    assert all(w["avg_cadence_spm"] == 200 for w in windows if w["lap_index"] == 2)
