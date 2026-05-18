"""Minimal stub for filtering module required by gcexport.py."""
from __future__ import annotations
from pathlib import Path


def read_exclude(exclude_file: str | None) -> set:
    """Return set of activity IDs to exclude. Empty if no file given."""
    if not exclude_file:
        return set()
    p = Path(exclude_file)
    if not p.exists():
        return set()
    return {line.strip() for line in p.read_text().splitlines() if line.strip()}


def update_download_stats(activity_id: str, directory: str) -> None:
    """No-op stats tracking."""
    pass
