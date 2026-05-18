#!/usr/bin/env python3
"""Video-Formcheck via Gemini (OpenRouter) — Kraft/Core/Balance/Ninja/Laufen.

Flow:
1. Video laden, Motion-Trimming (Intro/Outro abschneiden) — bei Kraft
   Für Laufen: feste Fenster (erste 15% + letzte 10% überspringen)
2. N gleichmäßige Frames extrahieren
3. Frames als sequentielle Bilder an Gemini via OpenRouter
4. Strukturiertes Feedback: Ausführung / Drill / Challenge

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
MODELS = {
    "flash": "google/gemini-2.5-flash",
    "pro":   "google/gemini-2.5-pro",
}
DEFAULT_MODEL = "pro"

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
    for pattern, tip in ANGLE_GUIDE.items():
        if pattern in key or key in pattern:
            return tip
    if any(kw in key for kw in RUN_KEYWORDS):
        return "seitlich (90°, 8–12m Distanz) — Fußaufsatz, Hüftextension, Oberkörperhaltung"
    return "seitlich oder schräg vorne (45°) — Gesamtbewegung beurteilen"


def is_run_exercise(exercise: str) -> bool:
    key = exercise.lower()
    return any(kw in key for kw in RUN_KEYWORDS)


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

Analysiere die Bewegungssequenz in zwei Ebenen:
1. Ausführungsqualität — was siehst du konkret in den Frames?
2. Challenge — ist diese Übung und Dosierung für diesen Athleten gerade optimal?

Wenn die Frames nicht aussagekräftig sind (unscharf, falscher Winkel, Athlet außerhalb Bild, Beleuchtung):
Schreibe NUR: "❌ Video nicht auswertbar: [Grund]\n📹 Nächstes Mal: [was ändern]"
Keine Analyse durchführen wenn die Qualität nicht reicht."""

SYSTEM_PROMPT_RUN = """Du bist ein erfahrener Lauf-Biomechanik-Experte. Du analysierst Laufvideos auf Technikqualität und Verletzungsrisiko.

Die folgenden Bilder sind chronologisch geordnete Frames aus einem Laufvideo — sie zeigen einen oder mehrere Gangzyklen eines Athleten. Aktive Verletzungen, Reha-Phasen oder Restriktionen — sofern relevant — stehen im `Athlet-Kontext`-Feld der User-Message; gewichte deine Beobachtungen entsprechend.

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

Wenn die Frames nicht aussagekräftig sind (unscharf, Athlet zu weit weg, falscher Winkel, nur Rücken oder Füße sichtbar):
Schreibe NUR: "❌ Video nicht auswertbar: [Grund]\n📹 Nächstes Mal: [was ändern — Distanz, Winkel, Bildausschnitt]"
Keine Analyse wenn Qualität nicht reicht."""


# ─── Gemini via OpenRouter ───────────────────────────────────────────────────

VIDEO_SIZE_LIMIT_MB = 50  # Direkte Video-Analyse bis 50MB, sonst Frames


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

Antworte in diesem Format (maximal 8–10 Sätze):

**{exercise} — Lauf-Formcheck**

**Technik**
[2–3 konkrete Beobachtungen — nur was sichtbar ist, keine Spekulation]

**Priorität für nächste Session**
[1 konkreter Korrekturpunkt — präzise und umsetzbar, mit Drill-Empfehlung]

**Risiko-Check**
[Fußaufsatz: Dorsalflexion-Winkel, Aufprallposition relativ zum Körperschwerpunkt; weitere athleten-spezifische Risiko-Marker falls im Athlet-Kontext genannt]"""
    else:
        return f"""Übung: {exercise}
Kamerawinkel: {angle or get_angle_tip(exercise)}{checklist_block}{context_block}

Antworte in diesem Format (maximal 8–10 Sätze):

**{exercise} — Formcheck**

**Ausführung**
[2–3 konkrete Beobachtungen — keine Spekulation]

**Drill für nächste Session**
[1 konkreter Korrekturpunkt]

