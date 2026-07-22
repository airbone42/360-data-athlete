"""Tests for HR-target recognition in the intervals.icu step linter.

%LTHR is the preferred target form — intervals.icu resolves it to concrete
bpm, which the watch follows verbatim, whereas "Zn HR" resolves against the
watch's own zone model and is deprecated. The linter must therefore accept
%LTHR as a valid target, or every correctly-written step reports as
target-less and the warning becomes noise that hides real findings.
"""
from __future__ import annotations

import pytest

from app.utils.intervals_icu_linter import validate_intervals_icu


def _hr_target_errors(text: str) -> list[str]:
    return [e for e in validate_intervals_icu(text) if "without HR target" in e]


@pytest.mark.parametrize(
    "step",
    [
        "- Easy 20m 68-75% LTHR",
        "- Steady 15m 72-80% LTHR",
        "- Threshold 10m 95% LTHR",
        "- Easy 20m 68 - 75 % LTHR",
        "- Easy 20m 68–75% lthr",
    ],
)
def test_lthr_percent_counts_as_hr_target(step: str) -> None:
    assert _hr_target_errors(f"Main\n{step}") == []


@pytest.mark.parametrize(
    "step",
    [
        "- Easy 20m Z2 HR",
        "- Threshold 5m 154-166 HR",
        "- Easy 20m <140 bpm",
        "- Easy 8m press lap",
    ],
)
def test_existing_target_forms_still_accepted(step: str) -> None:
    assert _hr_target_errors(f"Main\n{step}") == []


@pytest.mark.parametrize(
    "step",
    [
        "- Trabpause 100s",
        "- A-Skips 60s — bewusst langsam",
    ],
)
def test_target_less_long_step_still_flagged(step: str) -> None:
    # The widened pattern must not swallow the real finding it exists for.
    assert len(_hr_target_errors(f"Main\n{step}")) == 1


def test_lthr_target_on_short_step_is_flagged() -> None:
    # Steps under 60s carry no HR target; now that %LTHR is recognised, the
    # short-step rule sees it too.
    errors = validate_intervals_icu("Main\n- Stride 20s 95% LTHR")
    assert any("should not have an HR target" in e for e in errors)


def test_percent_without_lthr_is_not_a_target() -> None:
    # A bare percentage (e.g. an effort or grade note) is not an HR target.
    assert len(_hr_target_errors("Main\n- Bergauf 3m 8% Steigung")) == 1
