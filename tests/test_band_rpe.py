"""Tests for the RPE-vs-heart-rate discrepancy helpers.

Calibration source: research/rpe-vs-percent-lthr-endurance-run.md. The
thresholds are deliberately insensitive — the literature gives a corridor
about two CR10 points wide with a between-athlete SD near one point, so a
smaller trigger would fire on test-retest noise.
"""
from __future__ import annotations

import pytest

from app.utils import band_rpe as br


# ── RPE aus Freitext ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected",
    [
        ("RPE 6", [6.0]),
        ("RPE: 7", [7.0]),
        ("RPE 6,5", [6.5]),
        ("RPE 7-8", [7.5]),
        ("RPE 7–8", [7.5]),
        ("RPE Renntempo-Block: 6", [6.0]),
        ("3x10 Push-ups RPE 6-7 und L-Sit RPE 8", [6.5, 8.0]),
        ("", []),
        (None, []),
        ("kein Wert", []),
    ],
)
def test_parse_rpe_values(text, expected):
    assert br.parse_rpe_values(text) == expected


def test_prose_distance_guard_does_not_harvest_far_numbers():
    text = "RPE war heute deutlich niedriger als sonst, gestern lag sie bei 8"
    assert br.parse_rpe_values(text) == []


def test_out_of_range_values_are_dropped():
    assert br.parse_rpe_values("RPE 42") == []
    assert br.parse_rpe_values("RPE 0") == []


# ── Spitzenfenster ───────────────────────────────────────────────────


def test_best_rolling_mean_finds_the_block_not_the_session_mean():
    stream = [100] * 600 + [160] * 600 + [100] * 600
    assert br.best_rolling_mean(stream, 600) == 160.0


def test_best_rolling_mean_needs_a_full_window():
    assert br.best_rolling_mean([150] * 10, 60) is None


def test_best_rolling_mean_ignores_dropouts():
    assert br.best_rolling_mean([None, 0, 150, 150], 2) == 150.0


def test_pct_of_threshold():
    assert br.pct_of_threshold(166, 166) == pytest.approx(100.0)
    assert br.pct_of_threshold(None, 166) is None
    assert br.pct_of_threshold(150, None) is None


# ── Korridor ─────────────────────────────────────────────────────────


def test_corridor_bands():
    assert br.corridor_for(93) == (4.0, 6.0)
    assert br.corridor_for(97) == (5.0, 7.0)
    assert br.corridor_for(101) == (7.0, 8.0)
    assert br.corridor_for(50) is None


# ── Qualifikation ────────────────────────────────────────────────────


def test_short_block_does_not_qualify():
    assert br.evaluate_block(pct_lthr=93, rpe=1, duration_min=5) is None


def test_block_inside_the_startup_window_does_not_qualify():
    assert br.evaluate_block(
        pct_lthr=93, rpe=1, duration_min=10, start_offset_min=3
    ) is None


def test_missing_rpe_or_intensity_is_not_a_finding():
    assert br.evaluate_block(pct_lthr=93, rpe=None, duration_min=10) is None
    assert br.evaluate_block(pct_lthr=None, rpe=3, duration_min=10) is None


def test_high_decoupling_skips_rather_than_guesses():
    assert br.evaluate_block(
        pct_lthr=93, rpe=1, duration_min=10, decoupling_pct=15
    ) is None


# ── Verdikte ─────────────────────────────────────────────────────────


def test_edge_of_corridor_is_not_a_finding():
    """The case that motivated the check: 10 min at 93 % LTHR, RPE 6.

    It sits at the corridor edge, not below it. Firing here would be
    reading noise as evidence — the research is explicit about this.
    """
    assert br.evaluate_block(
        pct_lthr=93, rpe=6, duration_min=10, outdoor=True
    ) is None


def test_one_point_under_the_floor_is_still_noise():
    assert br.evaluate_block(
        pct_lthr=93, rpe=3, duration_min=10, outdoor=False
    ) is None


def test_two_points_under_the_floor_is_primary():
    out = br.evaluate_block(pct_lthr=93, rpe=2, duration_min=10, outdoor=False)
    assert out["verdict"] == "RPE_LOW_PRIMARY"
    assert out["delta"] == 2.0


def test_three_points_under_the_floor_is_strong_on_its_own():
    out = br.evaluate_block(pct_lthr=93, rpe=1, duration_min=10, outdoor=False)
    assert out["verdict"] == "RPE_LOW_STRONG"
    assert out["reason"] == "single_large"


def test_repeat_primary_escalates_to_strong():
    out = br.evaluate_block(
        pct_lthr=93, rpe=2, duration_min=10, outdoor=False, prior_low_primaries=1
    )
    assert out["verdict"] == "RPE_LOW_STRONG"
    assert out["reason"] == "recurrent"
    assert out["recurrent_n"] == 2


