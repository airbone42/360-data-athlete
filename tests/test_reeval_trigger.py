"""Tests for the exercise re-evaluation trigger in context_builder.

The trigger emits a cheap advisory flag at natural boundaries (recovery
week / periodization phase change / staleness) so the /training flow can
run the exercise-reviewer agent instead of blindly carrying exercises
forward. It never blocks and does nothing on a normal day.

All fixture dates are synthetic 2025 dates (Lehre 7 — no real athlete
training-diary dates in the public test suite).
"""
from __future__ import annotations

from datetime import date

from app.graphs.sub_athlete_context import context_builder as cb

# ── _parse_reeval_config ─────────────────────────────────────────────


def test_parse_reeval_config_defaults_when_block_missing() -> None:
    cfg = cb._parse_reeval_config("# Status\n\nNo re-eval block here.\n")
    assert cfg["staleness_weeks"] == cb._REEVAL_STALENESS_WEEKS_DEFAULT
    assert cfg["last_reeval_phase"] is None
    assert cfg["phases"] == []


def test_parse_reeval_config_none_content() -> None:
    cfg = cb._parse_reeval_config(None)
    assert cfg["staleness_weeks"] == cb._REEVAL_STALENESS_WEEKS_DEFAULT
    assert cfg["phases"] == []


def test_parse_reeval_config_parses_all_fields() -> None:
    content = (
        "## Re-Eval\n"
        "- **staleness_weeks:** 4\n"
        "- **last_reeval_phase:** Build I\n"
        "\n"
        "Build I | 2025-04-01 | 2025-05-31\n"
        "Build II | 2025-06-01 | 2025-06-30\n"
    )
    cfg = cb._parse_reeval_config(content)
    assert cfg["staleness_weeks"] == 4
    assert cfg["last_reeval_phase"] == "Build I"
    assert cfg["phases"] == [
        ("Build I", date(2025, 4, 1), date(2025, 5, 31)),
        ("Build II", date(2025, 6, 1), date(2025, 6, 30)),
    ]


def test_parse_reeval_config_placeholder_phase_is_none() -> None:
    cfg = cb._parse_reeval_config("- **last_reeval_phase:** —\n")
    assert cfg["last_reeval_phase"] is None


def test_parse_reeval_config_skips_inverted_phase_window() -> None:
    # end before start → dropped (parse mismatch guard)
    cfg = cb._parse_reeval_config("Bad | 2025-06-30 | 2025-06-01\n")
    assert cfg["phases"] == []


# ── _current_phase ───────────────────────────────────────────────────


def test_current_phase_inside_window() -> None:
    phases = [("Build II", date(2025, 6, 1), date(2025, 6, 30))]
    assert cb._current_phase(phases, date(2025, 6, 15)) == "Build II"


def test_current_phase_outside_window() -> None:
    phases = [("Build II", date(2025, 6, 1), date(2025, 6, 30))]
    assert cb._current_phase(phases, date(2025, 7, 1)) is None


# ── _parse_stale_exercises ───────────────────────────────────────────

_PROG = """## Grip

### Farmer's Hold
- **Aktueller Stand:** 3x35s
- **Re-Eval:** dient=Grip (Phase 2) | eingeführt=2025-01-01 | letzte-Re-Eval=2025-01-10 | Status=keep

### Wrist Curls
- **Re-Eval:** dient=Grip (Phase 2) | eingeführt=2025-05-01 | letzte-Re-Eval=2025-06-10 | Status=keep

### Old Move
- **Re-Eval:** dient=legacy | eingeführt=2025-01-01 | letzte-Re-Eval=2025-01-01 | Status=retire
"""


def test_parse_stale_exercises_flags_old_entry() -> None:
    # today far past Farmer's Hold last-reeval (2025-01-10), within Wrist Curls
    stale = cb._parse_stale_exercises(_PROG, date(2025, 6, 20), max_weeks=6)
    assert "Farmer's Hold" in stale
    assert "Wrist Curls" not in stale  # 10 days ago < 6 weeks


