"""Regression test for the hardcoded-restrictions scan path resolution.

The scan previously globbed `.claude/agents/*.md` under FRAMEWORK_ROOT —
a directory that does not exist in this repo (agent definitions live at
`agents/`). The check then silently scanned zero agent files. This test
pins the corrected layout: the resolved scan set must contain agent
files from `agents/` in this repository.
"""
from __future__ import annotations

from scripts import audit_consistency as ac


def test_agent_files_collected_nonempty() -> None:
    """The hardcode scan must pick up the agent definitions in agents/."""
    rels = [rel for _path, rel in ac._hardcode_scan_paths()]
    agent_rels = [r for r in rels if r.startswith("agents/")]
    assert agent_rels, (
        "hardcoded-restrictions scan resolved zero agent files — "
        "HARDCODE_SCAN_GLOBS no longer matches the agents/ layout"
    )


def test_scan_excludes_audit_meta_agents() -> None:
    """config-auditor/config-fixer describe the audit itself — excluded."""
    rels = {rel for _path, rel in ac._hardcode_scan_paths()}
    assert "agents/config-auditor.md" not in rels
    assert "agents/config-fixer.md" not in rels


def test_scan_paths_are_posix_relative() -> None:
    """Exclude matching relies on posix-style relative paths (no backslashes)."""
    for _path, rel in ac._hardcode_scan_paths():
        assert "\\" not in rel, f"non-posix relative path in scan set: {rel!r}"
