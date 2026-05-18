"""Mechanical plan validator — checks planned workouts against training paradigms.

Plugin architecture: each rule is a function `check_<name>(workouts, ctx) -> list[Finding]`.
Register new rules in `RULES`.

Input: JSON array (workouts with description/intervals_icu) via --file or stdin.
Output: JSON with findings[].
Exit code: 1 if ERROR finding present, else 0.

Usage:
    echo '[{...}]' | python3 scripts/validate_plan.py --date YYYY-MM-DD
    python3 scripts/validate_plan.py --date YYYY-MM-DD --file /tmp/workouts.json
    python3 scripts/validate_plan.py --date YYYY-MM-DD --file plan.json --json   # JSON output instead of plain text
    python3 scripts/validate_plan.py --date YYYY-MM-DD --file plan.json --rule R001   # run a single rule
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
    injury_locks: dict[str, list[str]] = field(default_factory=dict)


# ─────────────────────────── Helpers ───────────────────────────

# Exercises where >15 reps are explicitly allowed (iso-holds, mobility, plyo-hops, activation).
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
    r"\bface\s*pull",  # special case: R001 additionally checks reps for these
]

# For Face Pulls + similar hypertrophy/stability exercises: check >15 reps despite whitelist match
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

# Shoulder lock: exercises blocked when shoulder restriction is active (per athlete_static.md + injury_locks.json)
SHOULDER_LOCK_PATTERNS = [
    r"\bpull-?up", r"\bklimmzug",
    r"\brope\s*climb", r"\bseilklettern",
    r"\bbar\s*traverse",
    r"\bcampus\s*board",
    r"\bmuscle-?up",
]

# Heavy overhead push (exception: KB OHP 4kg = rehab)
HEAVY_OVERHEAD_PATTERNS = [
    r"\b(barbell|langhantel)\s*overhead",
    r"\bschulterpress\s*\d{2,}\s*kg",
    r"\bovermhead\s*press\s*\d{2,}\s*kg",
]

# Hard glute exercises (for DOMS check)
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

# Exercise line: must contain quantity (otherwise prose text)
_QUANT_LINE = re.compile(r"\d+\s*[x×]\s*\d+|\d+\s*(?:s|sec|sek|min|m\b)", flags=re.IGNORECASE)

# Extract reps from an exercise line: "3×17" or "3x17" → (sets=3, reps=17)
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
        # Filter section headers like "WARM-UP (5 min)"
        if re.match(r"^(WARM-?UP|HAUPTTEIL|HAUPT-TEIL|COOL-?DOWN|AKTIVIERUNG|BLOCK\b|FINISHER\b|MAIN\b)", stripped, flags=re.IGNORECASE):
            continue
        out.append(stripped)
    return out


def _matches_any(line: str, patterns: list[str]) -> bool:
    return any(re.search(p, line, flags=re.IGNORECASE) for p in patterns)


def _workout_name(w: dict) -> str:
    return w.get("name") or "(unnamed)"


def _description(w: dict) -> str:
    return (w.get("description") or w.get("intervals_icu") or "").strip()


# ─────────────────────────── Rules ───────────────────────────

def check_reps_ceiling(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R001 — Reps ceiling 15: hypertrophy/strength exercises should have max 15 reps.

    Exception: whitelist (iso-holds, mobility, plyo-hops). Override: HYPERTROPHY_REPS_CAP_OVERRIDES
    lists explicit hypertrophy exercises that are checked for >15 reps DESPITE whitelist match
    (e.g. Face Pulls).

    Sport-science anchor: `framework/research/hypertrophy-rep-ranges.md`
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
                    message=f"Reps {reps} > 15 — leaves hypertrophy zone. Line: «{line[:80]}»",
                    suggestion="Reduce reps to 12-15 and increase load (heavier band/weight) or add tempo stimulus (3-4s eccentric + hold).",
                ))
    return findings


def check_injury_locks_shoulder(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R002 — Shoulder lock: Pull-up, Hang, Rope Climb, Bar Traverse, Campus Board prohibited.

    Activation: `config/injury_locks.json` defines keywords per lock zone. When any
    keyword is found in `athlete_static.md`, the corresponding lock is active.

    Exceptions:
    - Dead Hang 2-5s is explicitly allowed (see athlete_static.md).
    - Scapular Pullups (scapular depression, no elbow flexion) are rehab-tier
      and belong to the shoulder rehab repertoire — not a prohibited pull-up.
    Hard stop (ERROR) on clear injury violations.
    """
    findings = []
    shoulder_keywords = ctx.injury_locks.get("shoulder", [])
    if not shoulder_keywords:
        return findings
    static_lower = ctx.athlete_static.lower()
    if not any(kw.lower() in static_lower for kw in shoulder_keywords):
        return findings
    for w in workouts:
        name = _workout_name(w)
        for line in _exercise_lines(_description(w)):
            if _matches_any(line, SHOULDER_LOCK_PATTERNS):
                if re.search(r"dead\s*hang.*[2-5]\s*s", line, flags=re.IGNORECASE):
                    continue
                if re.search(r"\b(scapular?|skapula(r|re|ren)?)\s*pull[-\s]?ups?", line, flags=re.IGNORECASE):
                    continue
                findings.append(Finding(
                    rule_id="R002",
                    severity=SEVERITY_ERROR,
                    workout=name,
                    message=f"Shoulder lock violated — blocked exercise: «{line[:80]}»",
                    suggestion="Replace with allowed variant (TRX Row instead of Pull-up, Face Pull instead of Hang, etc.) or remove.",
                ))
            if _matches_any(line, HEAVY_OVERHEAD_PATTERNS):
                findings.append(Finding(
                    rule_id="R002",
                    severity=SEVERITY_ERROR,
                    workout=name,
                    message=f"Heavy overhead press despite shoulder restriction: «{line[:80]}»",
                    suggestion="Reduce load to rehab level (KB OHP 4kg = OK) or remove exercise.",
                ))
    return findings


