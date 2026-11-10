"""Recovery spacing is a planning rule, not an injury (coach audit 2026-11-08).

The context used to print the tag rules as "⛔ Ninja upper body blocked after
Grip (forearm-flexor interference)". A model turned that into an injury the
athlete never had. These tests pin the wording, the grouping in
planningConstraints and the parity between the context and the pre-push
validator (both run through ``active_recovery_spacings``).
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml

from app.analytics.recovery import (
    MUSCLE_OVERLAP_RULES,
    RECOVERY_SPACING_HEADER,
    active_recovery_spacings,
)
from app.graphs.sub_athlete_context.context_builder import (
    _compute_planning_constraints,
    _compute_recovery_blocks,
)
from scripts.pre_push_validator import check_recovery_rules

TODAY = date(2026, 11, 10)
RULES = [
    (["plyo"], 3, "Plyo recovery"),
    (["legs"], 2, "Leg-strength recovery"),
    (["ninja", "grip"], 2, "Grip recovery"),
]

# Anatomy words that read like a finding when they sit next to a block.
_ANATOMY = re.compile(
    r"forearm|flexor|extensor|tendon|muscle|achilles|knee|shoulder|groin|cns",
    re.IGNORECASE,
)


def _act(day: str, tags: list[str]) -> dict:
    return {"start_date_local": f"{day}T08:00:00", "tags": tags, "type": "Workout"}


def test_spacing_runs_until_free_from() -> None:
    acts = [_act("2026-11-09", ["ninja", "grip", "upperbody"])]
    sp = active_recovery_spacings(acts, TODAY, RULES)
    assert [s["label"] for s in sp] == ["Grip recovery"]
    assert sp[0]["free_from"] == date(2026, 11, 11)
    assert sp[0]["days_ago"] == 1


def test_spacing_expired_rule_is_silent() -> None:
    acts = [_act("2026-11-07", ["plyo"])]  # 3 days ago, 3d rule -> free today
    assert active_recovery_spacings(acts, TODAY, RULES) == []


def test_spacing_uses_latest_activity_regardless_of_order() -> None:
    acts = [_act("2026-11-10", ["plyo"]), _act("2026-11-01", ["plyo"])]
    sp = active_recovery_spacings(acts, TODAY, RULES)
    assert sp[0]["days_ago"] == 0
    assert sp[0]["free_from"] == date(2026, 11, 13)


def test_spacing_matches_legacy_beine_tag() -> None:
    sp = active_recovery_spacings([_act("2026-11-09", ["beine"])], TODAY, RULES)
    assert [s["label"] for s in sp] == ["Leg-strength recovery"]


def test_spacing_reads_context_summary_dates() -> None:
    """pre_push_validator sees summarised activities ({"date": ...})."""
    sp = active_recovery_spacings([{"date": "2026-11-09", "tags": ["plyo"]}], TODAY, RULES)
    assert sp and sp[0]["label"] == "Plyo recovery"


def test_context_line_wording_has_no_lock_symbol() -> None:
    lines = _compute_recovery_blocks([_act("2026-11-10", ["ninja", "grip"])], TODAY)
    assert lines, "the shipped rules must include a grip rule"
    assert all("⛔" not in ln and "⏳" in ln for ln in lines)
    assert any("Grip recovery" in ln and "2026-11-12" in ln for ln in lines)


def test_planning_constraints_groups_spacing_under_own_header() -> None:
    acts = [_act("2026-11-10", ["ninja", "grip"])]
    lines = _compute_planning_constraints([], acts, TODAY).splitlines()
    assert RECOVERY_SPACING_HEADER in lines
    assert "not injuries" in RECOVERY_SPACING_HEADER
    head = lines.index(RECOVERY_SPACING_HEADER)
    assert lines[head + 1].startswith("  ⏳ ")
    assert not any(ln.startswith("⛔") and "recovery" in ln.lower() for ln in lines)


def test_no_header_without_running_spacing() -> None:
    text = _compute_planning_constraints([], [_act("2026-10-01", ["plyo"])], TODAY)
    assert RECOVERY_SPACING_HEADER not in text


def test_keyword_rules_join_the_same_group() -> None:
    acts = [{
        "start_date_local": "2026-11-10T08:00:00",
        "tags": ["core"],
        "description": "HAUPTTEIL\nFarmer Hold: 3x40s @ 24kg | RPE 7",
    }]
    lines = _compute_planning_constraints([], acts, TODAY).splitlines()
    head = lines.index(RECOVERY_SPACING_HEADER)
    assert any("Grip-hold spacing" in ln for ln in lines[head + 1:])


def test_shipped_labels_carry_no_anatomy() -> None:
    root = Path(__file__).resolve().parents[1]
    raw = yaml.safe_load((root / "config.example" / "recovery_rules.yaml").read_text())
    labels = [r["label"] for r in raw["rules"]] + [r["label"] for r in MUSCLE_OVERLAP_RULES]
    offenders = [lbl for lbl in labels if _ANATOMY.search(lbl) or "blocked" in lbl.lower()]
    assert offenders == []


def test_pre_push_validator_uses_same_rules_and_wording() -> None:
    recent = [{"date": "2026-11-09", "tags": ["beine"]}]
    planned = [{"name": "Kraft Beine", "type": "WeightTraining", "tags": ["legs"]}]
    out = check_recovery_rules(planned, recent, TODAY)
    assert len(out) == 1
    assert "planning rule, not an injury" in out[0]
    assert "free from 2026-11-11" in out[0]


def test_pre_push_validator_allows_after_spacing() -> None:
    recent = [{"date": "2026-11-08", "tags": ["legs"]}]
    planned = [{"name": "Kraft Beine", "type": "WeightTraining", "tags": ["legs"]}]
    assert check_recovery_rules(planned, recent, TODAY) == []
