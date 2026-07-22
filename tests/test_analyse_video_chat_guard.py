"""Tests for the chat-transport guard on video form checks.

Chat channels re-encode video on upload — resolution drops and compression
artefacts appear. A form check reads joint angles, limb positions and
left/right detail out of single frames, so that loss produces confident
wrong findings rather than no finding. Chat-sourced video is refused; the
athlete uploads the original to COACH_VIDEO_INBOX instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import analyse_video  # noqa: E402


@pytest.mark.parametrize(
    "path",
    [
        "/home/u/.claude/channels/telegram/inbox/123-abc.mp4",
        "/home/u/.claude/channels/whatsapp/inbox/clip.mp4",
        "/var/data/Channels/Inbox/Clip.MP4",  # case-insensitive
        "channels/inbox/relative.mp4",
    ],
)
def test_chat_transport_paths_are_detected(path: str) -> None:
    assert analyse_video.is_chat_transport_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "/data/video_inbox/clip.mp4",
        "/tmp/garmin/activity.mp4",
        "/home/u/videos/inbox_notes.mp4",  # 'inbox' only as a filename fragment
        "/home/u/channels_backup/clip.mp4",
    ],
)
def test_non_chat_paths_pass(path: str) -> None:
    assert analyse_video.is_chat_transport_path(path) is False


def test_inbox_unset_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    # No hardcoded fallback: an unset inbox reports as unset rather than
    # resolving to some guessed local directory.
    monkeypatch.delenv("COACH_VIDEO_INBOX", raising=False)
    assert analyse_video.video_inbox() is None


def test_inbox_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COACH_VIDEO_INBOX", "/data/form-videos")
    assert analyse_video.video_inbox() == Path("/data/form-videos")


def test_inbox_expands_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COACH_VIDEO_INBOX", "~/form-videos")
    inbox = analyse_video.video_inbox()
    assert inbox is not None and "~" not in str(inbox)
