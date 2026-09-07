#!/usr/bin/env python3
"""Video-Formcheck via Gemini (OpenRouter) — Kraft/Core/Balance/Ninja/Laufen.

Drei Stufen, getrennt nach Art der Aussage:

A. **Struktur** — Auflagepunkte, Seitigkeit, Gerät, Kamerawinkel, erhoben an
   wenigen Standbildern in Originalauflösung. Geschlossener Fragebogen mit
   erzwungener `nicht_erkennbar`-Option, ohne Übungsname. Ein nicht sicher
   erhobener Struktur-Claim blockt den Befund (Exit 4).
B. **Bewegung** — Wiederholungen, Tempo, früh-vs-spät, am nativen Video.
   Ebenfalls ohne Übungsname und ohne Athleten-Kontext.
C. **Bewertung** — nur Text aus A und B, nie Video, nie Frames; hier kommt der
   Athleten-Kontext dazu.

Warum der Split: Für Video deckelt Gemini einen Frame auf 70 Tokens (nur
`media_resolution=high` gäbe 280, und OpenRouter kann das nicht anfordern) —
ein Standbild bekommt 1120. Sämtliche real aufgetretenen Fehlbefunde waren
statisch-strukturell, keiner temporal. Details und Quellen:
framework/research/video-form-check-model-selection.md

Usage:
    python3 scripts/analyse_video.py --video /tmp/video.mp4 --exercise "Goblet Squat"
    python3 scripts/analyse_video.py --video /tmp/video.mp4 --exercise "Laufen Sagittal" --angle "seitlich"
    python3 scripts/analyse_video.py --video /tmp/video.mp4 --exercise "Laufen Posterior" --start 10 --end 30
    python3 scripts/analyse_video.py --video /tmp/video.mp4 --exercise "Tempo Run Sagittal" --slowmo
    python3 scripts/analyse_video.py --video /tmp/video.mp4 --exercise "Box Jump" --model pro
    python3 scripts/analyse_video.py --exercise "Hollow Rock" --angle-only
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.config import settings  # noqa: E402
from app.utils.tracing import (  # noqa: E402
    configure_tracing,
    get_tracer,
    script_span,
    set_span_io,
    set_span_metadata,
)

configure_tracing()

RUN_KEYWORDS = {"laufen", "run", "jogging", "tempo run", "easy run", "trail run",
                "bergauf", "bergab", "stride", "lauf sagittal", "lauf posterior",
                "run sagittal", "run posterior"}

# Modelle
#
# Slugs are pinned deliberately. OpenRouter's `~`-prefixed aliases
# (e.g. ~google/gemini-pro-latest) re-point without notice and offer no
# rollback, which would silently change grading behaviour on a check that
# gates progression decisions.
#
# Selection is backed by MotionBench (fine-grained motion perception) and
# Video-MME-v2 (temporal ordering / cross-segment inference), plus a local
# smoke test on a real form-check clip with known ground truth:
#   - gemini-2.5-pro (previous default) scored lowest of the modern field on
#     MotionBench (66.3) and, in the local test, confabulated on structures
#     that were not in frame at all.
#   - gemini-3.1-pro-preview correctly answered "not assessable" for the
#     lumbar contour (occluded by clothing/angle) and for a scapula outside
#     the frame, where the older model produced confident findings.
#   - bytedance-seed/seed-2.0-lite leads MotionBench on paper (72.4, vendor
#     self-reported) but failed the same local test: wrong stance answer with
#     high stated confidence, plus an unsupported fatigue claim. Not adopted.
MODELS = {
    "flash": "google/gemini-3-flash-preview",
    "pro":   "google/gemini-3.1-pro-preview",
}
DEFAULT_MODEL = "pro"

# `max_tokens` is a cap on reasoning + answer, not on the answer alone, and the
# models above are thinking models: a structure questionnaire that emits ~900
# tokens of JSON burned 3839 reasoning tokens before writing a character. At a
# 4000 cap that truncates mid-object, and the caller sees a JSON parse error
# rather than a budget problem. The cap is only charged when it is used, so it
# is set well above the observed need rather than tuned to it.
MAX_TOKENS = {"flash": 8000, "pro": 16000}

# Known limitation — read before trusting a fine spatial detail:
# on a chat-compressed clip at default sampling (~1 fps), a binary stance
# question ("stacked vs. staggered feet") was answered inconsistently across
# repeated identical runs of the SAME model. The information is not reliably
# present in the sampled frames, so no model choice fixes it.
#
# The remedy originally recorded here — "full-resolution upload" — turned out to
# be insufficient, and it is worth being precise about why: the 70-token cap is
# applied per *frame* regardless of what the source file contains, so uploading
# a sharper video buys nothing on a question like this. What actually raises the
# budget is asking the question of a still image instead (1120 tokens), which is
# what the structure pass does. Uploading the original is still right — chat
# re-encoding destroys detail before Gemini ever sees it — it is just not
# sufficient on its own.

# --- Chat-transport guard -------------------------------------------------
#
# Chat channels (Telegram et al.) re-encode video on upload: resolution is
# reduced and compression artefacts are introduced. A form check reads joint
# angles, limb positions and left/right detail out of single frames, so that
# loss directly produces perception errors — stacked vs. staggered feet,
# scapular position, subtle spine curvature. The analysis then reads as
# confident and is wrong, which is worse than no analysis.
#
# Videos arriving through a chat attachment are therefore refused by default.
# The athlete uploads the original file to COACH_VIDEO_INBOX instead.
_CHAT_INBOX_MARKERS = (("channels", "inbox"),)

# Exit codes the caller distinguishes. 3 = chat transport refused (above);
# 4 = the structural claims did not hold up, so no finding was produced. A 4 is
# a correct outcome, not a crash: it means the pipeline declined to guess.
EXIT_STRUCTURE_GATE = 4


def is_chat_transport_path(path: str) -> bool:
    """True when the path looks like a chat-plugin attachment download."""
    parts = [p.lower() for p in Path(path).parts]
    return any(all(marker in parts for marker in markers) for markers in _CHAT_INBOX_MARKERS)


def video_inbox() -> Path | None:
    """Configured upload directory for full-resolution form-check videos.

    Returns ``None`` when unset — the caller then reports that the inbox is
    not configured rather than falling back to a guessed local path.
    """
    raw = os.environ.get("COACH_VIDEO_INBOX", "").strip()
    return Path(raw).expanduser() if raw else None

# Kamera-Winkel pro Übung
ANGLE_GUIDE: dict[str, str] = {
    "goblet squat": "schräg vorne (45°) — Knie-Tracking und Oberkörperlage",
    "box jump": "seitlich — Absprung, Flugphase, Landung",
    "dead bug": "seitlich — Lendenwirbel-Kontakt zum Boden",
    "hollow rock": "seitlich — Lendenwirbel-Kontakt, Arm-/Beinposition",
    "hollow hold": "seitlich — Lendenwirbel-Kontakt, Körperspannung",
    "l-sit": "seitlich oder schräg vorne — Hüfthöhe, Schulterposition",
    "pallof press": "schräg hinten (45°) — Rumpf-Rotation, Standbein",
    "trx row": "seitlich — Körperlinie, Ellbogen-Führung",
    "farmer": "seitlich oder von hinten — Schulterposition, Wirbelsäule",
    "kb horn pinch": "von vorne — Daumen-Finger-Spannung, Unterarm",
    "single leg rdl": "seitlich — Hüftachse, Knie-Softness, Rücken",
    "bulgarian split squat": "seitlich — Knie-Tracking, Oberkörperlage",
    "side plank": "seitlich (90°) — Hüfthöhe, Körperlinie, Auflagepunkt des Stützarms",
    "planche lean": "seitlich — Körperlinie, Schulterposition über Handgelenk",
    "push-up": "seitlich — Körperlinie, Ellbogen-Winkel",
    # Laufen
    "laufen sagittal": "seitlich (90°, 8–12m Distanz) — Fußaufsatz, Knieflexion, Hüftextension, Schrittlänge",
    "laufen posterior": "direkt von hinten (8–12m Distanz) — Beckenstabilität, Fußaufsatz-Symmetrie, Pronation",
    "run sagittal": "seitlich (90°, 8–12m Distanz) — Fußaufsatz, Knieflexion, Hüftextension, Schrittlänge",
    "run posterior": "direkt von hinten (8–12m Distanz) — Beckenstabilität, Fußaufsatz-Symmetrie, Pronation",
    "lauf sagittal": "seitlich (90°, 8–12m Distanz) — Fußaufsatz, Knieflexion, Hüftextension, Schrittlänge",
    "lauf posterior": "direkt von hinten (8–12m Distanz) — Beckenstabilität, Fußaufsatz-Symmetrie, Pronation",
}


def get_angle_tip(exercise: str) -> str:
    key = exercise.lower().strip()
    # Longest match wins. The previous two-way substring test let a short
    # exercise name borrow a longer entry's guidance ("Plank" matching
    # "side plank"), which silently hands the wrong checkpoints to the
    # evaluation. Only the pattern-in-name direction is meaningful.
    matches = [(pat, tip) for pat, tip in ANGLE_GUIDE.items() if pat in key]
    if matches:
        return max(matches, key=lambda pair: len(pair[0]))[1]
    if any(kw in key for kw in RUN_KEYWORDS):
        return "seitlich (90°, 8–12m Distanz) — Fußaufsatz, Hüftextension, Oberkörperhaltung"
    return "seitlich oder schräg vorne (45°) — Gesamtbewegung beurteilen"


# An ANGLE_GUIDE entry carries two different things separated by an em dash:
# the camera *geometry* ("seitlich (90°)") and the evaluation *focus*
# ("Hüfthöhe, Körperlinie, Auflagepunkt des Stützarms"). Only the geometry may
# reach the structure pass — the focus names the finding the observer is meant
# to look for, which is exactly the prior that pass exists to avoid. The focus
# belongs in the evaluation, where a hypothesis is legitimate.

def get_angle_geometry(exercise: str) -> str:
    """Camera geometry only — safe for the structure pass."""
    return get_angle_tip(exercise).split("—", 1)[0].strip()


def get_angle_focus(exercise: str) -> str:
    """Evaluation focus only (empty when the entry names no checkpoints)."""
    parts = get_angle_tip(exercise).split("—", 1)
    return parts[1].strip() if len(parts) > 1 else ""


def is_run_exercise(exercise: str) -> bool:
    key = exercise.lower()
    return any(kw in key for kw in RUN_KEYWORDS)


# Begriffe, die eine konkrete AUSFÜHRUNG beschreiben (Haltung/Tiefe/Seite/Tempo).
# Solche Details gehören NICHT in --context: das Modell bestätigt sie sonst,
# statt sie aus dem Video zu lesen (Confirmation Bias). Erlaubt sind
# Verletzungen/Restriktionen/Sport-Profil; Ausführungs-Vorgaben nicht.
_SEEDING_PATTERNS = (
    "frontal", "goblet", "vor der brust", "gehalten", "hält die", "haelt die",
    "kontralateral", "ipsilateral", "über kopf", "ueber kopf",
    "bein vorne", "vorderes bein", "tempo 3", "tempo 2",
    # Contact-point and laterality vocabulary. These are the terms a correction
    # after a wrong structural finding is phrased in, and handing the model the
    # right answer produces a confirmation, not an observation.
    "unterarm", "ellbogen", "gestreckter arm", "gestreckten arm",
    "gestapelt", "gestaffelt", "stützarm", "stuetzarm", "stützhand", "stuetzhand",
    "linke seite", "rechte seite", "auf dem arm", "aufgestützt", "aufgestuetzt",
)


def _warn_on_seeded_context(context: str) -> list[str]:
    """Warnt, wenn --context die Ausführung beschreibt (Seeding-Risiko).

    Gibt die getroffenen Begriffe zurück (für Tests); druckt eine Warnung
    nach stderr. Non-blocking — die Analyse läuft weiter.
    """
    if not context:
        return []
    low = context.lower()
    hits = [p for p in _SEEDING_PATTERNS if p in low]
    if hits:
        print(
            "  ⚠️  --context beschreibt evtl. die AUSFÜHRUNG "
            f"({', '.join(hits)}) — das seedet die Analyse (Confirmation Bias). "
            "Nur Verletzungen/Restriktionen/Sport-Profil übergeben; Haltung/Tiefe/"
            "Seite liest das Modell selbst aus dem Video.",
            file=sys.stderr,
        )
    return hits


# ─── Checkliste ──────────────────────────────────────────────────────────────

def load_checklist(exercise: str) -> str:
    from app.utils.paths import resolve_config
    try:
        path = resolve_config("exercise_checklist.md")
    except FileNotFoundError:
        return ""
    content = path.read_text()
    key = exercise.lower()
    lines = content.split("\n")
    in_section, result = False, []
    for line in lines:
        if line.lower().startswith("##") and key in line.lower():
            in_section = True
            result.append(line)
        elif in_section and line.startswith("##"):
            break
        elif in_section:
            result.append(line)
    return "\n".join(result).strip()


# ─── System-Prompts ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Du bist ein erfahrener Bewegungsanalyst und Sportphysiologe. Du analysierst Trainingsvideos auf Ausführungsqualität und sportphysiologische Sinnhaftigkeit.

Die folgenden Bilder sind chronologisch geordnete Frames aus einem Trainings-Video. Sie zeigen eine einzelne Trainingsübung eines Athleten. Sport-Profil, aktuelle Restriktionen und Verletzungen — sofern relevant — stehen im `Athlet-Kontext`-Feld der User-Message; berücksichtige sie bei Bewertung und Dosierungs-Challenge.

KRITISCH — Beobachtung vor Bewertung (gegen Confirmation Bias):
- Der `Athlet-Kontext` und der Übungsname beschreiben NIE, WIE die Übung tatsächlich ausgeführt wird (Gewicht-Haltung, Tiefe, welches Bein vorne, Tempo). Solche Details liest du AUSSCHLIESSLICH aus den Frames — nimm sie NIEMALS aus Kontext oder Übungsname an.
- Beginne IMMER mit einem `Was ich sehe`-Block: Kamerawinkel; welches Gerät/Gewicht und WO/WIE es gehalten wird (welche Hand, vor der Brust / seitlich / über Kopf / kein Gewicht); welche Körperseite/welches Bein vorne. Erst danach bewerten.
- Für jedes Detail, das aus dem Winkel NICHT sicher erkennbar ist, schreibe ausdrücklich „nicht sicher erkennbar" — niemals raten, niemals mit Lehrbuch-Prosa füllen. Was du nicht in den Frames siehst, darf nicht in die Bewertung einfließen.

Analysiere die Bewegungssequenz in zwei Ebenen:
1. Ausführungsqualität — was siehst du konkret in den Frames?
2. Challenge — ist diese Übung und Dosierung für diesen Athleten gerade optimal?

ORIENTIERUNG ZUERST PRÜFEN: Steht der Athlet aufrecht im Bild? Wenn er quer oder
auf dem Kopf liegt, ist das Video gedreht — Gelenkwinkel und Links/Rechts-Aussagen
sind dann wertlos. NICHT im Kopf zurechtdrehen und trotzdem analysieren.
Schreibe stattdessen NUR: "❌ Video nicht auswertbar: Bild ist gedreht (Athlet liegt
quer/kopfüber im Bild)\n📹 Nächstes Mal: Analyse mit --rotate 90 (bzw. 180/270) erneut starten"

Wenn die Frames nicht aussagekräftig sind (unscharf, falscher Winkel, Athlet außerhalb Bild, Beleuchtung):
Schreibe NUR: "❌ Video nicht auswertbar: [Grund]\n📹 Nächstes Mal: [was ändern]"
Keine Analyse durchführen wenn die Qualität nicht reicht."""

