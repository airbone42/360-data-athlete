"""Smoke tests for config_loader and shoe_advisor.load_shoe_profiles."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.utils.config_loader import load_all_configs, reload_configs


# ---------------------------------------------------------------------------
# config_loader
# ---------------------------------------------------------------------------


def test_load_all_configs_returns_non_empty_dict() -> None:
    configs = load_all_configs()
    assert isinstance(configs, dict)
    assert len(configs) > 0


def test_load_all_configs_includes_key_files() -> None:
    configs = load_all_configs()
    for expected_key in ("athlete_static", "athlete_preferences", "training_paradigms"):
        assert expected_key in configs, f"Expected '{expected_key}' in configs"


def test_load_all_configs_values_are_nonempty_strings() -> None:
    configs = load_all_configs()
    for key, val in configs.items():
        assert isinstance(val, str), f"Config '{key}' is not a string"
        assert val.strip(), f"Config '{key}' is empty"


def test_load_all_configs_excludes_readme() -> None:
    """`README.md` in config dirs is documentation, not config — must not leak
    into the merged dict where it could accidentally become a prompt
    placeholder ({README}) and mask a real missing key."""
    configs = load_all_configs()
    assert "README" not in configs, (
        "README.md was loaded as a config key; load_all_configs() should "
        "skip non-config markdown files via _NON_CONFIG_STEMS."
    )
    assert "readme" not in configs


def test_reload_configs_clears_cache() -> None:
    # Just verify it doesn't raise
    reload_configs()
    configs = load_all_configs()
    assert len(configs) > 0


# ---------------------------------------------------------------------------
# shoe_advisor.load_shoe_profiles
# ---------------------------------------------------------------------------


def test_load_shoe_profiles_returns_list() -> None:
    from app.graphs.shoe_advisor import load_shoe_profiles
    profiles = load_shoe_profiles()
    assert isinstance(profiles, list)


def test_load_shoe_profiles_nonempty() -> None:
    from app.graphs.shoe_advisor import load_shoe_profiles
    profiles = load_shoe_profiles()
    assert len(profiles) > 0, "No shoe profiles found in equipment.md"


def test_load_shoe_profiles_have_required_keys() -> None:
    from app.graphs.shoe_advisor import load_shoe_profiles
    for profile in load_shoe_profiles():
        assert "name" in profile or "model" in profile, f"Profile missing name/model: {profile}"