def check_surface_required(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R003 — Run/Ride must have a surface field (shoe advisor depends on it)."""
    findings = []
    valid_surfaces = {"asphalt", "forstweg", "trail", "track", "treadmill"}
    for w in workouts:
        if w.get("type") not in ("Run", "Ride"):
            continue
        if w.get("indoor"):
            continue  # indoor = treadmill/turbo, no surface needed
        surface = w.get("surface")
        if not surface:
            findings.append(Finding(
                rule_id="R003",
                severity=SEVERITY_ERROR,
                workout=_workout_name(w),
                message="Run/Ride missing surface field — shoe advisor cannot reliably recommend.",
                suggestion=f"Set surface: one of {sorted(valid_surfaces)}",
            ))
        elif surface.lower() not in valid_surfaces:
            findings.append(Finding(
                rule_id="R003",
                severity=SEVERITY_WARNING,
                workout=_workout_name(w),
                message=f"surface='{surface}' not in standard set — shoe advisor uses heuristic.",
                suggestion=f"Standardize: {sorted(valid_surfaces)}",
            ))
    return findings


def check_glute_doms(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R004 — Active glute DOMS note in the last 3 days + hard glute exercises today.

    Sport-science anchor: `framework/research/doms-peak-timing.md`
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
            # Only "still active" if not explicitly resolved
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
                    message=f"Hard glute exercise despite active DOMS note (≤3d): «{line[:80]}»",
                    suggestion="Significantly reduce load or remove exercise until glute is symptom-free.",
                ))
    return findings


def check_achilles_plyo_surface(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R005 — Achilles Phase 3 + hard plyo + asphalt/track → suggest softer surface.

    Sport-science anchor: `framework/research/achilles-rehab-phases.md`,
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
                message=f"Plyo block ({plyo_workout}) + hard surface ({surface}) on the same day during Achilles Phase 3.",
                suggestion="Prefer forest path/trail if possible, or move plyo to a different day.",
            ))
    return findings


def check_lthr_settings_drift(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R006 — Sport-settings LTHR must match athlete_status.md.

    Historical finding: intervals.icu Run-LTHR diverged from status.md → %lthr steps wrong.
    """
    findings = []
    # Extract expected LTHR from athlete_status.md (supports both German "aktuell" and English "current")
    m = re.search(r"LTHR\s*(?:aktuell|current)[:\*\s]*?(\d{2,3})\s*bpm", ctx.athlete_status)
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
                message=f"intervals.icu Run-LTHR ({actual_lthr}) ≠ athlete_status.md LTHR ({expected_lthr}) — %lthr steps + load calculation wrong.",
                suggestion=f"PUT /api/v1/athlete/{settings.intervals_icu_athlete_id or '<athlete-id>'}/sport-settings/{s.get('id')} with lthr={expected_lthr}",
            ))
    return findings


