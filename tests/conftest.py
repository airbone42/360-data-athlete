"""Shared fixtures for coach test suite."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_cache(tmp_path: Path) -> Path:
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache


@pytest.fixture()
def tmp_config(tmp_path: Path) -> Path:
    """Copy real config dir into tmp so tests can mutate it.

    Prefers CONFIG_DIR (athlete-specific) when present, else falls back to
    CONFIG_FALLBACK (framework defaults under config.example/).
    """
    from app.utils.paths import CONFIG_DIR, CONFIG_FALLBACK
    src = CONFIG_DIR if CONFIG_DIR.exists() else CONFIG_FALLBACK
    dst = tmp_path / "config"
    shutil.copytree(src, dst)
    return dst


@pytest.fixture()
def sample_activity() -> dict:
    return {
        "id": "i123456",
        "name": "Test Run",
        "type": "Run",
        "start_date_local": "2025-04-19T08:00:00",
        "moving_time": 3600,
        "workout_type": "EASY",
        "tags": ["run"],
        "icu_training_load": 42.0,
        "icu_hr_zone_times": [600, 1800, 600, 300, 100],
        "gear_id": "g1",
    }


@pytest.fixture()
def sample_wellness() -> dict:
    return {
        "id": "2025-04-19",
        "hrv": 72.0,
        "restingHR": 48,
        "sleepScore": 80,
        "sleepSecs": 27000,
        "ctl": 55.0,
        "atl": 48.0,
    }
