"""Tests for validate_plan.py R021 — strides repeat-block within-block ordering.

R021 turns the athlete-configured ``stride_block_order`` (recovery-first vs
stride-first) into a hard push-time gate, so the order can no longer regress
to LLM discretion. It is a no-op when the config key is absent (framework
default: order unconstrained). Synthetic fixtures only.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import (  # type: ignore  # noqa: E402
    Context,
    SEVERITY_ERROR,
    check_stride_block_order,
)

STATUS_RECOVERY_FIRST = "stride_block_order: recovery-first\n"
STATUS_MARKDOWN = "- **stride_block_order:** recovery-first\n"  # bold-markdown form
STATUS_STRIDE_FIRST = "stride_block_order: stride-first\n"

_STRIDE_FIRST_ICU = (
    "Main\n- 40m 76-82% LTHR\n\n"
    "Strides 4x\n- Stride 20s\n- Easy 90s Z1 HR\n\n"
    "Cool-down\n- Cool-down 5m press lap"
)
_RECOVERY_FIRST_ICU = (
    "Main\n- 40m 76-82% LTHR\n\n"
    "Strides 4x\n- Easy 90s Z1 HR\n- Stride 20s\n\n"
    "Cool-down\n- Cool-down 5m press lap"
)


def _ctx(athlete_status: str) -> Context:
    return Context(target_date="2025-05-23", athlete_status=athlete_status)


def _run(icu: str) -> dict:
    return {"type": "Run", "name": "Easy Z2", "workout_type": "EASY", "intervals_icu": icu}


def test_recovery_first_pref_flags_stride_first_block() -> None:
    findings = check_stride_block_order([_run(_STRIDE_FIRST_ICU)], _ctx(STATUS_RECOVERY_FIRST))
    assert len(findings) == 1
    assert findings[0].rule_id == "R021"
    assert findings[0].severity == SEVERITY_ERROR


def test_recovery_first_pref_accepts_recovery_first_block() -> None:
    assert check_stride_block_order([_run(_RECOVERY_FIRST_ICU)], _ctx(STATUS_RECOVERY_FIRST)) == []


def test_markdown_bold_key_is_parsed() -> None:
    # The wrapper writes the key as `- **stride_block_order:** recovery-first`.
    findings = check_stride_block_order([_run(_STRIDE_FIRST_ICU)], _ctx(STATUS_MARKDOWN))
    assert len(findings) == 1


def test_stride_first_pref_flags_recovery_first_block() -> None:
    findings = check_stride_block_order([_run(_RECOVERY_FIRST_ICU)], _ctx(STATUS_STRIDE_FIRST))
    assert len(findings) == 1


def test_no_key_is_noop() -> None:
    assert check_stride_block_order([_run(_STRIDE_FIRST_ICU)], _ctx("no ordering configured\n")) == []


def test_non_stride_repeat_block_ignored() -> None:
    # A VO2max work-interval set carries no Stride item and may legitimately be
    # work-first — R021 must not touch it.
    vo2 = "Set 4x\n- Work 30s 360W 100rpm\n- Recovery 15s 180W"
    assert check_stride_block_order([_run(vo2)], _ctx(STATUS_RECOVERY_FIRST)) == []
