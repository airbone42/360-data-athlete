"""Tests for the structure pass, its gate, and the persistence lock.

Motivating case: a form check reported the athlete supported on an *extended
arm* when the footage showed a *forearm* support. That is a static structural
claim — a contact point — and it is the same class as every other wrong finding
this pipeline has produced: a misread contact point, a swapped anatomical side,
a detail present in no frame, a misread camera angle. None of them was temporal,
and two of them survived the two-pass context isolation that was built to stop
exactly this.

Two properties of the video path explain the class. A video frame is billed at
70 tokens on every media-resolution tier the transport can request, against 1120
for a still image, so a small region of a full-body frame is not represented at
all. And free prose under a known exercise name reproduces the textbook picture
of that exercise rather than the pixels.

The defenses tested here:

1. ``structure_gate`` blocks on anything that is not explicitly ``sicher``,
   including a missing field and a claim whose cited frame does not exist —
   silence is not a confirmation.
2. ``_update_exercise_log`` refuses to write while the unverified banner stands.
   This is the link in the damage path that turned a wrong reading into a
   training decision: the specialists read that file.
3. Neither the structure pass nor the movement pass is told the exercise name or
   the expected camera angle.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.analyse_video import (  # type: ignore  # noqa: E402
    STRUCTURE_UNVERIFIED_MARKER,
    FrameExtractionError,
    _build_perception_prompt,
    _build_structure_prompt,
    _parse_structure_json,
    _warn_on_seeded_context,
    extract_structure_frames,
    get_angle_focus,
    get_angle_geometry,
    get_angle_tip,
    structure_frames_dir,
    structure_gate,
)

FRAMES = ("frame_01_t00m03s.jpg", "frame_02_t00m11s.jpg")


def _record(**overrides) -> dict:
    """A structure record that passes the gate, before overrides are applied."""
    rec = {
        "aufnahme": {
            "kamera_winkel": "seitlich",
            "bildausschnitt": "ganzer_koerper",
            "belegframe": FRAMES[0],
            "sicherheit": "sicher",
        },
        "koerperposition": {
            "grundposition": "liegend_seitlich",
            "belegframe": FRAMES[0],
            "sicherheit": "sicher",
        },
        "bodenkontakte": [
            {
                "koerperteil": "Arm",
                "kontakt": "Unterarm_Ellbogen",
                "anatomische_seite": "rechts",
                "bildseite": "links",
                "seite_begruendung": "Bauchseite zur Kamera, Daumen zeigt nach oben",
                "belegframe": FRAMES[1],
                "sicherheit": "sicher",
            }
        ],
        "geraet": {"vorhanden": "nein", "belegframe": FRAMES[0], "sicherheit": "sicher"},
    }
    rec.update(overrides)
    return rec


# ── The gate ────────────────────────────────────────────────────────────────

def test_clean_record_passes() -> None:
    passed, reasons = structure_gate(_record(), FRAMES)
    assert passed, reasons


@pytest.mark.parametrize("level", ["unsicher", "nicht_erkennbar", "", None])
def test_uncertain_contact_blocks(level) -> None:
    rec = _record()
    rec["bodenkontakte"][0]["sicherheit"] = level
    passed, reasons = structure_gate(rec, FRAMES)
    assert not passed
    assert any("bodenkontakte" in r for r in reasons)


def test_undeterminable_contact_point_blocks_even_when_marked_certain() -> None:
    # The failure mode this whole stage exists for: a confident answer to a
    # question the frames cannot settle.
    rec = _record()
    rec["bodenkontakte"][0]["kontakt"] = "nicht_erkennbar"
    passed, reasons = structure_gate(rec, FRAMES)
    assert not passed
    assert any("Auflagepunkt nicht erkennbar" in r for r in reasons)


def test_undeterminable_laterality_blocks() -> None:
    rec = _record()
    rec["bodenkontakte"][0]["anatomische_seite"] = "nicht_erkennbar"
    passed, reasons = structure_gate(rec, FRAMES)
    assert not passed
    assert any("anatomische Seite" in r for r in reasons)


@pytest.mark.parametrize("field", ["aufnahme", "koerperposition", "bodenkontakte", "geraet"])
def test_missing_load_bearing_field_blocks(field) -> None:
    rec = _record()
    del rec[field]
    passed, reasons = structure_gate(rec, FRAMES)
    assert not passed
    assert any(field in r for r in reasons)


def test_empty_contact_list_blocks() -> None:
    passed, reasons = structure_gate(_record(bodenkontakte=[]), FRAMES)
    assert not passed


def test_certain_claim_citing_an_unknown_frame_blocks() -> None:
    # A claim whose evidence cannot be opened cannot be verified, so it is not
    # allowed to count as certain.
    rec = _record()
    rec["bodenkontakte"][0]["belegframe"] = "frame_99_t09m99s.jpg"
    passed, reasons = structure_gate(rec, FRAMES)
    assert not passed
    assert any("Belegframe" in r for r in reasons)


def test_gate_without_known_frames_does_not_check_evidence() -> None:
    # Called with no frame list (e.g. from a test or a replay), the evidence
    # check is skipped rather than failing every claim.
    passed, _ = structure_gate(_record(), ())
    assert passed


# ── Prompt isolation ────────────────────────────────────────────────────────

# Words that carry the identity of the movement. The run/strength split is a
# structural branch of the pipeline — the two modes ask different questions — so
# a prompt may reveal *that* someone is running. What it must not reveal is
# *which* exercise, because that is what summons the textbook picture.
DISTINCTIVE = {
    "Side Plank mit Hüft-Abduktion": ("side", "plank", "abduktion", "hüft"),
    "Bulgarian Split Squat": ("bulgarian", "split", "squat"),
    "Laufen Sagittal": ("sagittal",),
}


@pytest.mark.parametrize("exercise", sorted(DISTINCTIVE))
def test_movement_prompt_names_neither_exercise_nor_angle(exercise) -> None:
    prompt = _build_perception_prompt(exercise, "", run_mode="Laufen" in exercise).lower()
    assert exercise.lower() not in prompt
    for token in DISTINCTIVE[exercise]:
        assert token not in prompt, token
    assert get_angle_tip(exercise).lower() not in prompt


@pytest.mark.parametrize("exercise", sorted(DISTINCTIVE))
def test_structure_prompt_names_neither_exercise_nor_expected_angle(exercise) -> None:
    prompt = _build_structure_prompt(list(FRAMES), run_mode="Laufen" in exercise).lower()
    assert exercise.lower() not in prompt
    for token in DISTINCTIVE[exercise]:
        assert token not in prompt, token
    # The camera angle is asked, never asserted: the guide's tip must not appear,
    # and the old "laut Aufnahme-Vorgabe" phrasing that stated an expectation is
    # gone. Enum members naming possible angles are fine — they are the answer
    # options, and offering all of them is what keeps the question neutral.
    assert get_angle_tip(exercise).lower() not in prompt
    assert "vorgabe" not in prompt
    for option in ("frontal", "seitlich", "dorsal", "nicht_erkennbar"):
        assert option in prompt, option


def test_structure_prompt_offers_both_arm_support_options_and_abstention() -> None:
    # The incident in one assertion: forearm and extended arm must be two named
    # choices, and abstaining must be a third.
    prompt = _build_structure_prompt(list(FRAMES), run_mode=False)
    assert "Unterarm_Ellbogen" in prompt
    assert "Hand_gestreckter_Arm" in prompt
    assert "nicht_erkennbar" in prompt


def test_structure_prompt_lists_the_actual_frame_names() -> None:
    prompt = _build_structure_prompt(list(FRAMES), run_mode=False)
    for name in FRAMES:
        assert name in prompt


# ── Angle split ─────────────────────────────────────────────────────────────

def test_angle_geometry_drops_the_evaluation_focus() -> None:
    geometry = get_angle_geometry("TRX Row")
    assert "seitlich" in geometry
    assert "Ellbogen" not in geometry
    assert "—" not in geometry
    assert "Ellbogen-Führung" in get_angle_focus("TRX Row")


def test_longest_pattern_wins_so_plank_does_not_borrow_side_plank() -> None:
    assert "Stützarm" in get_angle_tip("Side Plank mit Hüft-Abduktion")
    assert "Stützarm" not in get_angle_tip("Plank")


# ── JSON parsing ────────────────────────────────────────────────────────────

def test_parse_strips_code_fences() -> None:
    assert _parse_structure_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _parse_structure_json('{"a": 1}') == {"a": 1}


def test_parse_rejects_prose() -> None:
    with pytest.raises(ValueError):
        _parse_structure_json("Das Video zeigt einen Seitstütz.")


# ── Seeding guard extension ─────────────────────────────────────────────────

def test_seeding_guard_flags_a_contact_point_correction() -> None:
    # The reflex after a wrong structural finding is to re-run with the
    # correction in --context. That yields a confirmation, not an observation.
    assert _warn_on_seeded_context("Athlet stützt auf dem Unterarm, nicht gestreckter Arm")
    assert _warn_on_seeded_context("Füße gestaffelt, nicht gestapelt")


def test_seeding_guard_still_allows_injury_context() -> None:
    assert _warn_on_seeded_context("Schulter rechts in Reha, LWS gereizt") == []


# ── Persistence lock ────────────────────────────────────────────────────────

def test_unverified_finding_is_not_persisted(tmp_path, monkeypatch) -> None:
    import scripts.analyse_video as av  # type: ignore

    log = tmp_path / "exercise_log.md"
    log.write_text("# Log\n", encoding="utf-8")
    monkeypatch.setattr(av, "_EXERCISE_LOG", log)

    av._update_exercise_log(
        "Side Plank", "clip.mp4",
        f"{STRUCTURE_UNVERIFIED_MARKER} — Befund: Stütz auf dem gestreckten Arm.",
        "2026-09-07",
    )
    assert log.read_text(encoding="utf-8") == "# Log\n"


def test_blocked_finding_is_not_persisted(tmp_path, monkeypatch) -> None:
    import scripts.analyse_video as av  # type: ignore

    log = tmp_path / "exercise_log.md"
    log.write_text("# Log\n", encoding="utf-8")
    monkeypatch.setattr(av, "_EXERCISE_LOG", log)

    av._update_exercise_log(
        "Side Plank", "clip.mp4", "❌ Formcheck blockiert: Struktur nicht belastbar erhoben.",
        "2026-09-07",
    )
    assert log.read_text(encoding="utf-8") == "# Log\n"


def test_verified_finding_is_persisted(tmp_path, monkeypatch) -> None:
    import scripts.analyse_video as av  # type: ignore

    log = tmp_path / "exercise_log.md"
    log.write_text("# Log\n", encoding="utf-8")
    monkeypatch.setattr(av, "_EXERCISE_LOG", log)

    av._update_exercise_log(
        "Side Plank", "clip.mp4",
        "Struktur-Verifikation: BESTÄTIGT 4. Unterarm-Stütz, Hüfte stabil.",
        "2026-09-07",
    )
    written = log.read_text(encoding="utf-8")
    assert "Side Plank" in written
    assert "Unterarm-Stütz" in written


# ── Frame extraction ────────────────────────────────────────────────────────

def test_missing_ffmpeg_raises_instead_of_degrading(tmp_path, monkeypatch) -> None:
    # The dangerous failure mode is a silent one: with no frames the check would
    # fall back to the video path, which is exactly the failure class this stage
    # exists to prevent — and nothing in the output would say so.
    import scripts.analyse_video as av  # type: ignore

    monkeypatch.setattr(av, "_ffmpeg_exe", lambda: None)
    with pytest.raises(FrameExtractionError):
        extract_structure_frames("whatever.mp4", tmp_path, count=3)


def test_frames_default_into_the_video_inbox(monkeypatch) -> None:
    # These are stills of the athlete. The inbox is gitignored; a default that
    # landed anywhere else could be committed and pushed.
    monkeypatch.setenv("COACH_VIDEO_INBOX", str(Path("/data/video_inbox")))
    target = structure_frames_dir("/clips/VID_123.mp4")
    assert target.parts[-2:] == ("frames", "VID_123")
    assert "video_inbox" in str(target)


def test_frames_fall_back_outside_the_repo_when_no_inbox(monkeypatch) -> None:
    monkeypatch.delenv("COACH_VIDEO_INBOX", raising=False)
    target = structure_frames_dir("/clips/VID_123.mp4")
    assert target.is_absolute()
    assert Path.cwd() not in target.parents


def test_explicit_frames_dir_wins() -> None:
    assert structure_frames_dir("/clips/VID_123.mp4", "/tmp/custom") == Path("/tmp/custom")


# ── "sicher" about not being able to tell is still not a confirmation ────────
#
# Observed on a real clip: the stills went into the pass rotated 90°, and the
# model answered `grundposition: "nicht_erkennbar"` with `sicherheit: "sicher"`
# — an honest abstention, correctly labelled. The gate read only `sicherheit`
# for these three records and let it through, so the run went on to produce an
# assessment on a body position nobody could name. The abstention lives in the
# value field; `sicherheit` describes confidence in the answer, including
# confidence that there is none.

def test_unreadable_body_position_blocks_even_when_certain() -> None:
    rec = _record(koerperposition={
        "grundposition": "nicht_erkennbar",
        "belegframe": FRAMES[0],
        "sicherheit": "sicher",
    })
    passed, reasons = structure_gate(rec, FRAMES)
    assert not passed
    assert any("koerperposition.grundposition" in r for r in reasons)


def test_unreadable_camera_angle_blocks_even_when_certain() -> None:
    rec = _record(aufnahme={
        "kamera_winkel": "nicht_erkennbar",
        "bildausschnitt": "ganzer_koerper",
        "belegframe": FRAMES[0],
        "sicherheit": "sicher",
    })
    passed, reasons = structure_gate(rec, FRAMES)
    assert not passed
    assert any("aufnahme.kamera_winkel" in r for r in reasons)


def test_unreadable_implement_presence_blocks() -> None:
    rec = _record(geraet={
        "vorhanden": "nicht_erkennbar",
        "belegframe": FRAMES[0],
        "sicherheit": "sicher",
    })
    passed, reasons = structure_gate(rec, FRAMES)
    assert not passed
    assert any("geraet.vorhanden" in r for r in reasons)


def test_implement_present_but_hand_unreadable_blocks() -> None:
    """Which hand carries the load is the laterality question that fails most."""
    rec = _record(geraet={
        "vorhanden": "ja",
        "was": "Kurzhantel",
        "anatomische_hand": "nicht_erkennbar",
        "belegframe": FRAMES[0],
        "sicherheit": "sicher",
    })
    passed, reasons = structure_gate(rec, FRAMES)
    assert not passed
    assert any("geraet.anatomische_hand" in r for r in reasons)


def test_no_implement_needs_no_hand() -> None:
    """`vorhanden: nein` carries no hand to name — that must not block."""
    passed, _ = structure_gate(_record(), FRAMES)
    assert passed