SYSTEM_PROMPT_RUN = """Du bist ein erfahrener Lauf-Biomechanik-Experte. Du analysierst Laufvideos auf Technikqualität und Verletzungsrisiko.

Die folgenden Bilder sind chronologisch geordnete Frames aus einem Laufvideo — sie zeigen einen oder mehrere Gangzyklen eines Athleten. Aktive Verletzungen, Reha-Phasen oder Restriktionen — sofern relevant — stehen im `Athlet-Kontext`-Feld der User-Message; gewichte deine Beobachtungen entsprechend.

KRITISCH — Beobachtung vor Bewertung (gegen Confirmation Bias): Beginne mit einem `Was ich sehe`-Block (Perspektive, Laufrichtung, sichtbarer Bildausschnitt — ganzer Körper / nur Beine / Distanz). Lies jeden Marker AUS den Frames; nimm nichts aus Lauftyp oder Kontext an. Für jeden Marker, der aus Winkel/Bildausschnitt NICHT sicher erkennbar ist, schreibe ausdrücklich „nicht sicher erkennbar" — niemals raten oder mit Lehrbuch-Prosa füllen.

Analysiere die Laufmechanik:
1. Fußaufsatz und Bodenphase (Dorsalflexion-Winkel beim Aufprall, Aufprallposition relativ zum Körperschwerpunkt)
2. Kadenz und Schrittlänge
3. Hüftextension beim Abdruck (vollständig?)
4. Kniehub und Schwungbeinführung
5. Oberkörper-Vorneigung und Rumpfstabilität
6. Armarbeit (Ellbogenwinkel, keine Mittellinie-Überkreuzung)

Bei posteriorer Kamera zusätzlich:
- Beckenstabilität (Trendelenburg — Absinken zur Seite?)
- Pronationsgrad und Fersensymmetrie
- Schulterachse (Asymmetrie = Kompensation?)

ORIENTIERUNG ZUERST PRÜFEN: Läuft der Athlet aufrecht im Bild? Liegt er quer oder
kopfüber, ist das Video gedreht — Gelenkwinkel, Fußaufsatz und Links/Rechts-Aussagen
sind dann wertlos. NICHT im Kopf zurechtdrehen und trotzdem analysieren.
Schreibe stattdessen NUR: "❌ Video nicht auswertbar: Bild ist gedreht (Athlet liegt
quer/kopfüber im Bild)\n📹 Nächstes Mal: Analyse mit --rotate 90 (bzw. 180/270) erneut starten"

Wenn die Frames nicht aussagekräftig sind (unscharf, Athlet zu weit weg, falscher Winkel, nur Rücken oder Füße sichtbar):
Schreibe NUR: "❌ Video nicht auswertbar: [Grund]\n📹 Nächstes Mal: [was ändern — Distanz, Winkel, Bildausschnitt]"
Keine Analyse wenn Qualität nicht reicht."""


# ─── Gemini via OpenRouter ───────────────────────────────────────────────────

VIDEO_SIZE_LIMIT_MB = 50  # Hard ceiling — above this we do not even attempt an upload.

# Practical payload target for the base64 data-URL upload.
#
# The file is base64-encoded into a single JSON request, which inflates it by
# ~33 %. Well below VIDEO_SIZE_LIMIT_MB the provider starts returning an empty
# response after a long upload instead of an error — observed reproducibly at
# ~36 MB (three attempts, both model tiers, each failing only after 10-12
# minutes), while a ~13 MB clip of the same footage succeeded first try. The
# hard limit alone therefore does not protect the caller: it lets a request
# through that is going to fail slowly and silently.
#
# So anything above this target is re-encoded down before upload rather than
# sent as-is.
VIDEO_UPLOAD_TARGET_MB = 15.0

# Orientation. Two different failure modes get confused with each other:
#
#   1. Rotation *metadata* — the file is stored landscape with a display-matrix
#      flag. Every well-behaved decoder applies it, so the athlete comes out
#      upright. `--rotate auto` reads the flag and applies it explicitly, which
#      also protects any consumer that ignores it.
#   2. Rotation *in the content* — the file carries no flag at all and the
#      athlete is simply lying sideways in a landscape frame. This happens with
#      some phone and action-cam recordings. No amount of metadata handling can
#      detect it, because there is no metadata to read.
#
# Case 2 is the dangerous one: a form check reads joint angles and left/right
# detail, and both are meaningless on a rotated frame — the model does not
# refuse, it confidently describes a sideways athlete. So the operator can force
# the correction with `--rotate 90|180|270` (counter-clockwise degrees), and the
# perception prompt separately instructs the model to reject a sideways clip
# instead of analysing it.
VALID_ROTATIONS = (0, 90, 180, 270)

# Input options for every ffmpeg call that rotates the picture itself.
#
# `-noautorotate` alone is not enough, and the gap is invisible until a
# downstream decoder disagrees: it stops ffmpeg from applying the display
# matrix, but the matrix is still *copied into the output container*. A clip
# rotated by our own transpose filter therefore reaches the model with the
# correction baked in **and** an instruction to apply it again — the athlete
# ends up 90° from where the pipeline believes he is. Extracted stills escape
# this only because JPEG carries no such field.
#
# `-display_rotation` (ffmpeg ≥ 6) overrides the input's rotation to zero, so
# nothing is applied on read and nothing is written on output. The binary is the
# pinned `imageio-ffmpeg` build, not the host's, so the version is ours to rely
# on.
ROTATION_NEUTRAL_INPUT = ["-display_rotation:v:0", "0"]

