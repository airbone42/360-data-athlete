"""Tests for validate_plan.py rule registry + degraded-context surfacing.

Covers two review findings:
- F5-01: the Weekly-Hard-Reize cap shared rule id R009 with
  check_hr_range_consistency, and `--rule` selection matched docstring
  substrings instead of registry ids. The registry is now explicit
  (rule_id, fn) pairs — ids must stay unique.
- F2-04: load_context() wrapped every remote fetch in a bare
  `except Exception` with empty defaults, so R004/R006/R014/R017
  silently self-deactivated on API hiccups. Failed sources now surface
  as VALIDATOR WARNINGs in the validation output (still fail-soft).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Make the scripts/ directory importable.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scripts.validate_plan as vp  # type: ignore  # noqa: E402
from scripts.validate_plan import (  # type: ignore  # noqa: E402
    RULES,
    Context,
    check_hr_range_consistency,
    check_weekly_hardreize_cap,
    load_context,
    run_validation,
)


# ─── Registry shape (F5-01) ──────────────────────────────────────────────

def test_rule_ids_unique():
    """Every registry entry carries a distinct rule_id — no R009-style collision."""
    ids = [rule_id for rule_id, _ in RULES]
    assert len(ids) == len(set(ids)), f"duplicate rule ids: {ids}"


def test_rule_ids_follow_convention():
    for rule_id, _ in RULES:
        assert re.fullmatch(r"R\d{3}", rule_id), f"unexpected rule id: {rule_id}"


def test_collision_resolved_r009_vs_r017():
    """HR-range consistency keeps R009; the Hard-Reize cap moved to R017."""
    registry = dict(RULES)
    assert registry["R009"] is check_hr_range_consistency
    assert registry["R017"] is check_weekly_hardreize_cap


def test_rule_functions_unique():
    fns = [fn for _, fn in RULES]
    assert len(fns) == len(set(fns))


# ─── --rule selection (F5-01) ────────────────────────────────────────────

def _run_without_surface() -> dict:
    """Triggers R003 (missing surface, ERROR) but no other rule."""
    return {
        "type": "Run",
        "name": "Easy Z2",
        "workout_type": "EASY",
        "intervals_icu": "- 40m Z2 HR",
        "description": "Locker laufen.",
    }


def test_only_rule_selects_by_registry_id():
    findings = run_validation([_run_without_surface()], Context(target_date="2025-05-23"), only_rule="R003")
    assert findings
    assert all(f.rule_id == "R003" for f in findings)


def test_only_rule_is_case_and_whitespace_tolerant():
    findings = run_validation([_run_without_surface()], Context(target_date="2025-05-23"), only_rule=" r003 ")
    assert findings
    assert all(f.rule_id == "R003" for f in findings)


def test_only_rule_no_substring_match():
    """An id that is a substring of messages/docstrings must not select rules."""
    findings = run_validation([_run_without_surface()], Context(target_date="2025-05-23"), only_rule="R999")
    assert findings == []


# ─── Degraded-context surfacing (F2-04) ──────────────────────────────────

def _boom(*_args, **_kwargs):
    raise ConnectionError("intervals.icu unreachable (synthetic)")


def test_load_context_failed_fetches_surface_as_warnings(monkeypatch):
    """Each failed remote source yields one VALIDATOR WARNING naming the
    impacted rule — instead of silently self-deactivating it."""
    monkeypatch.setattr(vp, "_read_config", lambda _path: "")
    monkeypatch.setattr(vp, "_load_injury_locks", lambda: {})
    monkeypatch.setattr(vp, "_fetch_recent_notes", _boom)
    monkeypatch.setattr(vp, "_fetch_sport_settings", _boom)
    monkeypatch.setattr(vp, "_fetch_recent_activities", _boom)
    monkeypatch.setattr(vp, "_fetch_raw_activities_for_hardreize", _boom)

    ctx = load_context("2025-05-23", fetch_remote=True)

    # Fail-soft: context fields keep their empty defaults.
    assert ctx.recent_notes == []
    assert ctx.sport_settings == []
    assert ctx.recent_activities == []
    assert ctx.weekly_hard_reize_balance == ""

    assert len(ctx.load_warnings) == 4
    messages = [w.message for w in ctx.load_warnings]
    for impacted in ("R004", "R006", "R014", "R017"):
        assert any(impacted in m for m in messages), f"{impacted} not surfaced: {messages}"
    for w in ctx.load_warnings:
        assert w.rule_id == "VALIDATOR"
        assert w.severity == "WARNING"
        assert "fetch failed" in w.message
        assert "intervals.icu unreachable (synthetic)" in w.message


def test_run_validation_emits_load_warnings(monkeypatch):
    """Degraded-context warnings reach the validator output (and survive --rule)."""
    monkeypatch.setattr(vp, "_read_config", lambda _path: "")
    monkeypatch.setattr(vp, "_load_injury_locks", lambda: {})
    monkeypatch.setattr(vp, "_fetch_recent_notes", _boom)
    monkeypatch.setattr(vp, "_fetch_sport_settings", _boom)
    monkeypatch.setattr(vp, "_fetch_recent_activities", _boom)
    monkeypatch.setattr(vp, "_fetch_raw_activities_for_hardreize", _boom)

    ctx = load_context("2025-05-23", fetch_remote=True)
    findings = run_validation([], ctx)
    validator_warnings = [f for f in findings if f.rule_id == "VALIDATOR"]
    assert len(validator_warnings) == 4

    # Warnings are not filtered away by --rule selection either.
    findings = run_validation([], ctx, only_rule="R003")
    assert len([f for f in findings if f.rule_id == "VALIDATOR"]) == 4


def test_load_context_no_remote_no_warnings(monkeypatch):
    """Offline mode (--no-remote) is an acknowledged state — no degradation warnings."""
    monkeypatch.setattr(vp, "_read_config", lambda _path: "")
    monkeypatch.setattr(vp, "_load_injury_locks", lambda: {})
    ctx = load_context("2025-05-23", fetch_remote=False)
    assert ctx.load_warnings == []
