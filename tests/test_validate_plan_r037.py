"""Tests for validate_plan.py R037 — description reading budget."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.validate_plan import Context, check_description_budget  # type: ignore  # noqa: E402

SHORT = "MAIN\n\nPull-up: 3×5 @ BW | RPE 7 | stop at form loss"
LONG_LINE = "Row: 3×8 @ 20 kg | RPE 7 | " + "why this load and not another " * 10


def _ctx(status: str = "") -> Context:
    return Context(target_date="2026-11-10", athlete_status=status)


def _w(desc: str, typ: str = "WeightTraining") -> dict:
    return {"type": typ, "name": "Kraft", "tags": ["upperbody"], "description": desc}


def test_short_description_passes():
    assert check_description_budget([_w(SHORT)], _ctx()) == []


def test_over_default_budget_warns():
    desc = "\n".join(["Exercise: 3×10 @ 10 kg | RPE 7 | one cue only here"] * 30)
    f = check_description_budget([_w(desc)], _ctx())
    assert [x.rule_id for x in f] == ["R037"]
    assert f[0].severity == "WARNING"
    assert "budget 1200" in f[0].message


def test_long_single_line_warns_under_budget():
    f = check_description_budget([_w(LONG_LINE)], _ctx())
    assert len(f) == 1 and "line(s) over" in f[0].message


def test_configured_budget_and_off_switch():
    desc = "x" * 900
    assert check_description_budget([_w(desc)], _ctx("description_max_chars: 800\n"))
    assert check_description_budget([_w("y" * 5000)], _ctx("description_max_chars: 0\n")) == []


def test_endurance_sessions_skipped():
    assert check_description_budget([_w("z" * 5000, typ="Run")], _ctx()) == []