# Re-encode ladder, tried in order until the output fits the target. Each step
# is (long-edge pixels, CRF). Resolution is reduced before quality because form
# checks depend on joint-position clarity more than on pixel count.
_COMPRESSION_LADDER: list[tuple[int, int]] = [
    (1280, 28),
    (960, 30),
    (720, 32),
]


def _openrouter_client() -> object:
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY nicht gesetzt in .env")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    if os.environ.get("CLAUDE_CODE_ENABLE_TELEMETRY"):
        try:
            from langsmith.wrappers import wrap_openai
            client = wrap_openai(client)
        except ImportError:
            pass
    return client


def _build_user_prompt(exercise: str, checklist: str, context: str, angle: str, run_mode: bool) -> str:
    checklist_block = f"\nÜbungs-Checkliste:\n{checklist}" if checklist else ""
    context_block = f"\nAthlet-Kontext: {context}" if context else ""
    if run_mode:
        return f"""Übung/Lauftyp: {exercise}
Kamerawinkel: {angle or get_angle_tip(exercise)}{checklist_block}{context_block}

Antworte in diesem Format (maximal 10–12 Sätze):

**{exercise} — Lauf-Formcheck**

**Was ich sehe**
[Perspektive/Kamerawinkel; Laufrichtung; sichtbarer Bildausschnitt (ganzer Körper / nur Beine / Distanz). Nicht sicher erkennbare Marker ausdrücklich „nicht sicher erkennbar" — nicht aus Lauftyp/Kontext annehmen.]

**Technik**
[2–3 konkrete Beobachtungen — nur was in den Frames sichtbar ist, keine Spekulation]

**Priorität für nächste Session**
[1 konkreter Korrekturpunkt — präzise und umsetzbar, mit Drill-Empfehlung]

**Risiko-Check**
[Fußaufsatz: Dorsalflexion-Winkel, Aufprallposition relativ zum Körperschwerpunkt; weitere athleten-spezifische Risiko-Marker falls im Athlet-Kontext genannt]"""
    else:
        return f"""Übung: {exercise}
Kamerawinkel: {angle or get_angle_tip(exercise)}{checklist_block}{context_block}

Antworte in diesem Format (maximal 10–12 Sätze):

**{exercise} — Formcheck**

**Was ich sehe**
[Kamerawinkel; Gerät/Gewicht + WO/WIE gehalten (welche Hand, vor der Brust / seitlich / über Kopf / kein Gewicht); welches Bein/welche Seite vorne. Nicht sicher erkennbare Details ausdrücklich „nicht sicher erkennbar" — NICHT aus Übungsname/Kontext annehmen.]

**Ausführung**
[2–3 konkrete Beobachtungen — nur was in den Frames sichtbar ist, keine Spekulation]

**Drill für nächste Session**
[1 konkreter Korrekturpunkt]

**Challenge**
[Ist diese Übung + Ansatz optimal? Wenn ja: "Passt so." Wenn nein: was wäre besser?]"""


# ─── Two-pass: perception without athlete context, then evaluation ──────────
#
# Athlete context in the same call as the video lets a supplied hypothesis
# colour the perception: the model reports the finding it was handed, at a
# confidence the footage does not support. Post-hoc "are you sure?" checking
# makes this measurably worse, so the countermeasure has to be structural.
#
# Pass 1 sees the video and NO athlete context, and may only describe.
# Pass 2 sees only pass 1's text — never the video — and gets the athlete
# context there. A hypothesis therefore cannot reach the pixels.
# Rationale + sources: framework/research/video-form-check-model-selection.md

PERCEPTION_SYSTEM_PROMPT = """Du bist ein präziser Beobachter. Du beschreibst ausschliesslich, was in einem Video sichtbar ist.

Du bewertest NICHT. Verboten sind Wertungen und Ursachenzuschreibungen jeder Art — auch implizite. Verbotene Wörter: gut, schlecht, sauber, instabil, kompensiert, zu tief, zu hoch, korrekt, falsch, ermüdungsbedingt, Schwäche, Defizit.

Für JEDE Beobachtung gibst du eine Sicherheitsangabe an: `sicher` | `unsicher` | `nicht erkennbar`.
`nicht erkennbar` ist eine vollwertige und ausdrücklich erwünschte Antwort. Eine ehrliche Enthaltung ist wertvoller als eine geratene Beobachtung — geratene Details führen stromabwärts zu falschen Trainingsentscheidungen.

Regeln:
- Räumliche Relationen zerlegst du, statt sie zusammenzufassen: vorne/hinten in Tiefenrichtung, Kontaktpunkte, Verdeckungen (verdeckt ein Körperteil ein anderes?).
- **Seitigkeit ist IMMER anatomisch anzugeben — aus Sicht des Athleten, nicht aus Sicht der Kamera.** Eine der Kamera zugewandte Körperseite kann im Bild links erscheinen und anatomisch rechts sein. Nenne zu jeder Seitenangabe (a) die anatomische Seite, (b) auf welcher Bildseite sie erscheint, und (c) woran du die anatomische Zuordnung festmachst (Blickrichtung des Gesichts, Bauch-/Rückenseite, Daumenstellung, Fussstellung). Wenn die anatomische Zuordnung nicht sicher ableitbar ist: `nicht erkennbar` — rate NIEMALS. Eine vertauschte Seitigkeit macht die gesamte Bewertung stromabwärts falsch.
- Jede Beobachtung bekommt einen Zeitstempel [mm:ss].
- Trendwörter (progressiv, zunehmend, im Verlauf, lässt nach) sind NUR zulässig, wenn du zwei Zeitstempel zitierst UND die Differenz konkret benennst. Andernfalls schreibst du „kein Trend belegbar".
- Was ausserhalb des Bildausschnitts liegt oder durch Kleidung, Winkel oder Unschärfe verdeckt ist, meldest du als `nicht erkennbar` — mit Angabe des Grundes."""


def _build_perception_prompt(exercise: str, angle: str, run_mode: bool) -> str:
    """Movement pass. No athlete context, no checklist — and no exercise name.

    ``exercise`` and ``angle`` are accepted for call-site compatibility and
    deliberately unused: naming the exercise hands the model a textbook picture,
    and the sharpest confabulation on record was precisely the standard coaching
    cue of the named movement, reported for a clip that never showed it. The
    structural questions this pass used to ask now belong to the structure pass,
    which asks them of stills; what is left here is what only video can answer.
    """
    del exercise, angle  # see docstring — priors, not inputs
    subject = "eine laufende Person" if run_mode else "eine trainierende Person"
    extra = (
        "- Fussaufsatz relativ zum Körperschwerpunkt, Kniewinkel bei Bodenkontakt, Rumpfneigung, Armführung\n"
        if run_mode else
        "- Bewegungstempo: zügig oder langsam, mit oder ohne Pause in den Endpositionen\n"
    )
    return f"""Das Video zeigt {subject}. Der Name der Übung wird dir bewusst nicht genannt — beschreibe, was zu sehen ist, nicht was zu einer Übung gehören würde.

Beschreibe ausschliesslich Sichtbares, in dieser Reihenfolge:

**1. Aufnahme**
Tatsächlicher Kamerawinkel und -höhe. Welcher Bildausschnitt ist zu sehen (ganzer Körper / Teilkörper)? Welche Körperteile sind zu KEINEM Zeitpunkt im Bild? Bildqualität/Unschärfe.

**2. Wiederholungen**
Wie viele voneinander abgegrenzte Wiederholungen sind zu sehen? Zeitstempel je Endposition. Ist es ein Halt ohne Wiederholungen, sage das.

**3. Erste Wiederholung** [mm:ss]
Beschreibe die Endposition der ersten Wiederholung isoliert.

**4. Letzte Wiederholung** [mm:ss]
Beschreibe die Endposition der letzten Wiederholung isoliert.

**5. Differenz**
Erst jetzt: Unterscheiden sich 3 und 4? Trendwörter nur mit zwei Zeitstempeln und konkreter Differenz, sonst „kein Trend belegbar".
{extra}
**6. Nicht beurteilbar**
Liste explizit auf, welche anatomischen Strukturen aus diesem Winkel NICHT beurteilbar sind und warum.

Auflagepunkte, Seitigkeit und Gerät beschreibst du hier NICHT — die werden getrennt an Standbildern erhoben. Halte dich knapp. Keine Bewertung, keine Empfehlung, keine Ursachen."""


# ─── Stage A: structure, asked of stills ────────────────────────────
#
# Every wrong finding this pipeline has produced was a *static structural* claim:
# which limb carries the load, on which surface (forearm vs. extended arm), which
# anatomical side, which implement, from which angle it was filmed. None was
# temporal. Two properties of the video path explain that.
#
# First, budget. A video frame is billed at 70 tokens on every media-resolution
# setting except `high` (280), and the OpenRouter transport exposes no way to ask
# for `high` — so the default is also the coarsest tier available. A still image
# gets 1120 tokens at the same default. The distinction between a forearm lying
# on the floor and an extended arm with the hand on the floor is a small region
# of a full-body frame; at 70 tokens it is simply not represented.
#
# Second, priors. Free prose under a known exercise name reproduces the textbook
# picture of that exercise. So this pass gets no exercise name, and it answers a
# closed-form questionnaire instead of writing a description — a forced choice
# between named options, with abstention as one of the options rather than as a
# discipline the model has to remember.

STRUCTURE_UNVERIFIED_MARKER = "⚠️ STRUKTUR UNVERIFIZIERT"

# Fields whose being wrong invalidates everything downstream. A swapped support
# side or a misread contact point does not degrade an assessment gracefully — it
# produces a confident finding about a movement that did not happen.
LOAD_BEARING_FIELDS = ("aufnahme", "koerperposition", "bodenkontakte", "geraet")

_CERTAIN = "sicher"

CONTACT_SEGMENTS_STRENGTH = (
    "Hand_gestreckter_Arm", "Hand_gebeugter_Arm", "Unterarm_Ellbogen",
    "Knie", "Schienbein", "Fuss", "Gesaess", "Huefte_Becken",
    "Ruecken_Schulterguertel", "kein_Kontakt", "nicht_erkennbar",
)
CONTACT_SEGMENTS_RUN = ("Ferse", "Mittelfuss", "Vorfuss", "kein_Kontakt", "nicht_erkennbar")

