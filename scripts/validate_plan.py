"""Mechanischer Plan-Validator — prüft geplante Workouts gegen Trainingsparadigmen.

Plugin-Architektur: jede Regel ist eine Funktion `check_<name>(workouts, ctx) -> list[Finding]`.
Neue Regeln einfach in `RULES` eintragen.

Input: JSON-Array (workouts mit description/intervals_icu) via --file oder stdin.
Output: JSON mit findings[].
Exit Code: 1 wenn ERROR-Finding vorhanden, sonst 0.

Usage:
    echo '[{...}]' | python3 scripts/validate_plan.py --date YYYY-MM-DD
    python3 scripts/validate_plan.py --date YYYY-MM-DD --file /tmp/workouts.json
    python3 scripts/validate_plan.py --date YYYY-MM-DD --file plan.json --json   # JSON-Output statt Klartext
    python3 scripts/validate_plan.py --date YYYY-MM-DD --file plan.json --rule R001   # einzelne Regel testen
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.intervals_client import IntervalsClient
from app.config import settings


SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"


@dataclass
class Finding:
    rule_id: str
    severity: str
    workout: str
    message: str
    suggestion: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Context:
    target_date: str
    athlete_static: str = ""
    athlete_status: str = ""
    training_paradigms: str = ""
    recent_notes: list[dict] = field(default_factory=list)
    recent_activities: list[dict] = field(default_factory=list)
    sport_settings: list[dict] = field(default_factory=list)


# ─────────────────────────── Helpers ───────────────────────────

# Übungen, bei denen >15 Reps EXPLIZIT erlaubt sind (Iso-Holds, Mobility, Plyo-Hops, Aktivierung).
HIGH_REP_WHITELIST = [
    r"\bpogo[-\s]?(hop|jump)",
    r"\bjumping jack",
    r"\bhampelmann",
    r"\bhigh knee", r"\bkniehub",
    r"\bbutt kick", r"\banfersen",
    r"\ba-?skip", r"\bb-?skip",
    r"\bbeinpendel", r"\bleg swing",
    r"\bschulterkreis", r"\barm-?pendel",
    r"\bhandgelenk", r"\bfingerstreck",
    r"\bcat-?cow",
    r"\bhip\s*flexor", r"\bhip\s*car",
    r"\bplank", r"\bhollow", r"\bside\s*plank",
    r"\bdead\s*hang",
    r"\bfarmer", r"\bbottom-?up", r"\bbottoms-?up",
    r"\btowel\s*(pinch|wrap)", r"\bgripmaster",
    r"\bwand-?slide", r"\bwall\s*slide",
    r"\bscapula",
    r"\bbalance\s*board",
    r"\beinbeinstand", r"\bsingle.?leg\s*stand",
    r"\bdehnung", r"\bstretch",
    r"\bfoam\s*roll",
    r"\bface\s*pull",  # Sonderfall: hier prüft R001 zusätzlich anhand der Reps
]

# Für Face Pulls + ähnliche Hypertrophie/Stabilitäts-Übungen wird trotz Whitelist auf >15 geprüft
HYPERTROPHY_REPS_CAP_OVERRIDES = [
    r"\bface\s*pull",
    r"\by-?raise", r"\bw-?raise", r"\bt-?raise",
    r"\baußenrotat", r"\bexternal\s*rotat",
    r"\bcurl\b", r"\bbizep", r"\btrizep",
    r"\bfly\b", r"\bbutterfly",
    r"\brear\s*delt",
    r"\b(latzug|lat-?pulldown|lat\s*pull-?down)",
    r"\brow\b", r"\brudern",
    r"\bsquat\b", r"\bkniebeug",
    r"\brdl\b", r"\bromanian\s*deadlift",
    r"\bhip\s*thrust", r"\bglute\s*bridge",
    r"\bstep-?up",
    r"\bovermlyhead\s*press", r"\bschulterpress",
    r"\bbench\s*press", r"\bbankdrück",
    r"\bdeadlift",
    r"\bpull-?up", r"\bklimmzug",
    r"\bdip\b",
    r"\bpush-?up", r"\bliegestütz",
]

# Schulter-Lock: dauerhaft gesperrt laut athlete_static.md
SHOULDER_LOCK_PATTERNS = [
    r"\bpull-?up", r"\bklimmzug",
    r"\brope\s*climb", r"\bseilklettern",
    r"\bbar\s*traverse",
    r"\bcampus\s*board",
    r"\bmuscle-?up",
]

# Schweres Push (Ausnahme: KB OHP 4kg = Reha)
HEAVY_OVERHEAD_PATTERNS = [
    r"\b(barbell|langhantel)\s*overhead",
    r"\bschulterpress\s*\d{2,}\s*kg",
    r"\bovermhead\s*press\s*\d{2,}\s*kg",
]

# Hard-Glute-Übungen (für DOMS-Check)
HARD_GLUTE_PATTERNS = [
    r"\brdl\b.*\d+\s*kg",
    r"\bromanian\s*deadlift",
    r"\bhip\s*thrust",
    r"\bdeadlift\s*\d+\s*kg",
    r"\bsquat\s*\d{2,}\s*kg",
]

# Plyo-Patterns
PLYO_PATTERNS = [
    r"\bpogo[-\s]?(hop|jump)",
    r"\bbox\s*jump",
    r"\bdrop\s*jump",
    r"\bsprung",
    r"\blateral\s*bound",
    r"\bdepth\s*jump",
]

# Übungs-Zeile: muss Mengenangabe enthalten (sonst Fließtext)
_QUANT_LINE = re.compile(r"\d+\s*[x×]\s*\d+|\d+\s*(?:s|sec|sek|min|m\b)", flags=re.IGNORECASE)

# Reps aus einer Übungs-Zeile extrahieren: "3×17" oder "3x17" → (sets=3, reps=17)
_SETS_REPS = re.compile(r"\b(\d+)\s*[x×]\s*(\d+)(?!\s*(?:s|sec|sek|min|m\b|kg))")


def _exercise_lines(description: str) -> list[str]:
    """Return strip()ed lines that look like exercise instructions."""
    if not description:
        return []
    out = []
    for line in description.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not _QUANT_LINE.search(stripped):
            continue
        # Section headers like "WARM-UP (5 min)" filtern
        if re.match(r"^(WARM-?UP|HAUPTTEIL|HAUPT-TEIL|COOL-?DOWN|AKTIVIERUNG|BLOCK\b|FINISHER\b|MAIN\b)", stripped, flags=re.IGNORECASE):
            continue
        out.append(stripped)
    return out


def _matches_any(line: str, patterns: list[str]) -> bool:
    return any(re.search(p, line, flags=re.IGNORECASE) for p in patterns)


def _workout_name(w: dict) -> str:
    return w.get("name") or "(unbenannt)"


def _description(w: dict) -> str:
    return (w.get("description") or w.get("intervals_icu") or "").strip()


# ─────────────────────────── Rules ───────────────────────────

def check_reps_ceiling(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R001 — Reps-Decke 15: Hypertrophie-/Strength-Übungen sollen max. 15 Reps haben.

    Ausnahme: Whitelist (Iso-Holds, Mobility, Plyo-Hops). Override: HYPERTROPHY_REPS_CAP_OVERRIDES
    kennen explizite Hypertrophie-Übungen, die TROTZ Whitelist-Match auf Reps geprüft werden
    (z.B. Face Pulls).

    Sport-Science-Anker: `framework/research/hypertrophy-rep-ranges.md`
    """
    findings = []
    for w in workouts:
        name = _workout_name(w)
        for line in _exercise_lines(_description(w)):
            for m in _SETS_REPS.finditer(line):
                reps = int(m.group(2))
                if reps <= 15:
                    continue
                is_override = _matches_any(line, HYPERTROPHY_REPS_CAP_OVERRIDES)
                is_whitelisted = _matches_any(line, HIGH_REP_WHITELIST)
                if is_whitelisted and not is_override:
                    continue
                findings.append(Finding(
                    rule_id="R001",
                    severity=SEVERITY_WARNING,
                    workout=name,
                    message=f"Reps {reps} > 15 — verlässt Hypertrophie-Zone. Zeile: «{line[:80]}»",
                    suggestion="Reps auf 12-15 senken und Last erhöhen (stärkeres Band/Gewicht) oder Tempo-Reiz (3-4s eccentric + Hold).",
                ))
    return findings


