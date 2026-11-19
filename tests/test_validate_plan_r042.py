"""Tests for validate_plan.py R042 (external session already covers a planned block)."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scripts.validate_plan as vp  # type: ignore  # noqa: E402
from scripts.validate_plan import (  # type: ignore  # noqa: E402
    RULES,
    Context,
    check_external_coverage,
    load_context,
    run_validation,
)

COVERAGE = {
    "sessions": [
        {"match": "^gym hall", "tags_any": ["hall"], "covers": ["core"], "label": "gym hall"},
        {"match": "^gym hall", "tags_any": ["hall"], "covers": ["mobility"],
         "workout_match": "shoulder", "label": "gym hall"},
        {"tags_any": ["therapy"], "covers": ["mobility"], "workout_match": "shoulder",
         "label": "therapy"},
        {"match": "physio.?class", "covers": ["core", "mobility", "upperbody"],
         "label": "physio class"},
    ]
}


def _entries(tmp_path, monkeypatch, data=COVERAGE) -> list[dict]:
    cfg = tmp_path / "config"
    cfg.mkdir(exist_ok=True)
    (cfg / "external_coverage.json").write_text(json.dumps(data))
    import app.utils.paths as paths
    monkeypatch.setattr(paths, "CONFIG_DIR", cfg)
    return vp._load_external_coverage()


def _ctx(entries, events=None, appointments=None) -> Context:
    return Context(
        target_date="2026-11-17",
        external_coverage=entries,
        day_calendar_events=events,
        day_appointments=appointments,
    )


def _core(name="Core block D") -> dict:
    return {"type": "WeightTraining", "name": name, "tags": ["core"], "description": "Plank 3x45s"}


def _shoulder_mobility(name="Shoulder mobility + breathing") -> dict:
    return {"type": "Workout", "name": name, "tags": ["mobility"], "description": "Wall slide 2x10"}


def test_r042_registered():
    assert [rid for rid, _ in RULES].count("R042") == 1


def test_physio_class_appointment_covers_planned_core(tmp_path, monkeypatch):
    entries = _entries(tmp_path, monkeypatch)
    appt = {"title": "Physio class", "start": "2026-11-17T19:00", "categories": ["THERAPY"]}
    f = check_external_coverage([_core()], _ctx(entries, events=[], appointments=[appt]))
    assert [x.rule_id for x in f] == ["R042"]
    assert f[0].severity == "WARNING"
    assert "'core'" in f[0].message and "physio class" in f[0].message


def test_hall_event_covers_planned_shoulder_mobility(tmp_path, monkeypatch):
    entries = _entries(tmp_path, monkeypatch)
    hall = {"name": "Gym hall", "tags": ["hall"], "description": ""}
    f = check_external_coverage(
        [_shoulder_mobility(), _core()], _ctx(entries, events=[hall], appointments=[])
    )
    assert sorted(x.workout for x in f) == ["Core block D", "Shoulder mobility + breathing"]
    assert all(x.severity == "WARNING" for x in f)


def test_workout_match_keeps_other_mobility_blocks_clear(tmp_path, monkeypatch):
    """A hip mobility block is not the shoulder mobility the hall covers."""
    entries = _entries(tmp_path, monkeypatch)
    hall = {"name": "Gym hall", "tags": ["hall"], "description": ""}
    hip = {"type": "Workout", "name": "Hip mobility", "tags": ["mobility"], "description": "90/90"}
    assert check_external_coverage([hip], _ctx(entries, events=[hall], appointments=[])) == []


def test_therapy_event_by_tag_covers_shoulder_mobility(tmp_path, monkeypatch):
    entries = _entries(tmp_path, monkeypatch)
    therapy = {"name": "Manual therapy shoulder", "tags": ["mobility", "therapy"], "description": ""}
    f = check_external_coverage([_shoulder_mobility()], _ctx(entries, events=[therapy]))
    assert [x.rule_id for x in f] == ["R042"]
    # The therapy session does not cover core.
    assert check_external_coverage([_core()], _ctx(entries, events=[therapy])) == []


def test_repush_of_the_same_planned_workout_does_not_warn(tmp_path, monkeypatch):
    """The plan's own event from an earlier push is not an external session."""
    entries = _entries(tmp_path, monkeypatch)
    earlier = {"name": "Shoulder mobility + breathing", "tags": ["mobility", "therapy"],
               "description": "Wall slide 2x10"}
    assert check_external_coverage(
        [_shoulder_mobility()], _ctx(entries, events=[earlier], appointments=[])
    ) == []