STRUCTURE_SYSTEM_PROMPT = """Du bist ein präziser Beobachter. Du beantwortest Fragen zu Standbildern ausschliesslich aus dem, was darin sichtbar ist.

Du bewertest NICHT. Keine Wertungen, keine Ursachenzuschreibungen, keine Empfehlungen. Verbotene Wörter: gut, schlecht, sauber, instabil, kompensiert, zu tief, zu hoch, korrekt, falsch, ermüdungsbedingt, Schwäche, Defizit.

`nicht_erkennbar` ist eine vollwertige und ausdrücklich erwünschte Antwort. Eine ehrliche Enthaltung ist wertvoller als eine geratene Beobachtung — geratene Details führen stromabwärts zu falschen Trainingsentscheidungen.

Du bekommst KEINEN Übungsnamen. Das ist Absicht: Ein Übungsname ruft ein Lehrbuchbild ab, und dieses Bild würde deine Beschreibung färben. Beschreibe, was auf den Bildern liegt — nicht, was zu einer Übung gehören würde. Nenne die Übung auch dann nicht, wenn du sie zu erkennen glaubst.

Regeln:
- **Seitigkeit ist IMMER anatomisch anzugeben — aus Sicht der Person, nicht aus Sicht der Kamera.** Eine der Kamera zugewandte Körperseite kann im Bild links erscheinen und anatomisch rechts sein. Gib zu jeder Seitenangabe an, auf welcher Bildseite sie erscheint und woran du die anatomische Zuordnung festmachst (Blickrichtung des Gesichts, Bauch-/Rückenseite, Daumenstellung, Fussstellung). Ist die Zuordnung nicht sicher ableitbar: `nicht_erkennbar` — rate NIEMALS. Eine vertauschte Seitigkeit macht die gesamte Bewertung stromabwärts falsch.
- Auflagepunkte zerlegst du. Für jedes Körperteil mit Bodenkontakt nennst du das konkrete Segment, das aufliegt. Ein Arm kann über die flache Hand bei gestrecktem Ellbogen aufliegen oder über den Unterarm mit dem Ellbogen am Boden — das sind verschiedene Antworten. Wähle die zutreffende aus der vorgegebenen Liste oder `nicht_erkennbar`.
- Jede Angabe bekommt einen `belegframe`: den Dateinamen des Bildes, auf dem du sie ablesen kannst. Nenne das Bild, das die Angabe am deutlichsten zeigt.
- Was ausserhalb des Bildausschnitts liegt oder durch Kleidung, Winkel oder Unschärfe verdeckt ist, meldest du als `nicht_erkennbar` — mit Angabe des Grundes.

Du antwortest AUSSCHLIESSLICH mit einem JSON-Objekt nach dem vorgegebenen Schema. Kein Fliesstext davor oder danach."""


def _build_structure_prompt(frame_names: list[str], run_mode: bool) -> str:
    """Stage-A prompt: no exercise name, no checklist, no athlete context.

    No expected camera angle either. By analysis time the shot already exists,
    so telling the model what angle was *intended* supplies nothing but a prior
    to confirm — and the camera geometry has itself been misread before, which
    makes it a question to ask rather than a fact to hand over.
    """
    segments = CONTACT_SEGMENTS_RUN if run_mode else CONTACT_SEGMENTS_STRENGTH
    enum = " | ".join(segments)
    listing = "\n".join(f"  {n}" for n in frame_names)
    subject = "einer laufenden Person" if run_mode else "einer trainierenden Person"
    return f"""Die folgenden {len(frame_names)} Standbilder stammen chronologisch aus einer Aufnahme {subject}:
{listing}

Antworte mit genau diesem JSON-Objekt:

{{
  "aufnahme": {{
    "kamera_winkel": "<frontal | schraeg_vorne | seitlich | schraeg_hinten | dorsal | von_oben | nicht_erkennbar>",
    "kamera_hoehe": "<bodennah | huefthoch | brusthoch | kopfhoch | nicht_erkennbar>",
    "bildausschnitt": "<ganzer_koerper | teilkoerper>",
    "nie_im_bild": ["<Körperteile, die zu keinem Zeitpunkt sichtbar sind>"],
    "belegframe": "<Dateiname>",
    "sicherheit": "sicher | unsicher | nicht_erkennbar"
  }},
  "koerperposition": {{
    "grundposition": "<liegend_seitlich | liegend_rueck | liegend_bauch | sitzend | stehend | vierfuessler | haengend | nicht_erkennbar>",
    "koerperlaengsachse": "<horizontal | vertikal | schraeg | nicht_erkennbar>",
    "belegframe": "<Dateiname>",
    "sicherheit": "sicher | unsicher | nicht_erkennbar"
  }},
  "bodenkontakte": [
    {{
      "koerperteil": "<Arm | Bein | Rumpf | Kopf>",
      "kontakt": "<{enum}>",
      "anatomische_seite": "<links | rechts | beidseitig | nicht_erkennbar>",
      "bildseite": "<links | rechts | nicht_erkennbar>",
      "seite_begruendung": "<woran du die anatomische Zuordnung festmachst>",
      "belegframe": "<Dateiname>",
      "sicherheit": "sicher | unsicher | nicht_erkennbar"
    }}
  ],
  "geraet": {{
    "vorhanden": "<ja | nein | nicht_erkennbar>",
    "was": "<Gerät/Gewicht, oder leer>",
    "anatomische_hand": "<links | rechts | beide | keine | nicht_erkennbar>",
    "position": "<vor_der_brust | seitlich | ueber_kopf | am_boden | keine | nicht_erkennbar>",
    "belegframe": "<Dateiname>",
    "sicherheit": "sicher | unsicher | nicht_erkennbar"
  }},
  "nicht_beurteilbar": ["<Struktur> — <Grund>"]
}}

Liste unter "bodenkontakte" JEDES Körperteil auf, das den Boden oder eine Unterlage berührt. Erfinde keine Einträge für Körperteile ohne Kontakt."""


def _parse_structure_json(raw: str) -> dict:
    """Tolerant parse — models fence JSON even when told not to."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Struktur-Pass lieferte kein JSON-Objekt")
    return json.loads(text[start:end + 1])


def structure_gate(claims: dict, frame_names: tuple[str, ...] = ()) -> tuple[bool, list[str]]:
    """Are the load-bearing structural claims safe to build an assessment on?

    Returns ``(passed, reasons)``. A blocked check is not a pipeline failure — it
    is the pipeline declining to guess, which is the outcome this stage exists to
    produce. Anything not explicitly ``sicher`` blocks, a missing field included:
    silence is not a confirmation. A ``sicher`` claim that cites no extracted
    frame is downgraded too, because a claim whose evidence cannot be opened
    cannot be verified.
    """
    reasons: list[str] = []

    def check_evidence(label: str, entry: dict) -> None:
        if entry.get("sicherheit") != _CERTAIN:
            reasons.append(f"{label}: Sicherheit „{entry.get('sicherheit', '—')}“")
            return
        beleg = str(entry.get("belegframe") or "")
        if frame_names and beleg not in frame_names:
            reasons.append(f"{label}: Belegframe „{beleg or '—'}“ ist kein extrahiertes Bild")

    for field in LOAD_BEARING_FIELDS:
        if field not in claims:
            reasons.append(f"{field}: fehlt in der Struktur-Antwort")

    for field in ("aufnahme", "koerperposition", "geraet"):
        value = claims.get(field)
        if isinstance(value, dict):
            check_evidence(field, value)

    contacts = claims.get("bodenkontakte")
    if isinstance(contacts, list):
        if not contacts:
            reasons.append("bodenkontakte: kein einziger Auflagepunkt erhoben")
        for idx, contact in enumerate(contacts, start=1):
            if not isinstance(contact, dict):
                reasons.append(f"bodenkontakte[{idx}]: unlesbarer Eintrag")
                continue
            label = f"bodenkontakte[{contact.get('koerperteil', idx)}]"
            check_evidence(label, contact)
            if contact.get("kontakt") == "nicht_erkennbar":
                reasons.append(f"{label}: Auflagepunkt nicht erkennbar")
            if contact.get("anatomische_seite") == "nicht_erkennbar":
                reasons.append(f"{label}: anatomische Seite nicht erkennbar")
    elif "bodenkontakte" in claims:
        reasons.append("bodenkontakte: keine Liste")

    return (not reasons), reasons


def format_structure_block(claims: dict, frames: list) -> str:
    """The auditable evidence trail appended to every analysis."""
    frame_list = "\n".join(f"- {f}" for f in frames)
    return (
        "=== STRUKTUR (Stage A, an Standbildern erhoben, ohne Übungsname) ===\n"
        f"{json.dumps(claims, ensure_ascii=False, indent=2)}\n"
        f"\nFrames (Belege für die Verifikation):\n{frame_list}"
    )


def blocked_by_structure_gate(reasons: list[str], frames: list, angle_focus: str) -> str:
    """Output for a blocked check: the open question, never a hedged finding."""
    lines = ["❌ Formcheck blockiert: Struktur nicht belastbar erhoben.", "", "Offen geblieben ist:"]
    lines += [f"- {r}" for r in reasons]
    lines += [
        "",
        "📹 Nächstes Mal: senkrecht zur Beobachtungsebene filmen, ganzer Körper im Bild, "
        "Kamera fix (Stativ), 20–40 s / 3–6 Wiederholungen.",
    ]
    if angle_focus:
        lines.append(f"   Zu beurteilen wäre: {angle_focus}")
    if frames:
        lines += ["", "Frames zum Selbst-Nachsehen:"] + [f"- {f}" for f in frames]
    return "\n".join(lines)


def analyse_structure_frames(
    client: object,
    model: str,
    frames: list,
    run_mode: bool,
    max_tok: int,
) -> dict:
    """Stage A — closed-form structural questionnaire on full-resolution stills."""
    content: list = [
        {"type": "text",
         "text": _build_structure_prompt([f.name for f in frames], run_mode)}
    ]
    for frame in frames:
        b64 = base64.b64encode(frame.read_bytes()).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

    response = client.chat.completions.create(  # type: ignore[attr-defined]
        model=model,
        max_tokens=max_tok,
        messages=[
            {"role": "system", "content": STRUCTURE_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        extra_headers={"X-Title": settings.openrouter_x_title},
    )
    return _parse_structure_json(_first_choice_content(response, model, "Stage A"))


def _build_evaluation_prompt(
    exercise: str, checklist: str, context: str, angle: str, run_mode: bool, perception: str,
    structure: dict | None = None,
) -> str:
    """Evaluation prompt. Sees only text — never the video, never the frames."""
    checklist_block = f"\nÜbungs-Checkliste:\n{checklist}" if checklist else ""
    context_block = f"\nAthlet-Kontext: {context}" if context else ""
    body = _build_user_prompt(exercise, checklist, context, angle, run_mode)
    structure_block = (
        "\n\n=== STRUKTUR (an Standbildern erhoben, ohne Übungsname) ===\n"
        + json.dumps(structure, ensure_ascii=False, indent=2)
        + "\n=== ENDE STRUKTUR ==="
    ) if structure else ""
    # Reuse the established output format, but bind it to the observation text.
    return f"""Ein unabhängiger Beobachter hat das Video beschrieben, OHNE den Athleten-Kontext zu kennen. Du siehst das Video selbst nicht — nur diese Beschreibung.

