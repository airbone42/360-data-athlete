"""Audit-check level tests for RPE_HR_DISCREPANCY."""
from __future__ import annotations

from scripts import audit_consistency as ac


def _act(aid="i1", day="2026-08-28", **kw):
    base = {
        "id": aid,
        "name": "Threshold-Block",
        "start_date_local": f"{day}T17:00:00",
        "icu_hr_zone_times": [0, 0, 0, 900, 0],
        "type": "VirtualRun",     # treadmill: no outdoor discount
        "lthr": 166,
    }
    base.update(kw)
    return base


def _note(day="2026-08-28", text="RPE 6"):
    return {"start_date_local": f"{day}T00:00:00", "description": text}


def _hr(bpm, seconds=900):
    return {"i1": [bpm] * seconds}


def test_no_streams_means_no_finding():
    assert ac.check_rpe_hr_discrepancy([_act()], [_note()], {}) == []


def test_effort_inside_the_corridor_is_quiet():
    # 153 bpm / 166 = 92 % LTHR -> corridor 4..6, RPE 6 sits at the ceiling
    assert ac.check_rpe_hr_discrepancy([_act()], [_note()], _hr(153)) == []


def test_far_too_easy_is_reported():
    out = ac.check_rpe_hr_discrepancy([_act()], [_note(text="RPE 1")], _hr(153))
    assert len(out) == 1
    assert out[0]["category"] == "rpe_low_strong"
    assert out[0]["severity"] == ac.MEDIUM
    assert "92.2 % LTHR" in out[0]["evidence"]
    assert out[0]["suggested_action"] == "recalibrate_band"


def test_finding_names_the_corridor_and_confounders():
    out = ac.check_rpe_hr_discrepancy([_act()], [_note(text="RPE 1")], _hr(153))
    assert "Korridor nach Confounder-Abzug 4.0–6.0" in out[0]["evidence"]
    assert "keine" in out[0]["evidence"]


def test_high_direction_routes_to_readiness_not_recalibration():
    out = ac.check_rpe_hr_discrepancy([_act()], [_note(text="RPE 9")], _hr(153))
    assert out[0]["category"] == "rpe_high_recurrent"
    assert "Readiness-Pfad" in out[0]["fix_hint"]
    assert out[0]["severity"] == ac.LOW


def test_check_is_registered_online():
    assert ac.CHECK_MAP["RPE_HR_DISCREPANCY"] == ("check_rpe_hr_discrepancy", True)