def check_pillar_rotation(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R007 — Ninja pillar rotation: Pull+Push on the same day = WARNING (pillar double)."""
    findings = []
    has_pull = False
    has_push = False
    pull_workout = ""
    push_workout = ""
    for w in workouts:
        if "ninja" not in (w.get("tags") or []):
            continue
        desc = _description(w).lower()
        # Pull indicators
        if any(re.search(p, desc, flags=re.IGNORECASE) for p in [r"\bpull-säule", r"\bpull\s*block", r"\btrx row", r"\bface\s*pull", r"\brudern\b"]):
            has_pull = True
            pull_workout = _workout_name(w)
        # Push indicators (excluding rehab OHP)
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
    """R008 — When a workout uses %lthr steps, verify values match the athlete's LTHR.

    Example: with LTHR 166, '93-99% lthr' = 154-164 bpm. If the coach writes '90-95% lthr'
    but expects Z4 stimulus (154-166), that is inconsistent.
    """
    findings = []
    m = re.search(r"LTHR\s*(?:aktuell|current)[:\*\s]*?(\d{2,3})\s*bpm", ctx.athlete_status)
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
            # Expected Z4: cap should be <= LTHR, lower bound >= 0.93*LTHR
            if hi_bpm > lthr + 0.5:
                findings.append(Finding(
                    rule_id="R008",
                    severity=SEVERITY_WARNING,
                    workout=_workout_name(w),
                    message=f"%lthr cap ({hi_pct}%={hi_bpm:.0f}bpm) > LTHR ({lthr}bpm) — above threshold, risky for build-up.",
                    suggestion="Cap at 99-100% lthr (Z4 threshold stimulus, not VO2max).",
                ))
            if lo_bpm < lthr * 0.85:
                findings.append(Finding(
                    rule_id="R008",
                    severity=SEVERITY_INFO,
                    workout=_workout_name(w),
                    message=f"%lthr range starts at {lo_pct}% ({lo_bpm:.0f}bpm) — below Z3, imprecise for Z4 stimulus.",
                    suggestion="Set lower range >= 92% LTHR for a clean Z4 stimulus range.",
                ))
    return findings


def check_hr_range_consistency(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R009 — HR range consistency between description and intervals_icu code.

    When the description names a BPM range (e.g. 'HR 120-130' or '120-130 bpm'),
    the intervals_icu code must set that BPM range explicitly — not use 'Z<n> HR'.
    'Z<n> HR' pushes the full zone on Garmin sync, which for cross-zone ranges
    (e.g. Z1-upper + Z2-lower = 120-130) or partial-zone ranges leads to the wrong
    target. The athlete sees the sync code on the watch, not the description.

    Historical bug: description 'HR 120-130', intervals_icu '50m Z1 HR' →
    athlete gets Z1 range (1-125) instead of 120-130 on the watch.
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
        # Does description have a BPM range NOT also present in intervals_icu code?
        desc_bpm_matches = list(bpm_pattern.finditer(desc))
        if not desc_bpm_matches:
            continue
        intervals_bpm_matches = list(bpm_pattern.finditer(intervals))
        zone_only_matches = list(zone_only_pattern.finditer(intervals))
        # If intervals_icu contains "Z<n> HR" AND no explicit BPM range
        if zone_only_matches and not intervals_bpm_matches:
            # Extract range from description for the hint text
            for m in desc_bpm_matches:
                lo = m.group(1) or m.group(3)
                hi = m.group(2) or m.group(4)
                findings.append(Finding(
                    rule_id="R009",
                    severity=SEVERITY_WARNING,
                    workout=_workout_name(w),
                    message=(
                        f"Description names HR range {lo}-{hi}, but intervals_icu code "
                        f"uses '{zone_only_matches[0].group(0)}'. Athlete sees the full "
                        f"zone on the watch, not the specific BPM range."
                    ),
                    suggestion=(
                        f"Replace 'Z<n> HR' in intervals_icu code with an explicit "
                        f"BPM range, e.g. 'XXm HR {lo}-{hi}'."
                    ),
                ))
                break  # ein Treffer pro Workout reicht
    return findings


def check_easy_hr_ceiling(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R010 — Easy/Recovery run must not let HR ceiling creep into Z3.

    For workout_type EASY or RECOVERY, this rule checks whether the HR ceiling
    set in intervals_icu code or description exceeds the Z2 upper bound from
    athlete_status.md. Z3 territory = tempo/threshold, does not belong in
    recovery workouts.

    Historical bug: recovery run with HR 110-145 — 145 was mid-Z3
    (Z2 upper bound 139). Athlete corrected it manually; validator had
    no rule for it.

    Sport-science anchor: `framework/research/polarized-training-seiler.md`
    """
    findings = []
    # Extract Z2 upper bound from athlete_status.md — format:
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
        # Search for BPM ranges in both intervals_icu code and description
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
                            f"{wt} run has HR ceiling {hi} bpm in {source_name} — "
                            f"exceeds Z2 upper bound ({z2_upper} bpm) "
                            f"and creeps into Z3 (tempo). Easy/recovery workouts must "
                            f"never push into Z3+."
                        ),
                        suggestion=(
                            f"Set HR ceiling to max {z2_upper} bpm — "
                            f"for recovery character prefer 5-10 bpm buffer below."
                        ),
                    ))
                    break  # ein Treffer pro Source reicht
    return findings