def check_injury_locks_shoulder(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R002 — Schulter-Sperre rechts: Pull-up, Hang, Rope Climb, Bar Traverse, Campus Board verboten.

    Ausnahme: Dead Hang aktiv 2-5s ist erlaubt (siehe athlete_static.md).
    Hard-Stop (ERROR) bei eindeutigen Verletzungs-Verstößen.
    """
    findings = []
    if "Schulter rechts" not in ctx.athlete_static and "Schultersteife" not in ctx.athlete_static:
        return findings  # keine aktive Schulter-Restriktion
    for w in workouts:
        name = _workout_name(w)
        for line in _exercise_lines(_description(w)):
            if _matches_any(line, SHOULDER_LOCK_PATTERNS):
                # Dead Hang 2-5s ist explizit erlaubt
                if re.search(r"dead\s*hang.*[2-5]\s*s", line, flags=re.IGNORECASE):
                    continue
                findings.append(Finding(
                    rule_id="R002",
                    severity=SEVERITY_ERROR,
                    workout=name,
                    message=f"Schulter-Sperre verletzt — gesperrte Übung: «{line[:80]}»",
                    suggestion="Übung ersetzen durch erlaubte Variante (TRX Row statt Pull-up, Face Pull statt Hang, etc.) oder weglassen.",
                ))
            if _matches_any(line, HEAVY_OVERHEAD_PATTERNS):
                findings.append(Finding(
                    rule_id="R002",
                    severity=SEVERITY_ERROR,
                    workout=name,
                    message=f"Schwerer Overhead Press trotz Schulter-Restriktion: «{line[:80]}»",
                    suggestion="Last reduzieren auf Reha-Niveau (KB OHP 4kg = OK) oder Übung weglassen.",
                ))
    return findings


def check_surface_required(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R003 — Run/Ride muss surface-Feld haben (Schuh-Advisor hängt davon ab)."""
    findings = []
    valid_surfaces = {"asphalt", "forstweg", "trail", "track", "treadmill"}
    for w in workouts:
        if w.get("type") not in ("Run", "Ride"):
            continue
        if w.get("indoor"):
            continue  # indoor = treadmill/turbo, kein surface nötig
        surface = w.get("surface")
        if not surface:
            findings.append(Finding(
                rule_id="R003",
                severity=SEVERITY_ERROR,
                workout=_workout_name(w),
                message="Run/Ride ohne surface-Feld — Schuh-Advisor kann nicht zuverlässig empfehlen.",
                suggestion=f"surface setzen: einer von {sorted(valid_surfaces)}",
            ))
        elif surface.lower() not in valid_surfaces:
            findings.append(Finding(
                rule_id="R003",
                severity=SEVERITY_WARNING,
                workout=_workout_name(w),
                message=f"surface='{surface}' nicht in Standard-Set — Schuh-Advisor rät heuristisch.",
                suggestion=f"Standardisieren: {sorted(valid_surfaces)}",
            ))
    return findings


def check_glute_doms(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R004 — Aktive Glute-DOMS-NOTE in letzten 3 Tagen + harte Glute-Übungen heute.

    Sport-Science-Anker: `framework/research/doms-peak-timing.md`
    """
    findings = []
    cutoff = (datetime.fromisoformat(ctx.target_date) - timedelta(days=3)).date()
    has_active_doms = False
    for note in ctx.recent_notes:
        note_date = note.get("start_date_local", "")[:10]
        try:
            nd = datetime.fromisoformat(note_date).date()
        except Exception:
            continue
        if nd < cutoff:
            continue
        desc = (note.get("description") or "").lower()
        if "glute" in desc and ("doms" in desc or "schmerz" in desc or "angeschlagen" in desc or "spürbar" in desc):
            # Nur "noch aktiv" wenn nicht ausdrücklich aufgehoben
            if "aufgehoben" in desc or "weg" in desc or "deutlich besser" in desc:
                continue
            has_active_doms = True
            break
    if not has_active_doms:
        return findings
    for w in workouts:
        for line in _exercise_lines(_description(w)):
            if _matches_any(line, HARD_GLUTE_PATTERNS):
                findings.append(Finding(
                    rule_id="R004",
                    severity=SEVERITY_WARNING,
                    workout=_workout_name(w),
                    message=f"Harte Glute-Übung trotz aktiver DOMS-NOTE (≤3d): «{line[:80]}»",
                    suggestion="Last deutlich reduzieren oder Übung streichen, bis Glute symptomfrei.",
                ))
    return findings


def check_achilles_plyo_surface(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R005 — Achilles Phase 3 + harte Plyo + Asphalt/Track → Hinweis auf weichen Untergrund.

    Sport-Science-Anker: `framework/research/achilles-rehab-phases.md`,
                         `framework/research/plyometrics-frequency-recovery.md`
    """
    findings = []
    if "Phase 3" not in ctx.athlete_static:
        return findings
    has_plyo = False
    plyo_workout = None
    for w in workouts:
        for line in _exercise_lines(_description(w)):
            if _matches_any(line, PLYO_PATTERNS):
                has_plyo = True
                plyo_workout = _workout_name(w)
                break
        if has_plyo:
            break
    if not has_plyo:
        return findings
    for w in workouts:
        if w.get("type") not in ("Run",):
            continue
        surface = (w.get("surface") or "").lower()
        if surface in ("asphalt", "track"):
            findings.append(Finding(
                rule_id="R005",
                severity=SEVERITY_INFO,
                workout=_workout_name(w),
                message=f"Plyo-Block ({plyo_workout}) + harte Surface ({surface}) am gleichen Tag bei Achilles Phase 3.",
                suggestion="Forstweg/Trail bevorzugen wenn möglich, oder Plyo auf einen anderen Tag legen.",
            ))
    return findings


def check_lthr_settings_drift(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R006 — Sport-Settings LTHR muss mit athlete_status.md übereinstimmen.

    Heutiger Lehrfall: intervals.icu Run-LTHR=154, status.md=166 → %lthr-Steps falsch.
    """
    findings = []
    # Erwartete LTHR aus athlete_status.md extrahieren
    m = re.search(r"LTHR\s*aktuell[:\*\s]*?(\d{2,3})\s*bpm", ctx.athlete_status)
    if not m:
        return findings
    expected_lthr = int(m.group(1))
    for s in ctx.sport_settings:
        types = s.get("types") or []
        if "Run" not in types:
            continue
        actual_lthr = s.get("lthr")
        if actual_lthr and actual_lthr != expected_lthr:
            findings.append(Finding(
                rule_id="R006",
                severity=SEVERITY_ERROR,
                workout="(global)",
                message=f"intervals.icu Run-LTHR ({actual_lthr}) ≠ athlete_status.md LTHR ({expected_lthr}) — %lthr-Steps + Load-Berechnung falsch.",
                suggestion=f"PUT /api/v1/athlete/{settings.intervals_icu_athlete_id or '<athlete-id>'}/sport-settings/{s.get('id')} mit lthr={expected_lthr}",
            ))
    return findings


def check_pillar_rotation(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R007 — Ninja-Säulen-Rotation: Pull+Push am gleichen Tag = WARNING (Säulen-Doppel)."""
    findings = []
    has_pull = False
    has_push = False
    pull_workout = ""
    push_workout = ""
    for w in workouts:
        if "ninja" not in (w.get("tags") or []):
            continue
        desc = _description(w).lower()
        # Pull-Indikatoren
        if any(re.search(p, desc, flags=re.IGNORECASE) for p in [r"\bpull-säule", r"\bpull\s*block", r"\btrx row", r"\bface\s*pull", r"\brudern\b"]):
            has_pull = True
            pull_workout = _workout_name(w)
        # Push-Indikatoren (außer Reha-OHP)
        if any(re.search(p, desc, flags=re.IGNORECASE) for p in [r"\bpush-?up", r"\bdip\b", r"\bbench\s*press", r"\bpush-säule", r"\bpush\s*block"]):
            has_push = True
            push_workout = _workout_name(w)
    if has_pull and has_push:
        findings.append(Finding(
            rule_id="R007",
            severity=SEVERITY_WARNING,
            workout=f"{pull_workout} + {push_workout}",
            message="Pull and Push pillar on the same day — pillar rotation violated.",
            suggestion="Move one pillar to a different day (check the pillar history in CLAUDE.md / planningConstraints).",
        ))
    return findings


def check_intervals_lthr_format(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R008 — Wenn Workout %lthr-Step verwendet, sicherstellen dass die Werte zur athleten-LTHR passen.

    Beispiel: Bei LTHR 166 ist '93-99% lthr' = 154-164 bpm. Wenn der Coach jedoch '90-95% lthr'
    schreibt aber Z4-Reiz (154-166) erwartet, ist das inkonsistent.
    """
    findings = []
    m = re.search(r"LTHR\s*aktuell[:\*\s]*?(\d{2,3})\s*bpm", ctx.athlete_status)
    if not m:
        return findings
    lthr = int(m.group(1))
    z4_lower = lthr * 0.93  # ~ untere Z4
    z4_upper = lthr  # = LTHR = obere Z4
    for w in workouts:
        intervals = w.get("intervals_icu") or ""
        for match in re.finditer(r"(\d+)-(\d+)\s*%\s*lthr", intervals, flags=re.IGNORECASE):
            lo_pct = int(match.group(1))
            hi_pct = int(match.group(2))
            lo_bpm = lthr * lo_pct / 100
            hi_bpm = lthr * hi_pct / 100
            # Erwartetes Z4: Cap soll <= LTHR sein, untere Grenze >= 0.93*LTHR
            if hi_bpm > lthr + 0.5:
                findings.append(Finding(
                    rule_id="R008",
                    severity=SEVERITY_WARNING,
                    workout=_workout_name(w),
                    message=f"%lthr-Cap ({hi_pct}%={hi_bpm:.0f}bpm) > LTHR ({lthr}bpm) — über Schwelle, unsicher für Wiederaufbau.",
                    suggestion="Cap auf 99-100% lthr begrenzen (Z4-Threshold-Reiz, nicht VO2max).",
                ))
            if lo_bpm < lthr * 0.85:
                findings.append(Finding(
                    rule_id="R008",
                    severity=SEVERITY_INFO,
                    workout=_workout_name(w),
                    message=f"%lthr-Range startet bei {lo_pct}% ({lo_bpm:.0f}bpm) — unterhalb Z3, unsauber für Z4-Reiz.",
                    suggestion="Untere Range >= 92% LTHR setzen für saubere Z4-Reiz-Range.",
                ))
    return findings


def check_hr_range_consistency(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R009 — HR-Range-Konsistenz zwischen Description und intervals_icu-Code.

    Wenn die Description eine BPM-Range nennt (z.B. 'HR 120-130' oder '120-130 bpm'),
    muss der intervals_icu-Code diese BPM-Range explizit setzen — nicht 'Z<n> HR' verwenden.
    'Z<n> HR' pusht im Garmin-Sync die volle Zone, was bei zonen-übergreifenden Ranges
    (z.B. Z1-oben + Z2-unten = 120-130) oder Teil-Range einer Zone zur falschen
    Vorgabe führt. Athlet sieht im Garmin den Sync-Code, nicht die Description.

    Beispiel-Bug 2026-05-08: Description 'HR 120-130', intervals_icu '50m Z1 HR' →
    Athlet bekommt Z1-Range (1-125) statt 120-130 angezeigt.
    """
    findings = []
    bpm_pattern = re.compile(
        r"\bHR\s*(\d{2,3})[-–](\d{2,3})\b|\b(\d{2,3})[-–](\d{2,3})\s*bpm\b",
        flags=re.IGNORECASE,
    )
    zone_only_pattern = re.compile(r"\bZ\d+\s*HR\b", flags=re.IGNORECASE)
    for w in workouts:
        if (w.get("type") or "").lower() not in ("run", "ride"):
            continue
        desc = _description(w)
        intervals = w.get("intervals_icu") or ""
        if not intervals:
            continue
        # Hat Description eine BPM-Range, die NICHT auch im intervals_icu-Code als BPM steht?
        desc_bpm_matches = list(bpm_pattern.finditer(desc))
        if not desc_bpm_matches:
            continue
        intervals_bpm_matches = list(bpm_pattern.finditer(intervals))
        zone_only_matches = list(zone_only_pattern.finditer(intervals))
        # Wenn intervals_icu "Z<n> HR" enthält UND keine BPM-Range explizit nennt
        if zone_only_matches and not intervals_bpm_matches:
            # Range aus Description extrahieren für Hinweis-Text
            for m in desc_bpm_matches:
                lo = m.group(1) or m.group(3)
                hi = m.group(2) or m.group(4)
                findings.append(Finding(
                    rule_id="R009",
                    severity=SEVERITY_WARNING,
                    workout=_workout_name(w),
                    message=(
                        f"Description nennt HR-Range {lo}-{hi}, intervals_icu-Code "
                        f"verwendet aber '{zone_only_matches[0].group(0)}'. Athlet sieht "
                        f"im Garmin die ganze Zone, nicht die spezifische BPM-Range."
                    ),
                    suggestion=(
                        f"Im intervals_icu-Code 'Z<n> HR' ersetzen durch "
                        f"explizite BPM-Range, z.B. 'XXm HR {lo}-{hi}' "
                        f"(siehe memory feedback_hr_range_intervals_icu.md)."
                    ),
                ))
                break  # ein Treffer pro Workout reicht
    return findings


def check_easy_hr_ceiling(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R010 — Easy/Recovery-Lauf darf HR-Decke nicht in Z3 hochlaufen.

    Bei workout_type EASY oder RECOVERY (Reha-Lauf) prüft die Regel, ob die im
    intervals_icu-Code oder Description gesetzte HR-Obergrenze die Z2-Obergrenze
    aus athlete_status.md überschreitet. Z3-Bereich = Tempo/Schwelle, gehört nicht
    in Recovery-Workouts.

    Beispiel-Bug 2026-05-11: Reha-Lauf mit HR 110-145 — 145 lag in Z3-Mitte
    (Z2-Obergrenze 139). Athlet hat es selbst korrigiert; Validator hatte
    keine Regel dafür.

    Sport-Science-Anker: `framework/research/polarized-training-seiler.md`
    """
    findings = []
    # Z2-Obergrenze aus athlete_status.md extrahieren — Format:
    # "Z1 1–125 | Z2 126–139 | Z3 140–153 | ..."
    m = re.search(
        r"Z1[^|]*?(\d{2,3})\s*\|\s*Z2[^|]*?\d{2,3}\s*[-–—]\s*(\d{2,3})",
        ctx.athlete_status,
    )
    if not m:
        return findings
    z2_upper = int(m.group(2))
    bpm_range_pattern = re.compile(r"\b(\d{2,3})\s*[-–—]\s*(\d{2,3})\s*bpm\b", flags=re.IGNORECASE)
    for w in workouts:
        if (w.get("type") or "").lower() != "run":
            continue
        wt = (w.get("workout_type") or "").upper()
        if wt not in ("EASY", "RECOVERY"):
            continue
        # In intervals_icu-Code UND Description nach BPM-Ranges suchen
        sources = [
            ("intervals_icu", w.get("intervals_icu") or ""),
            ("description", _description(w)),
        ]
        for source_name, text in sources:
            for match in bpm_range_pattern.finditer(text):
                lo = int(match.group(1))
                hi = int(match.group(2))
                if hi > z2_upper:
                    findings.append(Finding(
                        rule_id="R010",
                        severity=SEVERITY_ERROR,
                        workout=_workout_name(w),
                        message=(
                            f"{wt}-Lauf hat HR-Decke {hi} bpm im {source_name} — "
                            f"das überschreitet die Z2-Obergrenze ({z2_upper} bpm) "
                            f"und läuft in Z3 (Tempo). Easy/Recovery-Workouts dürfen "
                            f"nie in Z3+ hochziehen."
                        ),
                        suggestion=(
                            f"HR-Decke auf max. {z2_upper} bpm setzen — "
                            f"bei Recovery-/Reha-Charakter eher 5-10 bpm Puffer drunter "
                            f"(siehe memory feedback_easy_run_hr_ceiling.md)."
                        ),
                    ))
                    break  # ein Treffer pro Source reicht
    return findings


def check_intervals_duration_sanity(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R011 — intervals_icu computed total muss zu duration_min passen.

    Beispiel-Bug 2026-05-12: `Steigerungen 4x 100m` in intervals_icu wurde von
    intervals.icu als 4 × 100 Minuten interpretiert (statt 4 × 100m Distanz),
    resultierende moving_time 9450s (157 min) für ein als 65 min geplantes
    Threshold-Workout. Athlet musste manuell nachfragen.

    Diese Regel parst intervals_icu mit derselben Heuristik (Loop-Header `Nx`,
    Step-Lines mit Xm/Xs) und vergleicht mit workout.duration_min. Abweichung
    >50% → ERROR (sicher ein Format-Bug), >25% → WARNING (vermutlich press-lap
    oder unparseable Steps, aber lohnt Review).

    Lint-Regel im Linter blockt ohnehin schon `Distanz statt Zeit`-Format
    (z.B. `100m`), aber R011 fängt auch andere Parser-Diskrepanzen.
    """
    from app.utils.intervals_icu_linter import compute_intervals_total_seconds

    findings = []
    for w in workouts:
        icu = w.get("intervals_icu") or ""
        if not icu.strip():
            continue
        duration_min = w.get("duration_min")
        if not duration_min or duration_min <= 0:
            continue
        planned_s = int(duration_min) * 60
        computed_s = compute_intervals_total_seconds(icu)
        if computed_s == 0:
            # No parseable durations — can't compare. Skip silently.
            continue
        # press-lap Steps haben keine Duration → niedrige computed_s ist OK,
        # nur Abweichung NACH OBEN (>50%) ist sicher Bug.
        ratio = computed_s / planned_s
        if ratio > 1.5:
            findings.append(Finding(
                rule_id="R011",
                severity=SEVERITY_ERROR,
                workout=_workout_name(w),
                message=(
                    f"intervals_icu computed total {computed_s}s ({computed_s//60} min) "
                    f"ist >{(ratio-1)*100:.0f}% über geplanter duration_min {duration_min} min. "
                    f"Vermutlich Format-Bug (z.B. `100m` als Minuten statt Distanz, oder "
                    f"falscher Loop-Multiplier)."
                ),
                suggestion=(
                    "intervals_icu-Steps prüfen: Strides als `- Xs` (Sekunden) notieren, "
                    "keine Distanz-Notation (`100m`, `200m`) — intervals.icu interpretiert "
                    "`m` als Minuten. Distanz nur in Description-Klartext, nicht im "
                    "intervals_icu-Code."
                ),
            ))
        elif ratio > 1.25:
            findings.append(Finding(
                rule_id="R011",
                severity=SEVERITY_WARNING,
                workout=_workout_name(w),
                message=(
                    f"intervals_icu computed total {computed_s}s ({computed_s//60} min) "
                    f"weicht +{(ratio-1)*100:.0f}% von duration_min {duration_min} min ab — "
                    f"Review empfohlen."
                ),
                suggestion="Steps und Loop-Multiplier kontrollieren.",
            ))
    return findings


def check_intervals_step_targets(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R012 — intervals_icu-Steps müssen jeweils ein valides Target tragen.

    Zwei Vorfall-Klassen, die diese Regel verhindert:

    (A) **Silent-Drop bei arbiträren BPM-Ranges (alle Typen, ERROR).**
        intervals.icu unterstützt keine `XX-YYbpm`-Syntax — der Step wird
        zwar angelegt, aber das Target-Suffix wird ignoriert und der Step
        landet ohne HR-Anker im `workout_doc`. Athlet bekommt auf der Watch
        keine HF-Anzeige. → Erlaubte HR-Tokens: `Zn HR`, `Zn-Zm HR`,
        `XX% LTHR`, `XX-YY% LTHR`, `XX% HR`, `XX-YY% HR`.

    (B) **Wahoo 422 für Ride-Steps ohne Target (Ride only, ERROR).**
        Wahoo-Plan-Upload validiert strenger als intervals.icu und failt mit
        `"each interval that is not of type 'repeat' must have a valid
        'targets' array"` wenn ein Ride-Step nur Cadence (`110rpm`) oder
        gar nichts trägt. Spin-ups, Cool-downs und Locker-Pause-Steps müssen
        IMMER ein Power-/HR-Target haben.

    Run-Drills (Hip-Flexor, A-Skips, Beinpendel etc.) sind absichtlich
    target-frei — werden als Cue-Steps interpretiert. Daher gilt für Run:
    nur Main-Set-Steps (Duration ≥ 3 min) ohne Target → WARNING.

    Beide Vorfall-Klassen aus realer Anwendung dokumentiert, Details
    siehe `framework/research/intervals-icu-workout-syntax.md`.
    """
    import re

    # Tokens, die als „echtes" Target gelten
    TARGET_PATTERNS = [
        r"\d+(?:-\d+)?w\b",                  # 220w, 200-240w
        r"\d+(?:-\d+)?%\s*(?:ftp|map|mmp|lthr|hr|pace)?\b",  # 75%, 95-105% LTHR
        r"\bZ\d(?:-Z\d)?(?:\s+(?:HR|Pace))?\b",  # Z2, Z2-Z3, Z2 HR
        r"\d+:\d+/(?:km|100m)\s*Pace",       # 5:00/km Pace
        r"\bramp\s+\d+",                     # ramp 50%-75%
        r"\bfreeride\b",
    ]
    BAD_BPM_RE = re.compile(r"\b\d+(?:-\d+)?\s*bpm\b", re.IGNORECASE)
    LAP_PRESS_RE = re.compile(r"\bpress\s+lap\b", re.IGNORECASE)
    LOOP_HEADER_RE = re.compile(r"\b\d+x\b", re.IGNORECASE)
    # Duration parsers
    DURATION_MIN_RE = re.compile(r"\b(\d+)m\b", re.IGNORECASE)
    DURATION_SEC_RE = re.compile(r"\b(\d+)s\b", re.IGNORECASE)

    def _step_duration_seconds(text: str) -> int:
        secs = 0
        m = DURATION_MIN_RE.search(text)
        if m:
            secs += int(m.group(1)) * 60
        s = DURATION_SEC_RE.search(text)
        if s:
            secs += int(s.group(1))
        return secs

    findings = []
    for w in workouts:
        icu = w.get("intervals_icu") or ""
        if not icu.strip():
            continue
        wtype = (w.get("type") or "").strip()
        is_ride = wtype in {"Ride", "VirtualRide"}

        for raw_line in icu.split("\n"):
            line = raw_line.strip()
            if not line or not line.startswith("-"):
                continue
            content = line.lstrip("-").strip()

            # Bad-BPM-Range first — produces silent drop on ALL types
            if BAD_BPM_RE.search(content):
                findings.append(Finding(
                    rule_id="R012",
                    severity=SEVERITY_ERROR,
                    workout=_workout_name(w),
                    message=(
                        f"intervals_icu-Step `{content[:80]}` verwendet "
                        f"arbiträre BPM-Range — intervals.icu droppt das "
                        f"Suffix silent, Step landet ohne HF-Target."
                    ),
                    suggestion=(
                        "HR-Targets als `Zn HR`, `XX-YY% LTHR` oder "
                        "`XX-YY% HR` schreiben. Beispiel-Umrechnung bei "
                        "LTHR 166: 126-135 bpm = 76-81% LTHR."
                    ),
                ))
                continue

            # Skip until-lap-press steps (no target needed)
            if LAP_PRESS_RE.search(content):
                continue

            # Skip loop headers without their own duration
            if LOOP_HEADER_RE.search(content) and not re.search(r"\d+[ms]\b", content.lower()):
                continue

            has_target = any(re.search(p, content, re.IGNORECASE) for p in TARGET_PATTERNS)
            if has_target:
                continue

            # Step has duration but no target — flag based on workout type
            if is_ride:
                # Ride: Wahoo strict — every non-repeat step needs target
                findings.append(Finding(
                    rule_id="R012",
                    severity=SEVERITY_ERROR,
                    workout=_workout_name(w),
                    message=(
                        f"intervals_icu-Step `{content[:80]}` (Ride) hat kein "
                        f"Target (kein Watt, keine HR-Zone, kein %-Anker). "
                        f"Wahoo-Plan-Upload schlägt mit 422 fehl."
                    ),
                    suggestion=(
                        "Ride-Steps brauchen IMMER ein Target (auch Spin-ups, "
                        "Locker-Pausen, Cool-downs). Beispiele: Spin-up → "
                        "`15s 240W 110rpm`; Locker-Pause → `60s 150W`; "
                        "Cool-down → `6m 130W 85rpm`."
                    ),
                ))
            else:
                # Run/other: drills (< 3 min) ohne Target sind OK,
                # längere Main-Set-Steps ohne Target → WARNING
                dur_s = _step_duration_seconds(content)
                if dur_s >= 180:
                    findings.append(Finding(
                        rule_id="R012",
                        severity=SEVERITY_WARNING,
                        workout=_workout_name(w),
                        message=(
                            f"intervals_icu-Step `{content[:80]}` (Run) "
                            f"hat {dur_s//60} min Duration, aber kein Target "
                            f"— vermutlich Main-Set ohne HF-/Pace-Anker."
                        ),
                        suggestion=(
                            "Run-Drills < 3 min ohne Target sind OK (Cue-Steps). "
                            "Aber Main-Set / längere Steps brauchen Target: "
                            "`Z2 HR`, `85-90% LTHR`, oder `5:00/km Pace`."
                        ),
                    ))
    return findings


def check_intervals_repeat_block_adjacency(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R013 — Repeat-Block-Header (`Nx`) und seine `-`-Items müssen adjazent stehen.

    intervals.icu's Server-Parser erkennt einen Repeat-Block nur, wenn der
    Header (`Strides 5x`, `Set1 8x`, `Main Set 5x`) und seine Item-Zeilen
    durch einfache Newlines (`\\n`) getrennt sind — KEINE Leerzeile.

    Vorfalls-Muster aus realer Anwendung: Strides-Block mit Leerzeile
    zwischen `Strides 5x` und den `- Stride ...`-Items wurde als `reps=1`
    statt `reps=5` geparst. Athlet bekam auf der Watch nur 1 Stride statt
    5. Stille Drift, kein Server-Error. Details:
    `framework/research/intervals-icu-workout-syntax.md` (Falle C-bis).
    """
    import re

    REPEAT_HEADER_RE = re.compile(r"^\s*(?:[A-Za-zÄÖÜäöüß0-9 _\-]+\s+)?\d+x\s*$", re.IGNORECASE)
    findings = []
    for w in workouts:
        icu = w.get("intervals_icu") or ""
        if not icu.strip():
            continue
        lines = icu.split("\n")
        for idx, raw in enumerate(lines):
            line = raw.rstrip()
            if not REPEAT_HEADER_RE.match(line):
                continue
            # Header found — look at the next non-blank line. If there is a blank
            # line between header and the first `-` item, the parser will drop
            # the repeat semantics.
            next_idx = idx + 1
            if next_idx >= len(lines):
                continue
            if lines[next_idx].strip() == "":
                # Blank line right after header — check if a `-` item follows
                later_idx = next_idx + 1
                while later_idx < len(lines) and lines[later_idx].strip() == "":
                    later_idx += 1
                if later_idx < len(lines) and lines[later_idx].strip().startswith("-"):
                    findings.append(Finding(
                        rule_id="R013",
                        severity=SEVERITY_ERROR,
                        workout=_workout_name(w),
                        message=(
                            f"Repeat-Block-Header `{line.strip()}` hat eine "
                            f"Leerzeile vor den `-`-Items — intervals.icu "
                            f"droppt dann die Wiederholung silent (reps=1 "
                            f"statt N)."
                        ),
                        suggestion=(
                            f"Leerzeile zwischen `{line.strip()}` und dem "
                            f"ersten `-`-Item entfernen. Header und Items "
                            f"adjazent (nur `\\n`), Leerzeile (`\\n\\n`) NUR "
                            f"zwischen verschiedenen Blöcken."
                        ),
                    ))
    return findings


# Plugin-Registry: neue Regeln hier eintragen.
RULES: list[Callable[[list[dict], Context], list[Finding]]] = [
    check_reps_ceiling,
    check_injury_locks_shoulder,
    check_surface_required,
    check_glute_doms,
    check_achilles_plyo_surface,
    check_lthr_settings_drift,
    check_pillar_rotation,
    check_intervals_lthr_format,
    check_hr_range_consistency,
    check_easy_hr_ceiling,
    check_intervals_duration_sanity,
    check_intervals_step_targets,
    check_intervals_repeat_block_adjacency,
]


# ─────────────────────────── Context Loader ───────────────────────────

def _read_config(path: str) -> str:
    from app.utils.paths import resolve_config
    try:
        return resolve_config(path).read_text()
    except FileNotFoundError:
        return ""


async def _fetch_recent_notes(target_date: str, days_back: int = 7) -> list[dict]:
    """Fetch NOTE-events from intervals.icu für Glute-DOMS / Athleten-Feedback-Check."""
    client = IntervalsClient(settings.intervals_icu_athlete_id)
    end = datetime.fromisoformat(target_date).date()
    start = end - timedelta(days=days_back)
    events = await client.get_events(start.isoformat(), end.isoformat())
    return [e for e in events if e.get("category") == "NOTE"]


async def _fetch_sport_settings() -> list[dict]:
    """Fetch sport-settings from intervals.icu — used by R006."""
    import httpx
    aid = settings.intervals_icu_athlete_id
    api_key = settings.intervals_icu_api_key
    async with httpx.AsyncClient(auth=("API_KEY", api_key)) as ac:
        r = await ac.get(f"https://intervals.icu/api/v1/athlete/{aid}/sport-settings")
        if r.status_code != 200:
            return []
        return r.json() or []


def load_context(target_date: str, fetch_remote: bool = True) -> Context:
    ctx = Context(
        target_date=target_date,
        athlete_static=_read_config("athlete_static.md"),
        athlete_status=_read_config("athlete_status.md"),
        training_paradigms=_read_config("training_paradigms.md"),
    )
    if fetch_remote:
        try:
            ctx.recent_notes = asyncio.run(_fetch_recent_notes(target_date))
        except Exception:
            ctx.recent_notes = []
        try:
            ctx.sport_settings = asyncio.run(_fetch_sport_settings())
        except Exception:
            ctx.sport_settings = []
    return ctx


# ─────────────────────────── Main ───────────────────────────

def run_validation(workouts: list[dict], ctx: Context, only_rule: str = "") -> list[Finding]:
    findings = []
    for rule in RULES:
        if only_rule:
            # Match by rule_id token in docstring (e.g. "R001")
            doc = (rule.__doc__ or "")
            if only_rule not in doc:
                continue
        try:
            findings.extend(rule(workouts, ctx))
        except Exception as exc:  # noqa: BLE001
            findings.append(Finding(
                rule_id="VALIDATOR",
                severity=SEVERITY_WARNING,
                workout="(global)",
                message=f"Regel {rule.__name__} crashed: {exc}",
            ))
    return findings


def format_findings_text(findings: list[Finding]) -> str:
    if not findings:
        return "✅ Keine Findings — Plan ist sauber."
    by_severity = {SEVERITY_ERROR: [], SEVERITY_WARNING: [], SEVERITY_INFO: []}
    for f in findings:
        by_severity.setdefault(f.severity, []).append(f)
    lines = []
    for sev, label in [(SEVERITY_ERROR, "🛑 ERROR"), (SEVERITY_WARNING, "⚠️ WARNING"), (SEVERITY_INFO, "ℹ️ INFO")]:
        items = by_severity.get(sev) or []
        if not items:
            continue
        lines.append(f"\n{label} ({len(items)}):")
        for f in items:
            lines.append(f"  [{f.rule_id}] {f.workout}: {f.message}")
            if f.suggestion:
                lines.append(f"    → {f.suggestion}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate workout plan against training paradigms")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--file", help="Path to JSON file with workouts array")
    parser.add_argument("--json", action="store_true", help="JSON-Output statt Klartext")
    parser.add_argument("--rule", default="", help="Nur eine Regel ausführen (z.B. R001)")
    parser.add_argument("--no-remote", action="store_true", help="Skip intervals.icu fetches (offline mode)")
    parser.add_argument("--warnings-ok", action="store_true", help="Exit 0 even if WARNINGs (only ERRORs block)")
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            workouts = json.load(f)
    else:
        workouts = json.load(sys.stdin)

    if isinstance(workouts, dict):
        workouts = workouts.get("workouts") or []
    if not isinstance(workouts, list):
        workouts = [workouts]

    ctx = load_context(args.date, fetch_remote=not args.no_remote)
    findings = run_validation(workouts, ctx, only_rule=args.rule)

    if args.json:
        print(json.dumps({
            "date": args.date,
            "workout_count": len(workouts),
            "findings": [f.to_dict() for f in findings],
        }, ensure_ascii=False, indent=2))
    else:
        print(format_findings_text(findings))

    has_error = any(f.severity == SEVERITY_ERROR for f in findings)
    if has_error:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
