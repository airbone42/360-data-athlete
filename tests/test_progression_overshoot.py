"""Regression tests for the PROGRESSION_OVERSHOOT check.

The original bug: `_scannable_lines_from_pool(path)` called
`path.relative_to(ROOT)` only to look at the suffix, but `ROOT` is the
framework root and `resolve_config()` can return a path in the wrapper's
`CONFIG_DIR` (a sibling, not a child of `ROOT`). That made the helper
raise `ValueError` and crashed `check_progression_overshoot()` in any
real two-repo deployment.

Fix: discriminate JSON vs Markdown via `path.suffix` directly, no
`relative_to(ROOT)` involved. These tests pin both that the helper is
crash-free on out-of-tree paths and that the dispatcher itself stays
green when invoked end-to-end on the demo config.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import audit_consistency


def test_scannable_lines_handles_path_outside_framework_root(tmp_path: Path) -> None:
    """Simulate the container's two-repo layout: a JSON pool file lives in a
    directory that is NOT under `audit_consistency.ROOT`. Previously this
    crashed with `ValueError: ... is not in the subpath of ...`.
    """
    outside_root = tmp_path / "wrapper_config"
    outside_root.mkdir()
    pool_path = outside_root / "balance_pool.json"
    pool_path.write_text(
        json.dumps(
            {
                "exercises": [
                    {
                        "name": "Single-leg balance",
                        "description": "30 s pro Bein, Augen zu | Bosu mit Augen zu",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    # Must not raise.
    lines = audit_consistency._scannable_lines_from_pool(pool_path)
    assert isinstance(lines, list)
    # Two pipe-separated entries from the description field.
    flat = " ".join(text for _, text in lines)
    assert "Bein" in flat
    assert "Bosu" in flat


def test_scannable_lines_handles_markdown_outside_root(tmp_path: Path) -> None:
    """Same crash-free guarantee for markdown pool files."""
    outside = tmp_path / "wrapper_config"
    outside.mkdir()
    md_path = outside / "exercise_progressions.md"
    md_path.write_text("# Heading\n\n- Pistol Squat hold 5 s\n- Box Jump knee height\n",
                       encoding="utf-8")

    lines = audit_consistency._scannable_lines_from_pool(md_path)
    assert lines, "expected non-empty lines from a markdown pool"
    assert any("Pistol Squat" in text for _, text in lines)


def test_check_progression_overshoot_runs_without_exception() -> None:
    """End-to-end smoke: the check must complete without raising on the
    current canonical state, regardless of whether it finds anything."""
    findings = audit_consistency.check_progression_overshoot()
    assert isinstance(findings, list)
    for f in findings:
        assert f["category"] == "progression_overshoot"