**Challenge**
[Ist diese Übung + Ansatz optimal? Wenn ja: "Passt so." Wenn nein: was wäre besser?]"""


def analyse_with_gemini_video(
    video_path: str,
    exercise: str,
    checklist: str,
    context: str,
    angle: str,
    model_key: str = DEFAULT_MODEL,
    run_mode: bool = False,
    section_label: str = "",
) -> str:
    """Direkte Video-Analyse via OpenRouter video_url (Gemini sieht das komplette Video)."""
    size_mb = Path(video_path).stat().st_size / (1024 * 1024)
    if size_mb > VIDEO_SIZE_LIMIT_MB:
        raise ValueError(f"Video zu groß für direkte Analyse ({size_mb:.1f}MB > {VIDEO_SIZE_LIMIT_MB}MB) — nutze Frames")

    print(f"  Direkte Video-Analyse ({size_mb:.1f}MB)...", file=sys.stderr)
    with open(video_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    client = _openrouter_client()
    model = MODELS.get(model_key, MODELS[DEFAULT_MODEL])
    print(f"  Modell: {model}", file=sys.stderr)

    system_prompt = SYSTEM_PROMPT_RUN if run_mode else SYSTEM_PROMPT
    user_text = _build_user_prompt(exercise, checklist, context, angle, run_mode)

    content: list = [
        {"type": "text", "text": user_text},
        {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{b64}"}},
    ]

    # Pro/thinking models need more tokens for reasoning + output
    max_tok = 4000 if model_key == "pro" else 1200

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
        if not response.choices:
            raise RuntimeError(f"Leere Antwort von {model} — kein choices-Array zurückgegeben")
        content_out = response.choices[0].message.content
        if not content_out:
            raise RuntimeError(f"Leere Antwort-Content von {model} — choices vorhanden aber leer")
        set_span_io(output=content_out)
    return content_out



# ─── Main ────────────────────────────────────────────────────────────────────

from app.utils.alerts import alert_on_failure
from app.utils.paths import CONFIG_DIR as _CONFIG_DIR

# exercise_log.md is athlete-specific (filled with each form check) → write
# always into CONFIG_DIR. If running with only config.example available,
# the file is created in CONFIG_DIR which may equal CONFIG_FALLBACK.
_EXERCISE_LOG = _CONFIG_DIR / "exercise_log.md"


def _update_exercise_log(exercise: str, video_filename: str, summary: str, date_str: str) -> None:
    """Update or append entry in config/exercise_log.md."""
    import logging
    _log = logging.getLogger(__name__)
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
    short_summary = escape_for_prompt(summary.strip().replace("\n", " "), max_len=200)

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
                        help=f"Modell: flash (default, günstig) oder pro (tiefere Analyse)")
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
    parser.add_argument("--no-log", action="store_true",
                        help="exercise_log.md nicht aktualisieren (Ad-hoc-Analyse)")
    args = parser.parse_args()

    if args.angle_only:
        print(f"📹 Kamera-Empfehlung für '{args.exercise}':")
        print(f"   {get_angle_tip(args.exercise)}")
        return

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


def _run_analysis(args: argparse.Namespace) -> None:

    # Trim video if requested
    if args.video and (args.trim_start > 0 or args.trim_end > 0):
        import av as _av, tempfile as _tmp
        with _av.open(args.video) as _c:
            _dur = float(_c.duration) / 1e6
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
        print("\nAnalysiere mit Gemini (Video)...", file=sys.stderr)
        try:
            feedback = analyse_with_gemini_video(
                args.video, args.exercise, checklist, args.context, args.angle,
                args.model, run_mode=True,
            )
        except ValueError as e:
            print(f"Fehler: {e}", file=sys.stderr)
            print("Video komprimieren oder in kürzere Clips aufteilen.", file=sys.stderr)
            sys.exit(1)
        print(feedback)
        if not args.no_log and args.video:
            _update_exercise_log(args.exercise, Path(args.video).name, feedback, date.today().isoformat())
        return

    # Kraft/Core/Ninja: Direkte Video-Analyse (kein lokales Frame-Decoding)
    print("\nAnalysiere mit Gemini (Video)...", file=sys.stderr)
    try:
        feedback = analyse_with_gemini_video(
            args.video, args.exercise, checklist, args.context, args.angle,
            args.model, run_mode=False,
        )
    except ValueError as e:
        print(f"Fehler: {e}", file=sys.stderr)
        print("Video komprimieren oder in kürzere Clips aufteilen.", file=sys.stderr)
        sys.exit(1)
    print(feedback)
    if not args.no_log and args.video:
        _update_exercise_log(args.exercise, Path(args.video).name, feedback, date.today().isoformat())


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


def _run_garmin_sections(args: argparse.Namespace, checklist: str) -> None:
    """Analysiert Garmin-definierte Sections als direkte Video-Clips."""
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
                )
                print(f"\n### {label}\n")
                print(feedback)
                print()
            except Exception as e:
                print(f"  Video-Analyse fehlgeschlagen ({e}) — Section {label} übersprungen", file=sys.stderr)


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
                )
                print(f"\n### {label}\n")
                print(feedback)
                print()
            except Exception as e:
                print(f"  Video-Analyse fehlgeschlagen ({e}) — {label} übersprungen", file=sys.stderr)


if __name__ == "__main__":
    main()
