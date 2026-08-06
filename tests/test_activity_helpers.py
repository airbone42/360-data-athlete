"""Tests for the shared date-extraction helper (`app.utils.activity_helpers`)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.activity_helpers import activity_date


def test_prefers_start_date_local() -> None:
    a = {"start_date_local": "2026-08-06T07:00:00", "start_date": "2026-08-05T07:00:00"}
    assert activity_date(a) == "2026-08-06"


def test_falls_back_to_start_date() -> None:
    a = {"start_date": "2026-08-05T07:00:00"}
    assert activity_date(a) == "2026-08-05"


def test_falls_back_to_start_date_when_start_date_local_is_none() -> None:
    a = {"start_date_local": None, "start_date": "2026-08-05T07:00:00"}
    assert activity_date(a) == "2026-08-05"


def test_falls_back_to_start_date_when_start_date_local_is_empty() -> None:
    a = {"start_date_local": "", "start_date": "2026-08-05T07:00:00"}
    assert activity_date(a) == "2026-08-05"


def test_returns_empty_string_when_neither_field_present() -> None:
    assert activity_date({}) == ""


def test_returns_empty_string_when_both_fields_none() -> None:
    a = {"start_date_local": None, "start_date": None}
    assert activity_date(a) == ""


def test_truncates_to_iso_date_only() -> None:
    a = {"start_date_local": "2026-08-06T21:45:12Z"}
    assert activity_date(a) == "2026-08-06"