=== BEOBACHTUNG (Videobeschreibung) ===
{perception}
=== ENDE BEOBACHTUNG ==={structure_block}{checklist_block}{context_block}

Bewerte auf dieser Grundlage.

HARTE REGELN:
- Du darfst NICHTS behaupten, was nicht in der Beobachtung steht. Ergänze keine Details aus dem Übungsnamen, aus dem Athleten-Kontext oder aus Lehrbuchwissen.
- Was der Beobachter als `nicht erkennbar` gemeldet hat, bleibt offen. Formuliere es als offene Frage samt Angabe, welcher Kamerawinkel sie beantworten würde — niemals als Befund.
- Was der Beobachter mit `unsicher` markiert hat, kennzeichnest du in deiner Bewertung ebenfalls als unsicher.
- **Seitenangaben des Beobachters sind anatomisch zu lesen** (aus Sicht des Athleten). Hat der Beobachter die anatomische Zuordnung als `nicht erkennbar` gemeldet, darfst du KEINE seitenabhängige Aussage treffen — insbesondere keine Aussage darüber, ob eine Reha-Seite belastet wird oder nicht.
- Der Athleten-Kontext dient der Einordnung und der Dosierungs-Frage. Er ist KEIN Beleg dafür, dass ein bekanntes Muster im Video vorliegt — wenn die Beobachtung es nicht hergibt, liegt es nicht vor.
- **Der STRUKTUR-Block hat Vorrang.** Auflagepunkte, Seitigkeit, Gerät und Kamerawinkel wurden an Standbildern mit deutlich höherer Auflösung erhoben als der Videopfad sie hat. Widerspricht die Videobeschreibung dem Struktur-Block in einem dieser Punkte, gilt der Struktur-Block — und du benennst den Widerspruch ausdrücklich, statt ihn zu glätten.

