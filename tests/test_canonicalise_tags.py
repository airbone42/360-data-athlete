"""Unit tests for the bilingual leg-tag synonym helper.

`canonicalise_tags()` is the migration layer between the legacy German tag
"beine" and the new canonical English tag "legs". Both forms must be
treated as synonyms throughout the framework so historical activity data
keeps matching the rules while new plans emit the English form.
"""
from __future__ import annotations

from app.analytics.recovery import canonicalise_tags


def test_none_returns_empty_list() -> None:
    assert canonicalise_tags(None) == []


def test_empty_list_returns_empty() -> None:
    assert canonicalise_tags([]) == []


def test_lowercase_normalisation() -> None:
    # Without leg-synonym expansion the helper preserves input order.
    assert canonicalise_tags(["RUN", "Plyo"]) == ["run", "plyo"]


def test_beine_only_expands_to_include_legs() -> None:
    result = canonicalise_tags(["beine", "intervals"])
    assert "beine" in result
    assert "legs" in result
    assert "intervals" in result


def test_legs_only_expands_to_include_beine() -> None:
    result = canonicalise_tags(["legs", "intervals"])
    assert "beine" in result
    assert "legs" in result
    assert "intervals" in result


def test_both_present_passes_through() -> None:
    result = canonicalise_tags(["legs", "beine", "core"])
    assert set(result) == {"beine", "legs", "core"}


def test_unrelated_tags_unchanged() -> None:
    result = canonicalise_tags(["run", "intervals"])
    assert "beine" not in result
    assert "legs" not in result
    assert set(result) == {"run", "intervals"}