def test_coach_marked_event_is_not_external(tmp_path, monkeypatch):
    entries = _entries(tmp_path, monkeypatch)
    coach = {"name": "Gym hall warm-up run", "tags": ["hall"],
             "description": "- 20m Z2\n[coach-plan:surface=road]"}
    assert check_external_coverage([_core()], _ctx(entries, events=[coach])) == []


def test_planned_blocker_for_the_external_session_is_not_flagged(tmp_path, monkeypatch):
    """The coach's own empty time block for the hall carries the hall tags but
    is the external session itself, not a duplicate of it."""
    entries = _entries(tmp_path, monkeypatch)
    hall_sync = {"name": "Gym hall", "tags": ["hall"], "description": ""}
    blocker = {"type": "Workout", "name": "Gym hall evening", "tags": ["hall", "core"], "description": ""}
    assert check_external_coverage([blocker], _ctx(entries, events=[hall_sync])) == []


def test_no_config_no_warning(tmp_path, monkeypatch):
    import app.utils.paths as paths
    monkeypatch.setattr(paths, "CONFIG_DIR", tmp_path / "missing")
    monkeypatch.setattr(paths, "CONFIG_FALLBACK", tmp_path / "missing-too")
    assert vp._load_external_coverage() == []
    appt = {"title": "Physio class", "categories": []}
    hall = {"name": "Gym hall", "tags": ["hall"], "description": ""}
    ctx = _ctx([], events=[hall], appointments=[appt])
    assert check_external_coverage([_core(), _shoulder_mobility()], ctx) == []


def test_framework_default_config_keeps_rule_off():
    """config.example ships an empty list — a fresh install never fires R042."""
    data = json.loads((ROOT / "config.example" / "external_coverage.json").read_text())
    assert data["sessions"] == []


def test_loader_drops_invalid_entries(tmp_path, monkeypatch):
    entries = _entries(tmp_path, monkeypatch, {"sessions": [
        {"match": "(", "covers": ["core"]},          # invalid regex
        {"covers": ["core"]},                        # no session selector
        {"match": "x"},                              # no covers
        {"tags_any": ["Hall"], "covers": ["Core"]},  # valid, lower-cased
    ]})
    assert len(entries) == 1
    assert entries[0]["covers"] == ["core"] and entries[0]["tags_any"] == ["hall"]


def test_load_context_skips_fetch_without_config(monkeypatch):
    """Rule off → no extra remote calls and no degraded warning for R042."""
    def _boom(*_a, **_k):
        raise AssertionError("must not fetch")
    monkeypatch.setattr(vp, "_load_external_coverage", lambda: [])
    for fn in ("_fetch_recent_notes", "_fetch_sport_settings", "_fetch_recent_activities",
               "_fetch_ctl", "_fetch_raw_activities_for_hardreize", "_fetch_race_days_ahead",
               "_fetch_tomorrow_workouts"):
        async def _empty(*_a, **_k):
            return []
        monkeypatch.setattr(vp, fn, _empty)
    monkeypatch.setattr(vp, "_fetch_day_workout_events", _boom)
    monkeypatch.setattr(vp, "_fetch_day_appointments", _boom)
    ctx = load_context("2026-11-17", fetch_remote=True)
    assert ctx.day_calendar_events is None and ctx.day_appointments is None
    assert not any("R042" in w.message for w in ctx.load_warnings)


def test_unavailable_agenda_feed_raises_for_degraded_warning(monkeypatch):
    import app.api.agenda_feed as af

    async def _down(*_a, **_k):
        return {"appointments": [], "warnings": [f"{af.UNAVAILABLE_PREFIX} (timeout)"]}

    monkeypatch.setattr(af, "fetch_agenda", _down)
    try:
        asyncio.run(vp._fetch_day_appointments("2026-11-17"))
    except RuntimeError as exc:
        assert "timeout" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected RuntimeError")


def test_feed_off_returns_empty_list(monkeypatch):
    import app.api.agenda_feed as af

    async def _off(*_a, **_k):
        return {"appointments": [], "warnings": []}

    monkeypatch.setattr(af, "fetch_agenda", _off)
    assert asyncio.run(vp._fetch_day_appointments("2026-11-17")) == []


def test_run_validation_reports_r042_as_warning_only(tmp_path, monkeypatch):
    entries = _entries(tmp_path, monkeypatch)
    appt = {"title": "Physio class", "categories": []}
    findings = run_validation([_core()], _ctx(entries, events=[], appointments=[appt]), only_rule="R042")
    assert [f.rule_id for f in findings] == ["R042"]
    assert all(f.severity != "ERROR" for f in findings)