{body}"""


def _first_choice_content(response: object, model: str, stage: str) -> str:
    """The one message content, or a RuntimeError that names what went wrong.

    A truncated answer is called by its name here. It used to surface as a JSON
    parse error two frames up, where the handler advised shrinking the video —
    the one remedy that cannot help, because the budget was spent on reasoning
    tokens before the answer began.
    """
    choices = getattr(response, "choices", None)
    if not choices:
        raise RuntimeError(f"Leere Antwort von {model} ({stage}) — kein choices-Array zurückgegeben")
    choice = choices[0]
    out = choice.message.content
    if getattr(choice, "finish_reason", None) == "length":
        used = getattr(getattr(response, "usage", None), "completion_tokens", "?")
        raise RuntimeError(
            f"Antwort von {model} ({stage}) bei max_tokens abgeschnitten ({used} Tokens verbraucht) — "
            f"Denk-Tokens haben das Budget aufgebraucht. MAX_TOKENS im Script erhöhen; "
            f"das Video zu kürzen hilft hier nicht."
        )
    if not out:
        raise RuntimeError(f"Leere Antwort-Content von {model} ({stage}) — choices vorhanden aber leer")
    return out


def _call_openrouter_text(client: object, model: str, system: str, user: str, max_tok: int) -> str:
    """Plain text completion — used for the evaluation pass (no video payload)."""
    response = client.chat.completions.create(  # type: ignore[attr-defined]
        model=model,
        max_tokens=max_tok,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return _first_choice_content(response, model, "Stage C")


def analyse_with_gemini_video(
    video_path: str,
    exercise: str,
    checklist: str,
    context: str,
    angle: str,
    model_key: str = DEFAULT_MODEL,
    run_mode: bool = False,
    section_label: str = "",
    rotate: int | None = None,
    structure_frames: int = 0,
    frames_dir: str = "",
    skip_structure_gate: bool = False,
) -> str:
    """Formcheck in drei Stufen: Struktur (Standbilder) → Bewegung (Video) → Bewertung.

    ``rotate`` is degrees counter-clockwise to apply before upload; ``None``
    means read the container's display matrix (see VALID_ROTATIONS).
    """
    size_mb = Path(video_path).stat().st_size / (1024 * 1024)
    if size_mb > VIDEO_SIZE_LIMIT_MB:
        raise ValueError(f"Video zu groß für direkte Analyse ({size_mb:.1f}MB > {VIDEO_SIZE_LIMIT_MB}MB) — nutze Frames")

    source_path = video_path  # keep the untouched original for the still frames
    rotate_ccw = rotate if rotate is not None else _detect_metadata_rotation(video_path)
    if rotate_ccw:
        print(f"  Orientierung: drehe {rotate_ccw}° gegen den Uhrzeigersinn", file=sys.stderr)

    client = _openrouter_client()
    model = MODELS.get(model_key, MODELS[DEFAULT_MODEL])
    print(f"  Modell: {model}", file=sys.stderr)

    # ── Stage A ──────────────────────────────────────────────────────────────
    # Runs first, and on stills cut from the ORIGINAL file. Two reasons for the
    # ordering: the frames must not inherit the upload copy's downscaling (the
    # resolution is the entire point), and a blocked gate should cost nothing —
    # re-encoding a large clip can take minutes, and there is no sense paying
    # that for a check that is about to decline to produce a finding.
    structure: dict | None = None
    frames: list[Path] = []
    if structure_frames > 0:
        out_dir = structure_frames_dir(source_path, frames_dir)
        frames = extract_structure_frames(
            source_path, out_dir, count=structure_frames, rotate_ccw=rotate_ccw
        )
        print("  Stage A — Struktur an Standbildern...", file=sys.stderr)
        structure = analyse_structure_frames(
            client, model, frames, run_mode, MAX_TOKENS.get(model_key, MAX_TOKENS[DEFAULT_MODEL])
        )
        passed, reasons = structure_gate(structure, tuple(f.name for f in frames))
        if not passed:
            if skip_structure_gate:
                print(f"  ⚠️  Struktur-Gate übersprungen ({len(reasons)} offene Punkte).",
                      file=sys.stderr)
                structure["_gate_uebersprungen"] = reasons
            else:
                return blocked_by_structure_gate(
                    reasons, frames, get_angle_focus(exercise)
                ) + "\n\n" + format_structure_block(structure, frames)

    # ── Stage B ──────────────────────────────────────────────────────────────
    # Rotate upright and/or shrink before uploading. Above the practical payload
    # target the provider tends to answer with an empty body after a long upload
    # rather than with an error, so size is handled here rather than discovered
    # ten minutes later.
    if size_mb > VIDEO_UPLOAD_TARGET_MB:
        print(f"  {size_mb:.1f}MB über dem Upload-Ziel ({VIDEO_UPLOAD_TARGET_MB:.0f}MB) — bereite auf…",
              file=sys.stderr)
    prepared = _prepare_for_upload(video_path, rotate_ccw=rotate_ccw)
    if prepared:
        video_path = prepared
        size_mb = Path(video_path).stat().st_size / (1024 * 1024)
    elif size_mb > VIDEO_UPLOAD_TARGET_MB:
        print("  Aufbereitung brachte das Video nicht unter das Ziel — sende Original. "
              "Bei leerer Antwort das Video kürzen oder vorab verkleinern.",
              file=sys.stderr)

    print(f"  Stage B — Bewegung am Video ({size_mb:.1f}MB)...", file=sys.stderr)
    with open(video_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    # No athlete context, no checklist, no exercise name: the checklist names the
    # exact patterns the evaluation is looking for and would prime the
    # description just as the athlete context would.
    system_prompt = PERCEPTION_SYSTEM_PROMPT
    user_text = _build_perception_prompt(exercise, angle, run_mode)

    content: list = [
        {"type": "text", "text": user_text},
        {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{b64}"}},
    ]

    # Pro/thinking models need more tokens for reasoning + output
    max_tok = MAX_TOKENS.get(model_key, MAX_TOKENS[DEFAULT_MODEL])

    mode_tag = "running" if run_mode else "strength"
    span_name = f"Video analysis — {exercise} ({mode_tag})"
    if section_label:
        span_name = f"{span_name} · {section_label}"

    tracer = get_tracer("analyse_video")
    with tracer.start_as_current_span(span_name) as span:
        span.set_attribute("langsmith.trace.name", span_name)
        span.set_attribute("langsmith.span.kind", "llm")
        set_span_metadata(
            exercise=exercise,
            mode=mode_tag,
            model=model,
            video=Path(video_path).name,
            size_mb=round(size_mb, 1),
            section=section_label or None,
        )
        set_span_io(
            input={
                "exercise": exercise,
                "model": model,
                "video": Path(video_path).name,
                "size_mb": round(size_mb, 1),
                "checklist_lines": checklist.count("\n") if checklist else 0,
                "context": context[:200] if context else "",
            },
        )
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tok,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            extra_headers={"X-Title": settings.openrouter_x_title},
        )
        perception = _first_choice_content(response, model, "Stage B")

        # An unusable recording is reported by pass 1 and must not be talked
        # into a finding by pass 2 — return it verbatim.
        if perception.lstrip().startswith("❌"):
            set_span_io(output=perception)
            return perception

        print("  Stage C — Bewertung (nur Text, ohne Video, ohne Frames)...", file=sys.stderr)
        eval_system = SYSTEM_PROMPT_RUN if run_mode else SYSTEM_PROMPT
        eval_user = _build_evaluation_prompt(
            exercise, checklist, context, angle, run_mode, perception, structure
        )
        content_out = _call_openrouter_text(client, model, eval_system, eval_user, max_tok)

        set_span_io(output=content_out)

    # The observation stays attached: it is the evidence the assessment rests
    # on, and it is what makes a wrong finding auditable after the fact.
    out = f"{content_out}\n\n---\n**Bewegung (Stage B, ohne Athleten-Kontext erhoben)**\n\n{perception}"
    if structure is not None:
        # The banner is load-bearing, not decoration: _update_exercise_log refuses
        # to persist while it is present, so an unattended run cannot put an
        # unverified structural claim in front of the specialists.
        out = (
            f"{STRUCTURE_UNVERIFIED_MARKER} — Strukturaussagen sind noch nicht gegen "
            f"die Frames geprüft.\n\n{out}\n\n---\n"
            f"{format_structure_block(structure, frames)}"
        )
    return out



# ─── Main ────────────────────────────────────────────────────────────────────

from app.utils.alerts import alert_on_failure
from app.utils.paths import CONFIG_DIR as _CONFIG_DIR

# exercise_log.md is athlete-specific (filled with each form check) → write
# always into CONFIG_DIR. If running with only config.example available,
# the file is created in CONFIG_DIR which may equal CONFIG_FALLBACK.
_EXERCISE_LOG = _CONFIG_DIR / "exercise_log.md"


def _update_exercise_log(exercise: str, video_filename: str, summary: str, date_str: str) -> None:
    """Update or append entry in config/exercise_log.md.

    Refuses to write while the finding still carries the unverified-structure
    banner. This is the point where a wrong structural claim used to become a
    training decision: specialists read this file, so a finding that has not been
    checked against the frames must not reach it. The verifying agent removes the
    banner once it has adjudicated, and only then does the entry get written.
    """
    import logging
    _log = logging.getLogger(__name__)
    if STRUCTURE_UNVERIFIED_MARKER in summary or summary.lstrip().startswith("❌"):
        _log.warning(
            "exercise_log.md nicht geschrieben: Struktur unverifiziert bzw. Formcheck blockiert. "
            "Erst nach Frame-Verifikation persistieren."
        )
        print("  ℹ️  exercise_log.md NICHT geschrieben — Struktur erst verifizieren.",
              file=sys.stderr)
        return
    log_path = _EXERCISE_LOG
    if not log_path.exists():
        # Vorher: silent return. Bei frischem Wrapper-Setup (nur config.example
        # vorhanden, kein realer exercise_log.md) ging die Gemini-Analyse stumm
        # verloren. Jetzt: leere Datei mit Header anlegen und warnen — die
        # erste Befund-Persistenz für jede neue Übung steht damit drin.
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                "# Exercise Log — Form-Befunde aus Video-Analysen\n\n"
                "Wird automatisch von `scripts/analyse_video.py` befüllt.\n",
                encoding="utf-8",
            )
            _log.warning("exercise_log.md fehlte — neu angelegt unter %s", log_path)
        except OSError as exc:
            _log.error(
                "exercise_log.md fehlt und konnte nicht angelegt werden (%s) — Analyse für '%s' nicht persistiert.",
                exc,
                exercise,
            )
            return

    from app.utils.sanitize import escape_for_prompt
    content = log_path.read_text(encoding="utf-8")
    section_header = f"## {exercise}"
    # Gemini-Response wird hier persistiert und später von Spezialisten als
    # Prompt-Input gelesen → schützen vor Format-/Markdown-Injection.
    short_summary = escape_for_prompt(summary.strip().replace("\n", " "), max_len=1200)

    new_block = (
        f"\n## {exercise}\n"
        f"**Letztes Video:** {date_str} | `{video_filename}`\n"
        f"**Befund:** {short_summary}\n"
        f"**Drill:** —\n"
        f"**Progression:** —\n"
        f"**Status:** aktiv\n"
    )

    if section_header in content:
        # Update existing section: replace Letztes Video + Befund lines, keep Drill/Progression/Status
        lines = content.splitlines(keepends=True)
        out: list[str] = []
        in_section = False
        for line in lines:
            if line.startswith(section_header):
                in_section = True
                out.append(line)
                continue
            if in_section and line.startswith("## "):
                in_section = False
            if in_section and line.startswith("**Letztes Video:**"):
                out.append(f"**Letztes Video:** {date_str} | `{video_filename}`\n")
                continue
            if in_section and line.startswith("**Befund:**"):
                out.append(f"**Befund:** {short_summary}\n")
                continue
            if in_section and line.startswith("**Status:**") and "abgeschlossen" not in line:
                out.append("**Status:** aktiv\n")
                continue
            out.append(line)
        log_path.write_text("".join(out), encoding="utf-8")
    else:
        # Append new section
        sep = "\n---\n" if not content.rstrip().endswith("---") else "\n"
        log_path.write_text(content.rstrip() + sep + new_block + "\n---\n", encoding="utf-8")

    import logging
    logging.getLogger(__name__).info("exercise_log updated: %s | %s", exercise, date_str)


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Video-Formcheck via Gemini (OpenRouter)")
    parser.add_argument("--video", default="", help="Pfad zur Video-Datei")
    parser.add_argument("--exercise", required=True, help="Übungsname")
    parser.add_argument("--context", default="", help="Optionaler Kontext (RPE-Feedback etc.)")
    parser.add_argument("--angle", default="", help="Kamerawinkel (z.B. 'seitlich', 'posterior')")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=list(MODELS.keys()),
                        help="Modell: pro (default, tiefere Analyse) oder flash (günstiger)")
    parser.add_argument("--structure-frames", type=int, default=6,
                        help="Standbilder für den Struktur-Pass (Stage A); 0 schaltet ihn ab")
    parser.add_argument("--frames-dir", default="",
                        help="Ablage der Standbilder (Default: <COACH_VIDEO_INBOX>/frames/<clip>)")
    parser.add_argument("--skip-structure-gate", action="store_true",
                        help="Notfall: Befund trotz unsicherer Struktur ausgeben (bleibt unsicher)")
    parser.add_argument("--angle-only", action="store_true", help="Nur Kamera-Empfehlung ausgeben")
    # Lauf-spezifische Parameter
    parser.add_argument("--multi-section", action="store_true",
                        help="Laufen: mehrere Abschnitte analysieren (frisch / Mitte / müde)")
    parser.add_argument("--garmin-sections", default="",
                        help="Laufen: Komma-getrennte Section-Typen aus Garmin-Daten "
                             "(z.B. 'frisch,bergauf,müde'). Benötigt --activity-id.")
    parser.add_argument("--activity-id", default="",
                        help="intervals.icu Activity-ID für Garmin-Section-Matching")
    parser.add_argument("--section-duration", type=int, default=25,
                        help="Länge pro Garmin-Section in Sekunden (default: 25)")
    parser.add_argument("--trim-start", type=float, default=0.0,
                        help="Sekunden vom Anfang abschneiden (default: 0)")
    parser.add_argument("--trim-end", type=float, default=0.0,
                        help="Sekunden vom Ende abschneiden (default: 0)")
    parser.add_argument("--rotate", default="auto",
                        help="Bild aufrichten: 'auto' liest die Rotations-Metadaten "
                             "(default), oder 0/90/180/270 Grad GEGEN den Uhrzeigersinn "
                             "erzwingen. Nötig, wenn der Athlet quer im Bild liegt und die "
                             "Datei KEIN Rotations-Flag trägt — ein Formcheck auf einem "
                             "gedrehten Bild liefert selbstbewusste Fehlbefunde.")
    parser.add_argument("--no-log", action="store_true",
                        help="exercise_log.md nicht aktualisieren (Ad-hoc-Analyse)")
    parser.add_argument("--allow-chat-video", action="store_true",
                        help="Chat-komprimiertes Video trotzdem analysieren "
                             "(Notfall — Perzeptionsfehler wahrscheinlich, Befund entsprechend kennzeichnen)")
    args = parser.parse_args()

    if args.angle_only:
        print(f"📹 Kamera-Empfehlung für '{args.exercise}':")
        print(f"   {get_angle_tip(args.exercise)}")
        return

    if args.video and is_chat_transport_path(args.video) and not args.allow_chat_video:
        inbox = video_inbox()
        target = str(inbox) if inbox else "(COACH_VIDEO_INBOX ist nicht gesetzt — Upload-Ziel bitte konfigurieren)"
        print(
            "⛔ Video über einen Chat-Kanal empfangen — Analyse abgelehnt.\n"
            "\n"
            "Chat-Kanäle rekodieren Videos beim Upload: Auflösung runter, Kompressions-\n"
            "artefakte rein. Ein Formcheck liest Gelenkwinkel, Gliedmassen-Positionen und\n"
            "Links/Rechts-Details aus Einzelbildern — genau das geht dabei verloren, und\n"
            "die Analyse liefert dann selbstbewusste Fehlbefunde statt gar keiner.\n"
            "\n"
            f"Original-Datei bitte unverändert hier ablegen:\n  {target}\n"
            "\n"
            "Danach erneut mit --video <Pfad-im-Inbox> aufrufen.\n"
            "Notfall-Override (Befund als unsicher kennzeichnen): --allow-chat-video",
            file=sys.stderr,
        )
        raise SystemExit(3)

    # Wrap the whole analysis run in a sprechende root span
    mode_label = "garmin-sections" if (args.garmin_sections and args.activity_id) else (
        "multi-section" if args.multi_section else "single"
    )
    display = f"Form check — {args.exercise} ({mode_label}, model={args.model})"
    with script_span(
        "analyse_video",
        display_name=display,
        exercise=args.exercise,
        model=args.model,
        mode=mode_label,
        video=Path(args.video).name if args.video else "(none)",
    ):
        _run_analysis(args)


def _resolve_rotate_arg(raw: str) -> int | None:
    """'auto' -> None (read metadata); an explicit degree value -> int."""
    value = (raw or "auto").strip().lower()
    if value == "auto":
        return None
    try:
        deg = int(value) % 360
    except ValueError:
        raise SystemExit(f"--rotate: 'auto' oder {VALID_ROTATIONS} erwartet, nicht {raw!r}")
    if deg not in VALID_ROTATIONS:
        raise SystemExit(f"--rotate: nur {VALID_ROTATIONS} (Grad gegen den Uhrzeigersinn), nicht {raw!r}")
    return deg


def _finish(args: argparse.Namespace, feedback: str) -> None:
    """Persist the finding — or decline to, and say so with an exit code.

    A blocked structure gate exits 4 rather than 0 so that a wrapper script or a
    cron-driven call cannot mistake "no finding was produced" for "the form was
    fine". The log write is guarded a second time inside _update_exercise_log;
    the duplication is deliberate, because that file is what the specialists read.
    """
    if not args.no_log and args.video:
        _update_exercise_log(
            args.exercise, Path(args.video).name, feedback, date.today().isoformat()
        )
    if feedback.lstrip().startswith("❌ Formcheck blockiert"):
        sys.exit(EXIT_STRUCTURE_GATE)


def _run_analysis(args: argparse.Namespace) -> None:

    # Trim video if requested
    if args.video and (args.trim_start > 0 or args.trim_end > 0):
        import tempfile as _tmp
        _dur = _probe_duration_sec(args.video)
        _start = args.trim_start
        _end = _dur - args.trim_end
        _trimmed = _tmp.NamedTemporaryFile(suffix=".mp4", delete=False).name
        ok = _trim_video_clip(args.video, _start, _end, _trimmed)
        if ok:
            print(f"  Trimmed: {_start:.1f}s–{_end:.1f}s → {_trimmed}", file=sys.stderr)
            args.video = _trimmed
        else:
            print("  Trim fehlgeschlagen — verwende Original.", file=sys.stderr)

    ex_lower = args.exercise.lower()
    run_mode = is_run_exercise(ex_lower)

    _warn_on_seeded_context(args.context)

    checklist = load_checklist(args.exercise)

    # Laufen: Garmin-gesteuerte Sections (intelligentes Matching)
    if run_mode and args.garmin_sections and args.activity_id:
        _run_garmin_sections(args, checklist)
        return

    # Laufen: Direkte Video-Analyse (kein lokales Frame-Decoding)
    if run_mode:
        if args.multi_section:
            _run_multi_section(args, checklist)
            return
        print("\nAnalysiere mit Gemini...", file=sys.stderr)
        try:
            feedback = analyse_with_gemini_video(
                args.video, args.exercise, checklist, args.context, args.angle,
                args.model, run_mode=True, rotate=_resolve_rotate_arg(args.rotate),
                structure_frames=args.structure_frames, frames_dir=args.frames_dir,
                skip_structure_gate=args.skip_structure_gate,
            )
        except FrameExtractionError as e:
            print(f"⚠️ Technischer Fehler: Standbilder nicht extrahierbar — {e}", file=sys.stderr)
            print("   Ohne Standbilder ist der Formcheck nicht belastbar. "
                  "ffmpeg prüfen oder --structure-frames 0 (Befund bleibt unsicher).",
                  file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"Fehler: {e}", file=sys.stderr)
            print("Video komprimieren oder in kürzere Clips aufteilen.", file=sys.stderr)
            sys.exit(1)
        print(feedback)
        _finish(args, feedback)
        return

    # Kraft/Core/Ninja: Direkte Video-Analyse (kein lokales Frame-Decoding)
    print("\nAnalysiere mit Gemini...", file=sys.stderr)
    try:
        feedback = analyse_with_gemini_video(
            args.video, args.exercise, checklist, args.context, args.angle,
            args.model, run_mode=False, rotate=_resolve_rotate_arg(args.rotate),
            structure_frames=args.structure_frames, frames_dir=args.frames_dir,
            skip_structure_gate=args.skip_structure_gate,
        )
    except FrameExtractionError as e:
        print(f"⚠️ Technischer Fehler: Standbilder nicht extrahierbar — {e}", file=sys.stderr)
        print("   Ohne Standbilder ist der Formcheck nicht belastbar. "
              "ffmpeg prüfen oder --structure-frames 0 (Befund bleibt unsicher).",
              file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Fehler: {e}", file=sys.stderr)
        print("Video komprimieren oder in kürzere Clips aufteilen.", file=sys.stderr)
        sys.exit(1)
    print(feedback)
    _finish(args, feedback)


def _trim_video_clip(video_path: str, start_sec: float, end_sec: float, out_path: str) -> bool:
    """Schneidet einen Video-Clip aus (stream copy, kein Re-Encoding)."""
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        duration = end_sec - start_sec
        result = subprocess.run(
            [ffmpeg, "-y", "-ss", str(start_sec), "-i", video_path,
             "-t", str(duration), "-c", "copy", "-avoid_negative_ts", "1", out_path],
            capture_output=True, timeout=30,
        )
        return result.returncode == 0 and Path(out_path).exists()
    except Exception as e:
        print(f"  Clip-Trimming fehlgeschlagen: {e}", file=sys.stderr)
        return False


class FrameExtractionError(RuntimeError):
    """Stage A could not obtain frames — never degrade silently to the video path."""


def _ffmpeg_exe() -> str | None:
    """Single resolution point for the bundled ffmpeg binary."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _probe_duration_sec(video_path: str) -> float:
    """Clip length in seconds, read from ffmpeg itself.

    Preferred over :func:`_get_video_duration_sec`, whose last resort is to
    return a hard-coded 60 s. A wrong duration is worse than no duration here:
    frame timestamps are derived from it, so a silent fallback would sample
    past the end of a short clip and quietly hand the structure pass fewer
    frames than it asked for — or, on a long clip, only its opening seconds.
    """
    ffmpeg = _ffmpeg_exe()
    if ffmpeg:
        try:
            # ffmpeg exits non-zero without an output file but still prints the
            # container metadata, which is all we need.
            result = subprocess.run(
                [ffmpeg, "-i", video_path], capture_output=True, timeout=30
            )
            text = result.stderr.decode("utf-8", errors="replace")
            marker = "Duration:"
            if marker in text:
                stamp = text.split(marker, 1)[1].split(",", 1)[0].strip()
                hours, minutes, seconds = stamp.split(":")
                total = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                if total > 0:
                    return total
        except Exception:
            pass
    return _get_video_duration_sec(video_path)


