"""Smoke tests for workout_parser.parse_workouts()."""
from __future__ import annotations

import pytest

from app.graphs.main_daily_planner.workout_parser import (
    REQUIRED_FIELDS,
    VALID_TAGS,
    VALID_TYPES,
    parse_workouts,
)

_MINIMAL = {
    "type": "Run",
    "name": "Testlauf",
    "duration_min": 45,
    "workout_type": "EASY",
}


def _full(**overrides: object) -> dict:
    return {**_MINIMAL, **overrides}


# ---------------------------------------------------------------------------
# Valid inputs
# ---------------------------------------------------------------------------


def test_dict_with_workouts_key() -> None:
    notes, ws = parse_workouts({"coaching_notes": "gut", "workouts": [_full()]})
    assert notes == "gut"
    assert len(ws) == 1
    assert ws[0]["type"] == "Run"


def test_bare_list() -> None:
    notes, ws = parse_workouts([_full(), _full(type="Ride", name="Rad")])
    assert notes == ""
    assert len(ws) == 2


def test_empty_list_returns_rest_day() -> None:
    _, ws = parse_workouts([])
    assert len(ws) == 1
    assert ws[0]["workout_type"] == "RECOVERY"


def test_all_valid_types() -> None:
    for t in VALID_TYPES:
        _, ws = parse_workouts([_full(type=t)])
        assert ws[0]["type"] == t


# ---------------------------------------------------------------------------
# Tag filtering
# ---------------------------------------------------------------------------


def test_valid_tags_kept() -> None:
    _, ws = parse_workouts([_full(tags=["core", "plyo"])])
    assert set(ws[0]["tags"]) == {"core", "plyo"}


def test_legs_and_beine_both_accepted() -> None:
    """Bilingual compat during the beine → legs migration: both forms parse."""
    _, ws_legs = parse_workouts([_full(tags=["legs"])])
    assert "legs" in ws_legs[0]["tags"]
    _, ws_beine = parse_workouts([_full(tags=["beine"])])
    assert "beine" in ws_beine[0]["tags"]


def test_invalid_tags_dropped(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    with caplog.at_level(logging.WARNING):
        _, ws = parse_workouts([_full(tags=["core", "bogustag"])])
    assert "bogustag" not in ws[0]["tags"]
    assert "bogustag" in caplog.text


def test_valid_tags_constant_complete() -> None:
    expected = {"run", "ride", "core", "legs", "beine", "plyo", "balance",
                "mobility", "intervals", "ninja", "grip", "upperbody"}
    assert VALID_TAGS == expected


# ---------------------------------------------------------------------------
# Missing REQUIRED_FIELDS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
def test_missing_required_field_raises(missing_field: str) -> None:
    bad = {k: v for k, v in _MINIMAL.items() if k != missing_field}
    with pytest.raises(ValueError, match=missing_field):
        parse_workouts([bad])


# ---------------------------------------------------------------------------
# Invalid type
# ---------------------------------------------------------------------------


def test_invalid_type_raises() -> None:
    with pytest.raises(ValueError, match="invalid type"):
        parse_workouts([_full(type="Swim")])
