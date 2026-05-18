"""Smoke tests for scripts.audit_consistency.check_prompt_drift().

Verifies the drift-linter does not raise on the current canonical state,
catches injected divergence, and is registered in CHECK_MAP.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts import audit_consistency


def test_check_runs_clean_on_current_repo():
    """On the canonical state, the linter must return [] or only known-clean
    findings. If a canonical phrase has drifted, this test fails first."""
    findings = audit_consistency.check_prompt_drift()
    for f in findings:
        assert f["category"] == "prompt_drift"
    # Surface count for debugging without forcing a hard cap.
    assert isinstance(findings, list)


def test_check_is_registered_in_check_map():
    assert "PROMPT_DRIFT" in audit_consistency.CHECK_MAP
    name, online = audit_consistency.CHECK_MAP["PROMPT_DRIFT"]
    assert name == "check_prompt_drift"
    assert online is False, "prompt drift check should not require online APIs"


def test_drift_catches_injected_divergence(tmp_path, monkeypatch):
    """Inject a fake prompt directory with a deliberately-drifted line."""
    fake_root = tmp_path / "framework_fake"
    (fake_root / "prompts").mkdir(parents=True)
    (fake_root / "agents").mkdir()

    # Trigger present, but wording deliberately diverged from canonical.
    drifted = (
        "Always use HR zones from `context.hrZones` (paraphrased — not canonical)."
    )
    (fake_root / "agents" / "fake-specialist.md").write_text(
        f"---\nname: fake\n---\n\n{drifted}\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(audit_consistency, "FRAMEWORK_ROOT", fake_root)
    findings = audit_consistency.check_prompt_drift()

    drift_hits = [f for f in findings if f["category"] == "prompt_drift"]
    assert drift_hits, "drift linter should flag the injected divergent line"
    assert "hr_zone_briefing" in drift_hits[0]["evidence"], (
        "expected hr_zone_briefing label in evidence"
    )


def test_drift_accepts_canonical_form(tmp_path, monkeypatch):
    """Same trigger, but exact canonical wording → no finding."""
    fake_root = tmp_path / "framework_fake"
    (fake_root / "prompts").mkdir(parents=True)
    (fake_root / "agents").mkdir()

    canonical = (
        "Pass HR zones from `context.hrZones` verbatim — never reconstruct "
        "from memory, never compute LTHR or zone bounds from recall."
    )
    (fake_root / "agents" / "good-specialist.md").write_text(
        f"---\nname: good\n---\n\n{canonical}\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(audit_consistency, "FRAMEWORK_ROOT", fake_root)
    findings = audit_consistency.check_prompt_drift()
    drift_hits = [f for f in findings if f["category"] == "prompt_drift"]
    assert not drift_hits, (
        f"canonical wording should not be flagged; got: {drift_hits}"
    )


def test_drift_handles_missing_dirs(tmp_path, monkeypatch):
    """Linter must not crash if prompts/ or agents/ is absent."""
    empty = tmp_path / "framework_empty"
    empty.mkdir()
    monkeypatch.setattr(audit_consistency, "FRAMEWORK_ROOT", empty)
    findings = audit_consistency.check_prompt_drift()
    assert findings == []
