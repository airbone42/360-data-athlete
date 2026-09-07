"""Tests for orientation detection — the step ahead of every structural claim.

Motivating case: a phone clip carried ``displaymatrix: rotation of 90.00
degrees``; the detector read it through PyAV, whose ``stream.side_data`` is
``None`` on PyAV 17 whatever the file contains, and returned 0. The failure was
silent, so the stills reached the structure pass lying on their side — and a
sideways frame is precisely the input that produces confident wrong contact
points and swapped anatomical sides, the failure class the structure pass
exists to prevent. The detector must therefore read the value from ffmpeg, a
hard dependency of the module, and it must read it with the right sign: the
printed angle is already the counter-clockwise correction.

A truncated model answer is the other silent failure guarded here. The models
are thinking models and ``max_tokens`` caps reasoning plus answer, so a budget
that looks generous against the JSON alone truncates mid-object — which used to
surface as a JSON parse error whose handler advised shrinking the video, the one
remedy that cannot help.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.analyse_video import (  # type: ignore  # noqa: E402
    MAX_TOKENS,
    MODELS,
    _detect_metadata_rotation,
    _first_choice_content,
)


class _Completed:
    def __init__(self, stderr: str) -> None:
        self.stderr = stderr.encode()
        self.stdout = b""
        self.returncode = 1


def _dump(rotation_line: str = "") -> str:
    body = (
        "  Duration: 00:00:50.97, start: 0.000000, bitrate: 3176 kb/s\n"
        "  Stream #0:0[0x1](eng): Video: h264 (High), 1920x1080, 30 fps\n"
    )
    return body + rotation_line


@pytest.fixture
def _ffmpeg(monkeypatch):
    monkeypatch.setattr("scripts.analyse_video._ffmpeg_exe", lambda: "/usr/bin/ffmpeg")
    return monkeypatch


@pytest.mark.parametrize(
    "printed, expected",
    [
        ("90.00", 90),    # portrait clip needing one 90° CCW transpose
        ("-90.00", 270),  # the mirror case: 90° CW
        ("180.00", 180),
        ("0.00", 0),
    ],
)
def test_rotation_read_from_ffmpeg_dump(_ffmpeg, monkeypatch, printed, expected):
    """The printed display-matrix angle IS the CCW correction — no sign flip."""
    line = f"      Side data:\n        displaymatrix: rotation of {printed} degrees\n"
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Completed(_dump(line)))
    assert _detect_metadata_rotation("clip.mp4") == expected


def test_no_display_matrix_reports_zero(_ffmpeg, monkeypatch):
    """A clip whose content is sideways without a flag needs explicit --rotate."""
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Completed(_dump()))
    assert _detect_metadata_rotation("clip.mp4") == 0


def test_unparseable_angle_does_not_crash(_ffmpeg, monkeypatch):
    line = "        displaymatrix: rotation of 42.50 degrees\n"
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Completed(_dump(line)))
    # 42.5° is not a valid transpose chain — fall through rather than guess.
    assert _detect_metadata_rotation("clip.mp4") == 0


def test_budget_covers_reasoning_tokens():
    """Observed: 3839 reasoning tokens before the first character of JSON."""
    assert set(MAX_TOKENS) == set(MODELS)
    assert min(MAX_TOKENS.values()) > 4000


class _Choice:
    def __init__(self, content, finish_reason):
        self.message = type("M", (), {"content": content})()
        self.finish_reason = finish_reason


class _Response:
    def __init__(self, content, finish_reason="stop", completion_tokens=10):
        self.choices = [_Choice(content, finish_reason)]
        self.usage = type("U", (), {"completion_tokens": completion_tokens})()


def test_truncated_answer_names_the_budget_not_the_video():
    with pytest.raises(RuntimeError) as err:
        _first_choice_content(_Response('{"aufnahme": {', "length", 3996), "m", "Stage A")
    message = str(err.value)
    assert "max_tokens" in message and "3996" in message
    assert "kürzen hilft hier nicht" in message


def test_complete_answer_passes_through():
    assert _first_choice_content(_Response("ok"), "m", "Stage A") == "ok"


@pytest.mark.parametrize("response", [_Response(None), _Response("")])
def test_empty_content_still_raises(response):
    with pytest.raises(RuntimeError):
        _first_choice_content(response, "m", "Stage B")
