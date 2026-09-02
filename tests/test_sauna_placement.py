"""R025 — sauna placement against its three documented buffers.

Anchor: `research/sauna-dosis-und-platzierung-endurance.md`. The rule exists
because a sauna reads as free — it is not a training stimulus, so nothing in
the plan pushes back on it — while its fluid and cardiovascular cost lands on
whatever comes next.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "validate_plan", ROOT / "scripts" / "validate_plan.py"
)
vp = importlib.util.module_from_spec(_spec)
sys.modules["validate_plan"] = vp
_spec.loader.exec_module(vp)


def _ctx(race_days_ahead=None):
    return vp.Context(target_date="2026-09-03", race_days_ahead=race_days_ahead)


SAUNA = {"type": "Workout", "name": "Sauna — Post-Session", "tags": ["sauna"]}
EASY_RUN = {"type": "Run", "name": "Easy Z2", "workout_type": "ENDURANCE", "tags": ["run"]}
THRESHOLD = {"type": "Run", "name": "Threshold 3x10", "workout_type": "THRESHOLD", "tags": ["run", "intervals"]}
STRENGTH = {"type": "WeightTraining", "name": "Schicht D", "tags": ["core"]}


def _ids(findings):
    return sorted({f.severity for f in findings})


def test_no_sauna_no_findings():
    assert vp.check_sauna_placement([EASY_RUN, THRESHOLD], _ctx()) == []


def test_post_session_after_easy_run_is_clean():
    """The prescribed use: endurance session, sauna straight after."""
    assert vp.check_sauna_placement([EASY_RUN, SAUNA], _ctx()) == []


def test_same_day_as_quality_warns():
    f = vp.check_sauna_placement([THRESHOLD, SAUNA], _ctx())
    assert len(f) == 1
    assert f[0].severity == vp.SEVERITY_WARNING
    assert "12 h" in f[0].message


def test_long_run_counts_as_quality():
    long_run = {"type": "Run", "name": "Long Run 110 min", "workout_type": "LONG", "tags": ["run"]}
    f = vp.check_sauna_placement([long_run, SAUNA], _ctx())
    assert any(x.severity == vp.SEVERITY_WARNING for x in f)


def test_standalone_sauna_is_info_not_warning():
    """Legitimate use — but it must not be booked as heat acclimation."""
    f = vp.check_sauna_placement([STRENGTH, SAUNA], _ctx())
    assert len(f) == 1
    assert f[0].severity == vp.SEVERITY_INFO
    assert "standalone" in f[0].message


def test_race_lockout_fires_inside_48h():
    f = vp.check_sauna_placement([EASY_RUN, SAUNA], _ctx(race_days_ahead=1))
    assert any("race" in x.message and x.severity == vp.SEVERITY_WARNING for x in f)


def test_race_lockout_silent_outside_48h():
    f = vp.check_sauna_placement([EASY_RUN, SAUNA], _ctx(race_days_ahead=3))
    assert f == []


def test_missing_race_data_does_not_fire():
    """Fail-soft: no calendar data must not invent a lockout."""
    f = vp.check_sauna_placement([EASY_RUN, SAUNA], _ctx(race_days_ahead=None))
    assert f == []


def test_sauna_itself_is_never_read_as_quality():
    """'Heat acclimation' in the name must not make the sauna its own trigger."""
    heat = {"type": "Workout", "name": "Heat acclimation block", "tags": ["sauna"]}
    f = vp.check_sauna_placement([EASY_RUN, heat], _ctx())
    assert f == []