def structure_frames_dir(video_path: str, explicit: str = "") -> Path:
    """Where the extracted stills are written.

    Deliberately a persistent location, not a temp dir: the verification step
    reads these exact files as its evidence, and a claim whose evidence has
    already been deleted cannot be adjudicated afterwards.
    """
    if explicit:
        return Path(explicit).expanduser()
    inbox = video_inbox()
    if inbox:
        return inbox / "frames" / Path(video_path).stem
    import tempfile as _tmp
    return Path(_tmp.gettempdir()) / "coach_video_frames" / Path(video_path).stem


def extract_structure_frames(
    video_path: str,
    out_dir: Path,
    count: int = 6,
    rotate_ccw: int = 0,
) -> list[Path]:
    """Evenly spaced stills at source resolution — the input for the structure pass.

    Why stills at all, when the video is uploaded anyway: for *video* Gemini
    caps a frame at 70 tokens on every media-resolution setting except `high`
    (280), and the OpenRouter transport exposes no way to request `high`. Still
    images are not subject to that cap. Every wrong finding this pipeline has
    produced was a static structural claim — a contact point, a side, a piece of
    equipment, a camera angle — so those questions are asked of stills and the
    video is left to carry what it is actually good at, the movement over time.

    No downscale happens here on purpose; `_COMPRESSION_LADDER` exists for the
    video upload, and shrinking a frame would give back the detail this pass is
    for. JPEG at the top quality step keeps the request small enough to survive
    the upload (a large payload is a documented silent-failure mode here) while
    staying far above what the video path ever resolved.
    """
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        raise FrameExtractionError(
            "ffmpeg nicht verfügbar (Paket `imageio-ffmpeg`) — ohne Standbilder liefe "
            "der Formcheck wieder über den Video-Pfad, also genau in die Fehlerklasse "
            "zurück, die diese Stufe verhindert."
        )

    duration = _probe_duration_sec(video_path)
    if duration <= 0:
        raise FrameExtractionError("Video-Dauer nicht lesbar — keine Frames extrahierbar.")

    out_dir.mkdir(parents=True, exist_ok=True)
    filters = ["transpose=2"] * ((rotate_ccw % 360) // 90)
    frames: list[Path] = []

    for i in range(count):
        # Sample at interval midpoints so neither the first nor the last frame
        # lands on a cut, where a half-finished rep is common.
        ts = duration * (i + 0.5) / count
        # The timestamp is part of the filename because a verdict has to cite its
        # evidence: "refuted at frame_03_t00m11s.jpg" is checkable weeks later.
        out_path = out_dir / f"frame_{i + 1:02d}_t{int(ts) // 60:02d}m{int(ts) % 60:02d}s.jpg"
        cmd = [ffmpeg, "-y", *ROTATION_NEUTRAL_INPUT, "-ss", f"{ts:.3f}", "-i", video_path]
        if filters:
            cmd += ["-vf", ",".join(filters)]
        cmd += ["-frames:v", "1", "-q:v", "2", str(out_path)]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=60)
        except Exception as e:
            print(f"  Frame {i + 1} fehlgeschlagen: {e}", file=sys.stderr)
            continue
        if result.returncode == 0 and out_path.exists():
            frames.append(out_path)

    if not frames:
        raise FrameExtractionError(f"ffmpeg lieferte kein einziges Standbild aus {video_path}")
    total_mb = sum(f.stat().st_size for f in frames) / (1024 * 1024)
    print(f"  {len(frames)} Struktur-Frames → {out_dir} ({total_mb:.1f}MB)", file=sys.stderr)
    return frames


def _run_garmin_sections(args: argparse.Namespace, checklist: str) -> None:
    """Analysiert Garmin-definierte Sections als direkte Video-Clips.

    Ohne Struktur-Pass: Auflagepunkte und Seitigkeit ändern sich zwischen einer
    frischen und einer müden Section desselben Clips nicht, die Sections sind per
    Konstruktion eine zeitliche Frage.
    """
    import subprocess as sp
    import tempfile

    # extract_run_dynamics.py aufrufen um Sections zu ermitteln
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "extract_run_dynamics.py"),
        "--activity-id", args.activity_id,
        "--video", args.video,
        "--find-sections", args.garmin_sections,
        "--section-duration", str(args.section_duration),
    ]
    try:
        result = sp.run(cmd, capture_output=True, text=True, timeout=60)
        sections = json.loads(result.stdout)
    except Exception as e:
        print(f"Fehler beim Section-Finder: {e}", file=sys.stderr)
        return

    if not sections:
        print("Keine Sections gefunden", file=sys.stderr)
        return

    print(f"  {len(sections)} Sections gefunden", file=sys.stderr)
    client = _openrouter_client()
    model = MODELS.get(args.model, MODELS[DEFAULT_MODEL])

    with tempfile.TemporaryDirectory() as tmpdir:
        for sec in sections:
            label = sec["label"]
            start = float(sec["video_start_sec"])
            end = float(sec["video_end_sec"])
            ctx = sec.get("context", "")
            if args.context:
                ctx = f"{ctx} | {args.context}" if ctx else args.context

            clip_path = str(Path(tmpdir) / f"clip_{label.replace(' ', '_')}.mp4")

            print(f"\n── {label} ({start:.0f}s–{end:.0f}s) ──", file=sys.stderr)

            trimmed = _trim_video_clip(args.video, start, end, clip_path)
            if not trimmed:
                print(f"  Clip-Trimming fehlgeschlagen — Section {label} übersprungen", file=sys.stderr)
                continue

            clip_size_mb = Path(clip_path).stat().st_size / (1024 * 1024)
            if clip_size_mb > VIDEO_SIZE_LIMIT_MB:
                print(f"  Clip zu groß ({clip_size_mb:.1f}MB) — Section {label} übersprungen", file=sys.stderr)
                continue

            try:
                feedback = analyse_with_gemini_video(
                    clip_path, args.exercise, checklist, ctx, args.angle,
                    args.model, run_mode=True, section_label=label,
                    rotate=_resolve_rotate_arg(args.rotate),
                )
                print(f"\n### {label}\n")
                print(feedback)
                print()
            except Exception as e:
                print(f"  Video-Analyse fehlgeschlagen ({e}) — Section {label} übersprungen", file=sys.stderr)