def test_parse_stale_exercises_skips_retired() -> None:
    stale = cb._parse_stale_exercises(_PROG, date(2025, 6, 20), max_weeks=6)
    assert "Old Move" not in stale


def test_parse_stale_exercises_respects_threshold() -> None:
    # With a 1-week threshold, Wrist Curls (10 days) also becomes stale
    stale = cb._parse_stale_exercises(_PROG, date(2025, 6, 20), max_weeks=1)
    assert "Wrist Curls" in stale


def test_parse_stale_exercises_none_content() -> None:
    assert cb._parse_stale_exercises(None, date(2025, 6, 20), max_weeks=6) == []


# ── _reeval_recovery_active ───────────────────────────────────────────


def test_recovery_active_true() -> None:
    state = {"aktiv": "ja", "ende_geplant": "2025-06-30"}
    assert cb._reeval_recovery_active(state, date(2025, 6, 20)) is True


def test_recovery_active_expired_end() -> None:
    state = {"aktiv": "ja", "ende_geplant": "2025-06-10"}
    assert cb._reeval_recovery_active(state, date(2025, 6, 20)) is False


def test_recovery_active_inactive() -> None:
    state = {"aktiv": "nein", "ende_geplant": "2025-06-30"}
    assert cb._reeval_recovery_active(state, date(2025, 6, 20)) is False


def test_recovery_active_none_state() -> None:
    assert cb._reeval_recovery_active(None, date(2025, 6, 20)) is False


# ── _compute_reeval_trigger (integration, configs monkeypatched) ──────


def _patch_configs(monkeypatch, *, status: str | None, prog: str | None) -> None:
    def fake_read(filename: str) -> str | None:
        if filename == "athlete_status.md":
            return status
        if filename == "exercise_progressions.md":
            return prog
        return None

    monkeypatch.setattr(cb, "_read_optional_config", fake_read)


def test_trigger_none_on_normal_day(monkeypatch) -> None:
    _patch_configs(monkeypatch, status="## Re-Eval\n- **staleness_weeks:** 6\n", prog=_PROG)
    # fresh date → Farmer's Hold not stale, no recovery, no phase config
    out = cb._compute_reeval_trigger(date(2025, 1, 12), deload_state={"aktiv": "nein"})
    assert out is None


def test_trigger_fires_on_recovery_week(monkeypatch) -> None:
    _patch_configs(monkeypatch, status="", prog=None)
    out = cb._compute_reeval_trigger(
        date(2025, 6, 20), deload_state={"aktiv": "ja", "ende_geplant": "2025-06-30"}
    )
    assert out is not None
    assert "recovery week active" in out
    assert "🔄" in out


def test_trigger_fires_on_staleness(monkeypatch) -> None:
    _patch_configs(monkeypatch, status="- **staleness_weeks:** 6\n", prog=_PROG)
    out = cb._compute_reeval_trigger(date(2025, 6, 20), deload_state={"aktiv": "nein"})
    assert out is not None
    assert "stale" in out
    assert "Farmer's Hold" in out


def test_trigger_fires_on_phase_change(monkeypatch) -> None:
    status = (
        "- **last_reeval_phase:** Build I\n"
        "Build I | 2025-04-01 | 2025-05-31\n"
        "Build II | 2025-06-01 | 2025-06-30\n"
    )
    _patch_configs(monkeypatch, status=status, prog=None)
    out = cb._compute_reeval_trigger(date(2025, 6, 15), deload_state={"aktiv": "nein"})
    assert out is not None
    assert "phase change Build I → Build II" in out


def test_trigger_no_phase_change_when_anchor_matches(monkeypatch) -> None:
    status = (
        "- **last_reeval_phase:** Build II\n"
        "Build II | 2025-06-01 | 2025-06-30\n"
    )
    _patch_configs(monkeypatch, status=status, prog=None)
    out = cb._compute_reeval_trigger(date(2025, 6, 15), deload_state={"aktiv": "nein"})
    assert out is None