def test_outdoor_lowers_the_floor_and_is_reported():
    indoor = br.evaluate_block(pct_lthr=93, rpe=2, duration_min=10, outdoor=False)
    outdoor = br.evaluate_block(pct_lthr=93, rpe=2, duration_min=10, outdoor=True)
    assert indoor["verdict"] == "RPE_LOW_PRIMARY"
    assert outdoor is None
    assert "outdoor" in br.evaluate_block(
        pct_lthr=93, rpe=1, duration_min=10, outdoor=True
    )["confounders_applied"]


def test_heat_lowers_the_floor_further_and_is_named():
    """Heat raises HR without raising effort, so the floor drops again."""
    named = br.evaluate_block(
        pct_lthr=101, rpe=3, duration_min=10, outdoor=True, temp_c=26
    )
    assert named["verdict"] == "RPE_LOW_PRIMARY"
    assert named["confounders_applied"] == ["outdoor", "heat≥22°C"]
    assert named["corridor"] == (5.0, 8.0)  # 7 -1 outdoor -1 heat


def test_threshold_band_outdoors_in_heat_is_effectively_unreachable():
    """A property of the calibration, recorded rather than papered over.

    At 90–94 % LTHR the corridor floor is 4; outdoor and heat take it to 2,
    and a primary needs two points below that. There is no RPE an athlete
    would plausibly report at threshold in the heat that trips it. The check
    earns its keep in the higher bands and on the treadmill — where the
    corridor is not already discounted twice.
    """
    for rpe in (0.5, 1, 2, 3):
        assert br.evaluate_block(
            pct_lthr=93, rpe=rpe, duration_min=10, outdoor=True, temp_c=26
        ) is None


def test_high_direction_reports_only_as_readiness_signal():
    out = br.evaluate_block(pct_lthr=93, rpe=9, duration_min=10, outdoor=False)
    assert out["verdict"] == "RPE_HIGH_RECURRENT"


def test_corridor_used_is_returned_for_audit():
    out = br.evaluate_block(pct_lthr=93, rpe=1, duration_min=10, outdoor=False)
    assert out["corridor"] == (4.0, 6.0)


# ── Kandidaten-Auswahl ───────────────────────────────────────────────


def _act(aid, day, zones, **kw):
    base = {
        "id": aid,
        "start_date_local": f"{day}T17:00:00",
        "icu_hr_zone_times": zones,
        "type": "Run",
        "lthr": 166,
    }
    base.update(kw)
    return base


def _note(day, text):
    return {"start_date_local": f"{day}T00:00:00", "description": text}


def test_candidate_needs_a_quality_session_and_one_rpe():
    acts = [_act("i1", "2026-08-28", [800, 440, 345, 262, 0])]
    notes = [_note("2026-08-28", "RPE Renntempo-Block: 6")]
    out = br.select_candidates(acts, notes)
    assert [c["date"] for c in out] == ["2026-08-28"]
    assert out[0]["rpe"] == 6.0


def test_easy_day_is_no_candidate():
    acts = [_act("i1", "2026-08-28", [1530, 1270, 58, 0, 0])]
    notes = [_note("2026-08-28", "RPE 3")]
    assert br.select_candidates(acts, notes) == []


def test_two_quality_sessions_on_one_day_are_dropped():
    """Session-RPE cannot be attributed across two blocks."""
    acts = [
        _act("i1", "2026-08-28", [0, 0, 0, 600, 0]),
        _act("i2", "2026-08-28", [0, 0, 0, 700, 0]),
    ]
    notes = [_note("2026-08-28", "RPE 6")]
    assert br.select_candidates(acts, notes) == []


def test_two_rpe_values_in_one_note_are_dropped():
    acts = [_act("i1", "2026-08-28", [0, 0, 0, 600, 0])]
    notes = [_note("2026-08-28", "Block A RPE 6, Block B RPE 8")]
    assert br.select_candidates(acts, notes) == []


def test_two_notes_with_one_value_each_are_dropped():
    acts = [_act("i1", "2026-08-28", [0, 0, 0, 600, 0])]
    notes = [_note("2026-08-28", "RPE 6"), _note("2026-08-28", "RPE 8")]
    assert br.select_candidates(acts, notes) == []


def test_activity_without_zone_times_is_ignored():
    acts = [
        _act("i1", "2026-08-28", None),
        _act("i2", "2026-08-28", [0, 0, 0, 600, 0]),
    ]
    notes = [_note("2026-08-28", "RPE 6")]
    assert [c["activity"]["id"] for c in br.select_candidates(acts, notes)] == ["i2"]


def test_treadmill_counts_as_indoor():
    assert br.is_outdoor(_act("i1", "2026-08-28", None, type="VirtualRun")) is False
    assert br.is_outdoor(_act("i1", "2026-08-28", None, trainer=True)) is False
    assert br.is_outdoor(_act("i1", "2026-08-28", None)) is True