def _detect_metadata_rotation(video_path: str) -> int:
    """Rotation in degrees CCW from the container's display matrix, 0 if absent.

    Only covers failure mode 1 (see VALID_ROTATIONS). A clip whose *content* is
    sideways without a flag reports 0 here — that case needs an explicit
    ``--rotate``.

    Read from ffmpeg rather than from PyAV. ffmpeg is a hard dependency of this
    module already (the structure pass cannot run without it), while PyAV is
    optional and its side-data API is not stable across versions: on PyAV 17
    ``stream.side_data`` is ``None`` even for a clip whose display matrix
    ffmpeg prints, so the old lookup returned 0 for every file. That failure is
    silent and it is the expensive kind — the frames then reach the structure
    pass lying on their side, and a sideways frame produces exactly the
    confident wrong contact-point / laterality claims this stage exists to
    prevent. PyAV stays as a fallback for deployments that ship it without
    ffmpeg.

    Sign convention: ``av_display_rotation_get`` (what the ``-i`` dump prints)
    is already the counter-clockwise correction to apply — a clip printing
    ``rotation of 90.00 degrees`` needs one ``transpose=2``, which is what
    ffmpeg's own autorotate inserts for it.
    """
    ffmpeg = _ffmpeg_exe()
    if ffmpeg:
        try:
            result = subprocess.run(
                [ffmpeg, "-i", video_path], capture_output=True, timeout=30
            )
            text = result.stderr.decode("utf-8", errors="replace")
            marker = "displaymatrix: rotation of"
            if marker in text:
                raw = text.split(marker, 1)[1].split("degrees", 1)[0].strip()
                deg = int(round(float(raw))) % 360
                if deg in VALID_ROTATIONS:
                    return deg
        except Exception:
            pass
    try:
        import av
        with av.open(video_path) as container:
            stream = container.streams.video[0]
            side = getattr(stream, "side_data", None)
            if not side:
                return 0
            for key in ("DISPLAYMATRIX", "displaymatrix"):
                try:
                    value = side[key]
                except Exception:
                    continue
                if value is None:
                    continue
                return int(round(float(getattr(value, "rotation", value)))) % 360
    except Exception:
        pass
    return 0


def _prepare_for_upload(
    video_path: str,
    rotate_ccw: int = 0,
    target_mb: float = VIDEO_UPLOAD_TARGET_MB,
) -> str | None:
    """Re-encode a clip for the upload: rotate upright and shrink below target.

    Returns the path of a temporary re-encoded file, or ``None`` when nothing
    could be produced (caller then decides whether to send the original).

    Prefers an ffmpeg binary when one is available and falls back to PyAV, since
    deployments differ in which of the two they ship.
    """
    import tempfile as _tmp

    needs_rotate = rotate_ccw % 360 != 0
    size_mb = Path(video_path).stat().st_size / (1024 * 1024)
    if not needs_rotate and size_mb <= target_mb:
        return None  # nothing to do

    ffmpeg = None
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg = None

    for long_edge, crf in _COMPRESSION_LADDER:
        out_path = _tmp.NamedTemporaryFile(suffix=".mp4", delete=False).name
        ok = False

        if ffmpeg:
            filters = []
            if needs_rotate:
                # transpose=2 is 90° CCW; chain it for 180/270.
                filters += ["transpose=2"] * ((rotate_ccw % 360) // 90)
            filters.append(
                f"scale='if(gt(iw,ih),min({long_edge},iw),-2)':"
                f"'if(gt(iw,ih),-2,min({long_edge},ih))'"
            )
            try:
                result = subprocess.run(
                    [ffmpeg, "-y", *ROTATION_NEUTRAL_INPUT, "-i", video_path,
                     "-vf", ",".join(filters),
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
                     "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
                     out_path],
                    capture_output=True, timeout=600,
                )
                ok = result.returncode == 0 and Path(out_path).exists()
            except Exception as e:
                print(f"  ffmpeg-Reencode fehlgeschlagen ({long_edge}px/CRF{crf}): {e}",
                      file=sys.stderr)
        else:
            ok = _reencode_with_pyav(video_path, out_path, rotate_ccw, long_edge, crf)

        if not ok:
            continue

        out_mb = Path(out_path).stat().st_size / (1024 * 1024)
        if out_mb <= target_mb:
            note = f", {rotate_ccw}° CCW gedreht" if needs_rotate else ""
            print(f"  Aufbereitet: {out_mb:.1f}MB (lange Kante {long_edge}px, CRF {crf}{note})",
                  file=sys.stderr)
            return out_path
        print(f"  {long_edge}px/CRF{crf} → {out_mb:.1f}MB, noch über {target_mb:.0f}MB",
              file=sys.stderr)

    return None


def _reencode_with_pyav(
    src: str, dst: str, rotate_ccw: int, long_edge: int, crf: int
) -> bool:
    """PyAV fallback for _prepare_for_upload when no ffmpeg binary is present."""
    try:
        import av
        from PIL import Image  # noqa: F401  (used via frame.to_image)
    except Exception as e:
        print(f"  Kein Reencode möglich (weder ffmpeg noch PyAV/Pillow: {e})", file=sys.stderr)
        return False

    try:
        with av.open(src) as inp, av.open(dst, "w") as out:
            in_stream = inp.streams.video[0]
            in_stream.thread_type = "AUTO"
            fps = in_stream.average_rate or 30

            out_stream = None
            for frame in inp.decode(in_stream):
                img = frame.to_image()
                if rotate_ccw % 360:
                    img = img.rotate(rotate_ccw % 360, expand=True)
                w, h = img.size
                scale = min(1.0, long_edge / max(w, h))
                if scale < 1.0:
                    # even dimensions required by yuv420p
                    img = img.resize((max(2, int(w * scale) // 2 * 2),
                                      max(2, int(h * scale) // 2 * 2)))

                if out_stream is None:
                    out_stream = out.add_stream("libx264", rate=fps)
                    out_stream.width, out_stream.height = img.size
                    out_stream.pix_fmt = "yuv420p"
                    out_stream.options = {"crf": str(crf), "preset": "veryfast"}

                new_frame = av.VideoFrame.from_image(img)
                for packet in out_stream.encode(new_frame):
                    out.mux(packet)

            if out_stream is not None:
                for packet in out_stream.encode():
                    out.mux(packet)
        return Path(dst).exists() and Path(dst).stat().st_size > 0
    except Exception as e:
        print(f"  PyAV-Reencode fehlgeschlagen ({long_edge}px/CRF{crf}): {e}", file=sys.stderr)
        return False


def _get_video_duration_sec(video_path: str) -> float:
    """Gibt Video-Länge in Sekunden zurück."""
    try:
        import imageio
        reader = imageio.get_reader(video_path, plugin="pyav")
        meta = reader.get_meta_data()
        reader.close()
        duration = meta.get("duration", None)
        if duration:
            return float(duration)
        fps = float(meta.get("fps", 30.0))
        nframes = meta.get("nframes", 0)
        if nframes and fps:
            return nframes / fps
    except Exception:
        pass
    try:
        all_frames = list(imageio.imiter(video_path, plugin="pyav"))
        fps = 30.0
        return len(all_frames) / fps
    except Exception:
        return 60.0


def _run_multi_section(args: argparse.Namespace, checklist: str) -> None:
    """Analysiert frisch / Mitte / müde als 3 direkte Video-Clips via OpenRouter."""
    import tempfile
    duration = _get_video_duration_sec(args.video)
    print(f"  Video-Länge: {duration:.1f}s → 3 Abschnitte", file=sys.stderr)

    sections = [
        ("Frisch (Anfang)", duration * 0.10, duration * 0.35),
        ("Mitte", duration * 0.40, duration * 0.65),
        ("Müde (Ende)", duration * 0.70, duration * 0.95),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        for label, start_sec, end_sec in sections:
            print(f"\n── {label} ({start_sec:.0f}s–{end_sec:.0f}s) ──", file=sys.stderr)
            clip_path = str(Path(tmpdir) / f"clip_{label.replace(' ', '_').replace('(', '').replace(')', '')}.mp4")
            trimmed = _trim_video_clip(args.video, start_sec, end_sec, clip_path)
            if not trimmed:
                print(f"  Clip-Trimming fehlgeschlagen — {label} übersprungen", file=sys.stderr)
                continue

            clip_size_mb = Path(clip_path).stat().st_size / (1024 * 1024)
            if clip_size_mb > VIDEO_SIZE_LIMIT_MB:
                print(f"  Clip zu groß ({clip_size_mb:.1f}MB) — {label} übersprungen", file=sys.stderr)
                continue

            context_with_label = f"[{label}]{' — ' + args.context if args.context else ''}"
            try:
                feedback = analyse_with_gemini_video(
                    clip_path, args.exercise, checklist, context_with_label, args.angle,
                    args.model, run_mode=True, section_label=label,
                    rotate=_resolve_rotate_arg(args.rotate),
                )
                print(f"\n### {label}\n")
                print(feedback)
                print()
            except Exception as e:
                print(f"  Video-Analyse fehlgeschlagen ({e}) — {label} übersprungen", file=sys.stderr)


if __name__ == "__main__":
    main()