def check_intervals_duration_sanity(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R011 — intervals_icu computed total must match duration_min.

    Historical bug: `Strides 4x 100m` in intervals_icu was interpreted by
    intervals.icu as 4 × 100 minutes (instead of 4 × 100m distance),
    resulting moving_time 9450s (157 min) for a workout planned as 65 min.

    This rule parses intervals_icu with the same heuristic (loop header `Nx`,
    step lines with Xm/Xs) and compares with workout.duration_min. Deviation
    >50% → ERROR (certainly a format bug), >25% → WARNING (probably press-lap
    or unparseable steps, but worth reviewing).

    The linter already blocks `distance instead of time` format
    (e.g. `100m`), but R011 also catches other parser discrepancies.
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
        # press-lap steps have no duration → low computed_s is OK,
        # only upward deviation (>50%) is certainly a bug.
        ratio = computed_s / planned_s
        if ratio > 1.5:
            findings.append(Finding(
                rule_id="R011",
                severity=SEVERITY_ERROR,
                workout=_workout_name(w),
                message=(
                    f"intervals_icu computed total {computed_s}s ({computed_s//60} min) "
                    f"is >{(ratio-1)*100:.0f}% above planned duration_min {duration_min} min. "
                    f"Likely a format bug (e.g. `100m` parsed as minutes instead of distance, or "
                    f"wrong loop multiplier)."
                ),
                suggestion=(
                    "Check intervals_icu steps: write strides as `- Xs` (seconds), "
                    "no distance notation (`100m`, `200m`) — intervals.icu interprets "
                    "`m` as minutes. Distance only in description prose, not in "
                    "intervals_icu code."
                ),
            ))
        elif ratio > 1.25:
            findings.append(Finding(
                rule_id="R011",
                severity=SEVERITY_WARNING,
                workout=_workout_name(w),
                message=(
                    f"intervals_icu computed total {computed_s}s ({computed_s//60} min) "
                    f"deviates +{(ratio-1)*100:.0f}% from duration_min {duration_min} min — "
                    f"review recommended."
                ),
                suggestion="Check steps and loop multiplier.",
            ))
    return findings


def check_intervals_step_targets(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R012 — intervals_icu steps must each carry a valid target.

    Two incident classes this rule prevents:

    (A) **Silent drop on arbitrary BPM ranges (all types, ERROR).**
        intervals.icu does not support `XX-YYbpm` syntax — the step is
        created but the target suffix is ignored, leaving the step without
        an HR anchor in `workout_doc`. Athlete gets no HR display on the
        watch. → Allowed HR tokens: `Zn HR`, `Zn-Zm HR`,
        `XX% LTHR`, `XX-YY% LTHR`, `XX% HR`, `XX-YY% HR`.

    (B) **Wahoo 422 for Ride steps without target (Ride only, ERROR).**
        Wahoo plan upload validates more strictly than intervals.icu and fails
        with `"each interval that is not of type 'repeat' must have a valid
        'targets' array"` when a Ride step only carries cadence (`110rpm`) or
        nothing at all. Spin-ups, cool-downs and recovery-pause steps must
        ALWAYS have a power/HR target.

    Run drills (hip-flexor, A-skips, leg swings etc.) are intentionally
    target-free — interpreted as cue steps. Therefore for Run:
    only main-set steps (duration ≥ 3 min) without target → WARNING.

    Both incident classes documented from real usage, details in
    `framework/research/intervals-icu-workout-syntax.md`.
    """
    import re

    # Tokens that count as a "real" target
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
                        f"intervals_icu step `{content[:80]}` uses "
                        f"arbitrary BPM range — intervals.icu silently drops "
                        f"the suffix, step ends up without HR target."
                    ),
                    suggestion=(
                        "Write HR targets as `Zn HR`, `XX-YY% LTHR` or "
                        "`XX-YY% HR`. Example conversion with "
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
                findings.append(Finding(
                    rule_id="R012",
                    severity=SEVERITY_ERROR,
                    workout=_workout_name(w),
                    message=(
                        f"intervals_icu step `{content[:80]}` (Ride) has no "
                        f"target (no watts, no HR zone, no % anchor). "
                        f"Wahoo plan upload will fail with 422."
                    ),
                    suggestion=(
                        "Ride steps ALWAYS need a target (including spin-ups, "
                        "recovery pauses, cool-downs). Examples: spin-up → "
                        "`15s 240W 110rpm`; recovery pause → `60s 150W`; "
                        "cool-down → `6m 130W 85rpm`."
                    ),
                ))
            else:
                # Run/other: drills (< 3 min) without target are OK,
                # longer main-set steps without target → WARNING
                dur_s = _step_duration_seconds(content)
                if dur_s >= 180:
                    findings.append(Finding(
                        rule_id="R012",
                        severity=SEVERITY_WARNING,
                        workout=_workout_name(w),
                        message=(
                            f"intervals_icu step `{content[:80]}` (Run) "
                            f"has {dur_s//60} min duration but no target "
                            f"— likely main-set without HR/pace anchor."
                        ),
                        suggestion=(
                            "Run drills < 3 min without target are OK (cue steps). "
                            "But main-set / longer steps need a target: "
                            "`Z2 HR`, `85-90% LTHR`, or `5:00/km Pace`."
                        ),
                    ))
    return findings


def check_intervals_repeat_block_adjacency(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R013 — Repeat block header (`Nx`) and its `-` items must be adjacent.

    intervals.icu's server parser only recognises a repeat block when the
    header (`Strides 5x`, `Set1 8x`, `Main Set 5x`) and its item lines
    are separated by simple newlines (`\\n`) — NO blank line.

    Incident pattern from real usage: strides block with blank line between
    `Strides 5x` and the `- Stride ...` items was parsed as `reps=1`
    instead of `reps=5`. Athlete got only 1 stride on the watch instead of
    5. Silent drift, no server error. Details:
    `framework/research/intervals-icu-workout-syntax.md` (trap C-bis).
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
                            f"Repeat block header `{line.strip()}` has a "
                            f"blank line before the `-` items — intervals.icu "
                            f"silently drops the repeat (reps=1 instead of N)."
                        ),
                        suggestion=(
                            f"Remove blank line between `{line.strip()}` and the "
                            f"first `-` item. Header and items must be adjacent "
                            f"(only `\\n`), blank line (`\\n\\n`) ONLY between "
                            f"different blocks."
                        ),
                    ))
    return findings


def check_easy_run_conservatism(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R014 — Easy/Z2-Run Conservatism Guard.

    Surfaces when an Easy/EASY run in the plan is significantly shorter than
    the rolling easy-run baseline of the last ~3 weeks AND coaching_notes /
    description contain no explicit recovery/symptom trigger.
    Potentially violates the `No silent conservatism` rule (CLAUDE.md).

    Drift incident pattern: an easy run was set well below the baseline
    despite green wellness signals and no documented recovery trigger. The
    cut came from an activity-NOTE cap (workout-type-specific) that was
    erroneously applied as a general run cap.
    """
    findings = []
    easy_runs = [
        w for w in workouts
        if w.get("type") == "Run"
        and (
            (w.get("workout_type") or "").upper() == "EASY"
            or (w.get("intensity") or "").lower() == "low"
        )
    ]
    if not easy_runs:
        return findings

    # Baseline aus den letzten 21 Tagen Easy-Runs (Long-Runs/Quality ausgeschlossen)
    recent_easy_durations = []
    for a in (ctx.recent_activities or [])[-30:]:
        if a.get("type") != "Run":
            continue
        dur = a.get("duration_min") or 0
        if dur < 20:
            continue  # too short for easy baseline
        # Exclude long runs (>=75 min) and quality runs (training_load >70)
        if dur >= 75:
            continue
        if (a.get("training_load") or 0) > 70:
            continue
        recent_easy_durations.append(dur)
    if len(recent_easy_durations) < 3:
        return findings  # insufficient baseline

    recent_easy_durations.sort()
    median_dur = recent_easy_durations[len(recent_easy_durations) // 2]

    RECOVERY_REASON_RE = re.compile(
        r"\b(recovery\s*week|deload|taper|active\s*injury|symptom|"
        r"acute\s*fatigue|abandoned|🔴|red\s*flag|reha\s*phase|"
        r"phase\s*[123]\s*aufbau|achilles[-\s]*schutz|"
        r"hrv.*🔴|intensityreadiness.*🔴|"
        r"morgensteifigkeit|nach\s*quality|post[-\s]*quality)\b",
        re.IGNORECASE,
    )

    for w in easy_runs:
        planned = w.get("duration_min") or 0
        if planned <= 0:
            continue
        if not median_dur:
            continue
        ratio = planned / median_dur
        if ratio >= 0.7:
            continue  # within 30% of baseline
        notes = (w.get("description") or "") + " " + (w.get("coaching_notes") or "")
        if RECOVERY_REASON_RE.search(notes):
            continue
        findings.append(Finding(
            rule_id="R014",
            severity=SEVERITY_WARNING,
            workout=_workout_name(w),
            message=(
                f"Easy run {planned} min = {int(ratio*100)}% of 30d easy median "
                f"({median_dur} min) — no explicit recovery triggers in the plan."
            ),
            suggestion=(
                "Over-conservatism suspect (CLAUDE.md §No silent conservatism). "
                "Either raise duration toward baseline or document a concrete "
                "recovery reason in coaching_notes/description "
                "(recovery week, red-flag wellness, acute symptom, rehab phase, "
                "achilles protection)."
            ),
        ))
    return findings


# Plugin registry: register new rules here.
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
    check_easy_run_conservatism,
]


# ─────────────────────────── Context Loader ───────────────────────────

def _read_config(path: str) -> str:
    from app.utils.paths import resolve_config
    try:
        return resolve_config(path).read_text()
    except FileNotFoundError:
        return ""


async def _fetch_recent_notes(target_date: str, days_back: int = 7) -> list[dict]:
    """Fetch NOTE events from intervals.icu for glute-DOMS / athlete feedback check."""
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


async def _fetch_recent_activities(target_date: str, days_back: int = 30) -> list[dict]:
    """Fetch recent activities from intervals.icu for conservatism guard (R014)."""
    client = IntervalsClient(settings.intervals_icu_athlete_id)
    end = datetime.fromisoformat(target_date).date()
    start = end - timedelta(days=days_back)
    activities = await client.get_activities(start.isoformat(), end.isoformat())
    return [
        {
            "date": a.get("start_date_local", "")[:10],
            "type": a.get("type"),
            "name": a.get("name"),
            "duration_min": int((a.get("moving_time") or 0) / 60),
            "training_load": a.get("icu_training_load"),
        }
        for a in activities
    ]


def _load_injury_locks() -> dict[str, list[str]]:
    """Load injury lock keywords from config/injury_locks.json (or config.example/ fallback)."""
    from app.utils.paths import resolve_config
    try:
        path = resolve_config("injury_locks.json")
        data = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    result: dict[str, list[str]] = {}
    for zone, cfg in data.items():
        if isinstance(cfg, dict):
            result[zone] = cfg.get("activation_keywords", [])
        elif isinstance(cfg, list):
            result[zone] = cfg
    return result


def load_context(target_date: str, fetch_remote: bool = True) -> Context:
    ctx = Context(
        target_date=target_date,
        athlete_static=_read_config("athlete_static.md"),
        athlete_status=_read_config("athlete_status.md"),
        training_paradigms=_read_config("training_paradigms.md"),
        injury_locks=_load_injury_locks(),
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
        try:
            ctx.recent_activities = asyncio.run(_fetch_recent_activities(target_date))
        except Exception:
            ctx.recent_activities = []
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
                message=f"Rule {rule.__name__} crashed: {exc}",
            ))
    return findings


def format_findings_text(findings: list[Finding]) -> str:
    if not findings:
        return "✅ No findings — plan is clean."
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
    parser.add_argument("--json", action="store_true", help="JSON output instead of plain text")
    parser.add_argument("--rule", default="", help="Run only one rule (e.g. R001)")
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
