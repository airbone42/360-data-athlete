"""Tests for the load-progression helper and validator rules R033-R035.

R033 (single-session spike) is a WARNING-only convention; R034 (quality
density) and R035 (calendar deload) are opt-in athlete decisions. Dates are
synthetic 2025 values on purpose. 2025-03-17 is a Monday.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from app.utils.load_progression import (  # noqa: E402
    compute_deload_due,
    is_quality_run,
    parse_load_rules,
)
from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    check_deload_due,
    check_quality_run_density,
    check_session_spike_vs_30d_longest,
)

TODAY = "2025-03-17"
STATUS_ON = """
quality_runs_max_7d: 2
quality_min_spacing_h: 48
long_run_quality_mode: block
quality_density_severity: error
deload_every_n_weeks: 3
deload_reduction_pct: 30
deload_severity: error
session_spike_warn_pct: 10
"""


def _act(day: str, minutes: int, **kw) -> dict:
    return {"type": "Run", "date": day, "start_date_local": f"{day}T07:00:00",
            "duration_min": minutes, **kw}


def _plan(minutes: int, **kw) -> dict:
    return {"type": "Run", "name": "Run", "duration_min": minutes, **kw}


def _ctx(status: str = STATUS_ON, acts: list[dict] | None = None) -> Context:
    return Context(target_date=TODAY, athlete_status=status, recent_activities=acts or [])


BLOCK = "- 15m 70% LTHR\n3x\n- 6m 98% LTHR\n- 2m 70% LTHR\n"
LONG_BLOCK = "- 20m 70% LTHR\n- 20m 98% LTHR\n- 30m 70% LTHR\n"
LONG_Z2 = "- 100m 70% LTHR\n"


# ───────────────────────── configuration ─────────────────────────

def test_parse_defaults_and_empty_keys():
    r = parse_load_rules("")
    assert r["session_spike_warn_pct"] == 10
    assert r["quality_runs_max_7d"] is None and r["deload_every_n_weeks"] is None
    r = parse_load_rules("quality_runs_max_7d:\nsession_spike_warn_pct:\n")
    assert r["quality_runs_max_7d"] is None
    assert r["session_spike_warn_pct"] is None  # present but empty = off


def test_parse_markdown_bold_and_comment_forms():
    r = parse_load_rules("- **deload_every_n_weeks:** 4\nquality_runs_max_7d: 2   # decision\n")
    assert r["deload_every_n_weeks"] == 4 and r["quality_runs_max_7d"] == 2


# ───────────────────────── quality definition ─────────────────────────

def test_pure_z2_long_run_is_not_quality_in_block_mode():
    assert not is_quality_run(_plan(100, intervals_icu=LONG_Z2), "block")


def test_long_run_with_embedded_block_counts():
    assert is_quality_run(_plan(110, intervals_icu=LONG_BLOCK), "block")


def test_long_run_with_short_block_does_not_count():
    short = "- 80m 70% LTHR\n- 10m 98% LTHR\n- 10m 70% LTHR\n"
    assert not is_quality_run(_plan(100, intervals_icu=short), "block")


def test_long_run_mode_all_and_none():
    assert is_quality_run(_plan(100, intervals_icu=LONG_Z2), "all")
    assert not is_quality_run(_plan(110, intervals_icu=LONG_BLOCK), "none")


def test_threshold_session_and_race_count_strides_do_not():
    assert is_quality_run(_plan(60, intervals_icu=BLOCK))
    assert is_quality_run(_plan(40, tags=["race"]))
    strides = "- 20m 70% LTHR\n6x\n- 20s 110% LTHR\n- 60s 60% LTHR\n"
    assert not is_quality_run(_plan(30, intervals_icu=strides))


# ───────────────────────── R033 ─────────────────────────

def test_r033_warns_above_threshold_never_error():
    acts = [_act("2025-03-09", 100)]
    out = check_session_spike_vs_30d_longest([_plan(120)], _ctx(acts=acts))
    assert [f.severity for f in out] == ["WARNING"]
    assert "> 10-30 %" in out[0].message and "proxy" in out[0].message


def test_r033_big_spike_stays_warning_and_names_band():
    out = check_session_spike_vs_30d_longest([_plan(250)], _ctx(acts=[_act("2025-03-09", 100)]))
    assert out[0].severity == "WARNING" and "> 100 %" in out[0].message


def test_r033_within_threshold_is_silent():
    assert check_session_spike_vs_30d_longest([_plan(110)], _ctx(acts=[_act("2025-03-09", 100)])) == []


def test_r033_ack_and_race_are_info():
    acts = [_act("2025-03-09", 100)]
    acked = _plan(130, coaching_notes="[spike-ok: race rehearsal]")
    assert check_session_spike_vs_30d_longest([acked], _ctx(acts=acts))[0].severity == "INFO"
    race = _plan(130, tags=["race"])
    assert check_session_spike_vs_30d_longest([race], _ctx(acts=acts))[0].severity == "INFO"


def test_r033_no_run_in_30_days_is_info():
    old = [_act("2025-01-01", 100)]
    out = check_session_spike_vs_30d_longest([_plan(60)], _ctx(acts=old))
    assert [f.severity for f in out] == ["INFO"]


def test_r033_switch_off_and_distance_preferred():
    assert check_session_spike_vs_30d_longest(
        [_plan(200)], _ctx("session_spike_warn_pct:\n", [_act("2025-03-09", 100)])) == []
    acts = [_act("2025-03-09", 100, distance_km=20)]
    out = check_session_spike_vs_30d_longest([_plan(100, distance_km=24)], _ctx(acts=acts))
    assert "distance" in out[0].message


def test_r033_default_on_without_key_but_today_excluded():
    # key absent -> default 10 %; a run done today is not its own baseline
    acts = [_act(TODAY, 200)]
    out = check_session_spike_vs_30d_longest([_plan(60)], _ctx("", acts))
    assert [f.severity for f in out] == ["INFO"]


# ───────────────────────── R034 ─────────────────────────

def test_r034_off_without_key():
    assert check_quality_run_density([_plan(60, intervals_icu=BLOCK)], _ctx("")) == []


def test_r034_third_quality_run_in_7d_errors():
    acts = [_act("2025-03-11", 60, tags=["intervals"]), _act("2025-03-14", 60, tags=["intervals"])]
    out = check_quality_run_density([_plan(60, intervals_icu=BLOCK)], _ctx(acts=acts))
    assert out and out[0].severity == "ERROR" and "3 quality runs" in out[0].message


def test_r034_spacing_violation_errors_with_two_runs_only():
    acts = [_act("2025-03-16", 60, tags=["intervals"])]
    out = check_quality_run_density([_plan(60, intervals_icu=BLOCK)], _ctx(acts=acts))
    assert out and out[0].severity == "ERROR" and "to the quality run" in out[0].message


def test_r034_two_runs_with_enough_spacing_pass():
    acts = [_act("2025-03-13", 60, tags=["intervals"])]
    assert check_quality_run_density([_plan(60, intervals_icu=BLOCK)], _ctx(acts=acts)) == []


def test_r034_easy_plan_and_z2_long_run_do_not_fire():
    acts = [_act("2025-03-16", 60, tags=["intervals"]), _act("2025-03-15", 60, tags=["intervals"])]
    assert check_quality_run_density([_plan(50)], _ctx(acts=acts)) == []
    assert check_quality_run_density([_plan(100, intervals_icu=LONG_Z2)], _ctx(acts=acts)) == []


def test_r034_severity_warning_when_configured():
    status = STATUS_ON.replace("quality_density_severity: error", "quality_density_severity: warning")
    acts = [_act("2025-03-16", 60, tags=["intervals"])]
    out = check_quality_run_density([_plan(60, intervals_icu=BLOCK)], _ctx(status, acts))
    assert out[0].severity == "WARNING"


# ───────────────────────── deloadDue / R035 ─────────────────────────

def _weeks(minutes_by_week_back: dict[int, int]) -> list[dict]:
    """Runs placed in completed weeks; key k = k weeks before the current week."""
    monday = date.fromisoformat(TODAY)
    acts = []
    for k, mins in minutes_by_week_back.items():
        day = (monday - timedelta(weeks=k) + timedelta(days=2)).isoformat()
        acts.append(_act(day, mins))
    return acts


FLAT = {k: 200 for k in range(1, 8)}
START = date.fromisoformat(TODAY) - timedelta(days=75)


def _due(acts, **kw):
    return compute_deload_due(acts, date.fromisoformat(TODAY), every_n_weeks=3,
                              history_start=START, **kw)


def test_due_after_three_build_weeks():
    d = _due(_weeks(FLAT))
    assert d["due"] is True and d["weeks_since_last_reduction"] == 3


def test_reduction_week_resets_counter():
    d = _due(_weeks({**FLAT, 2: 130}))  # 130 <= 70 % of 200
    assert d["due"] is False and d["weeks_since_last_reduction"] == 1


def test_week_just_above_threshold_is_not_a_reduction():
    d = _due(_weeks({**FLAT, 2: 150}))  # 75 % -> still a build week
    assert d["due"] is True


def test_illness_week_counts_as_deload_whatever_the_reason():
    d = _due(_weeks({**FLAT, 1: 0}))
    assert d["due"] is False and d["weeks_since_last_reduction"] == 0


def test_history_too_short_is_reported_not_due():
    short = compute_deload_due(_weeks(FLAT), date.fromisoformat(TODAY), every_n_weeks=3,
                               history_start=date.fromisoformat(TODAY) - timedelta(days=28))
    assert short["due"] is False and short["history_complete"] is False


def test_recovery_block_flagged_active():
    state = {"active": "yes", "planned_end": "2025-03-23"}
    assert _due(_weeks(FLAT), deload_state=state)["recovery_week_active"] is True


def _r035_ctx(status=STATUS_ON, extra=""):
    ctx = _ctx(status + extra)
    ctx.load_history_activities = _weeks(FLAT)
    return ctx


def test_r035_quality_run_in_due_week_errors():
    out = check_deload_due([_plan(60, intervals_icu=BLOCK)], _r035_ctx())
    assert out and out[0].severity == "ERROR" and out[0].rule_id == "R035"


def test_r035_long_run_in_due_week_errors_even_when_pure_z2():
    out = check_deload_due([_plan(100, intervals_icu=LONG_Z2)], _r035_ctx())
    assert out and out[0].severity == "ERROR"


def test_r035_easy_run_is_fine():
    assert check_deload_due([_plan(45)], _r035_ctx()) == []


def test_r035_recovery_block_silences_it():
    block = "\n## Recovery week status\n- **active:** yes\n- **planned end:** 2025-03-23\n"
    assert check_deload_due([_plan(60, intervals_icu=BLOCK)], _r035_ctx(extra=block)) == []


def test_r035_off_without_key_and_warning_severity():
    assert check_deload_due([_plan(60, intervals_icu=BLOCK)], _r035_ctx("")) == []
    status = STATUS_ON.replace("deload_severity: error", "deload_severity: warning")
    out = check_deload_due([_plan(60, intervals_icu=BLOCK)], _r035_ctx(status))
    assert out[0].severity == "WARNING"


def test_context_field_none_when_not_configured(monkeypatch):
    from app.graphs.sub_athlete_context import context_builder as cb
    monkeypatch.setattr(cb, "_read_optional_config", lambda name: "")
    assert cb._compute_deload_due_field([], date.fromisoformat(TODAY), {}) is None
    monkeypatch.setattr(cb, "_read_optional_config", lambda name: STATUS_ON)
    out = cb._compute_deload_due_field(_weeks(FLAT), date.fromisoformat(TODAY), {})
    assert out["due"] is True
    line = cb._append_deload_due_line("No restrictions", out)
    assert "CALENDAR DELOAD DUE" in line and "No restrictions" not in line
