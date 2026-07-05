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
    exercise_progressions: str = ""
    competition_plan: str = ""
    recent_notes: list[dict] = field(default_factory=list)
    recent_activities: list[dict] = field(default_factory=list)
    sport_settings: list[dict] = field(default_factory=list)
    injury_locks: dict[str, list[str]] = field(default_factory=dict)
    # Per-zone allow-patterns (regex strings) that exempt a matching exercise
    # line from the zone's lock — athlete-specific clearances documented in
    # config/injury_locks.json (e.g. a cleared passive Dead Hang). The
    # framework default (config.example) keeps these empty so a fresh user
    # starts fully locked.
    injury_lock_allows: dict[str, list[str]] = field(default_factory=dict)
    weekly_hard_reize_balance: str = ""
    # Current fitness (CTL) — fetched fail-soft from intervals.icu wellness;
    # None when offline / fetch failed. Used by R014 to map onto the
    # per-phase easy-run band in competition_plan.md.
    ctl: float | None = None
    # WARNING findings from failed remote fetches in load_context() —
    # surfaced by run_validation() so rules that silently self-deactivate
    # on missing context (R004/R006/R014/R017) are visible as degraded.
    load_warnings: list[Finding] = field(default_factory=list)


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
    # Rotator-cuff internal-rotation band work is a low-load endurance/
    # fatigue protocol (high reps by design, e.g. a physio-prescribed 3x25
    # to fatigue the internal rotators) — not a hypertrophy lift. External
    # rotation stays in the override cap list (typically prescribed ≤15).
    r"\binnenrotat", r"\binternal\s*rotat",
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
    r"\boverhead\s*press", r"\bschulterpress",
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
    r"\bdead\s*hang",
    # Bare "hang"/"hanging" (e.g. "Bar Hang 30s", "Hanging Leg Raise") — but
    # NOT hang-position lift variants ("hang power clean", "hang snatch"),
    # which start from a hang position and are no bar hangs. "overhang" is
    # excluded by the leading \b.
    r"\bhang(?:ing)?\b(?!\s*(?:power\s+)?(?:clean|snatch))",
]

# Heavy overhead push — barbell overhead is heavy by construction; named
# overhead-press variants count as heavy from HEAVY_OVERHEAD_MIN_KG
# (exception: light KB OHP at rehab loads, e.g. 4 kg). The weight-bound
# pattern follows the canonical specialist inline format
# `Name: SxR Wkg | RPE` — the load may sit anywhere after the exercise
# name on the line (but not past a `|` separator or a line break).
HEAVY_OVERHEAD_BARBELL_RE = re.compile(
    r"\b(?:barbell|langhantel)\s*overhead", re.IGNORECASE
)
HEAVY_OVERHEAD_WEIGHTED_RE = re.compile(
    r"\b(?:overhead\s*press|schulterpress\w*|military\s*press)\b"
    r"[^|\n]*?\b(\d{1,3}(?:[.,]\d+)?)\s*kg\b",
    re.IGNORECASE,
)
HEAVY_OVERHEAD_MIN_KG = 10.0


def _is_heavy_overhead(line: str) -> bool:
    """True when the line prescribes a heavy overhead push (R002)."""
    if HEAVY_OVERHEAD_BARBELL_RE.search(line):
        return True
    m = HEAVY_OVERHEAD_WEIGHTED_RE.search(line)
    if m:
        return float(m.group(1).replace(",", ".")) >= HEAVY_OVERHEAD_MIN_KG
    return False


# Dead-hang exception (R002): holds of 2-5 s are rehab-tier and allowed.
_DEAD_HANG_RE = re.compile(r"\bdead\s*hang\b", re.IGNORECASE)
_HOLD_SECONDS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*s(?:ec|ek)?\b", re.IGNORECASE)


def _dead_hang_allowed(line: str) -> bool:
    """True when the line is a dead hang whose hold times are all 2-5 s.

    The seconds are parsed numerically — substring matches like the `5s`
    inside `15s`/`45s` must NOT pass as allowed holds.
    """
    m = _DEAD_HANG_RE.search(line)
    if not m:
        return False
    secs = [
        float(x.replace(",", "."))
        for x in _HOLD_SECONDS_RE.findall(line[m.end():])
    ]
    return bool(secs) and all(2 <= s <= 5 for s in secs)

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
    - Config-driven clearance: `injury_locks.json` may list `allow_patterns`
      per zone (regex) that exempt a cleared exercise at any dosage — e.g. a
      physio-cleared passive Dead Hang. The framework default
      (config.example) keeps these empty so a fresh user starts fully locked;
      an athlete documents the clearance in their own config/injury_locks.json.
    - Dead Hang with hold times of 2-5 s is allowed framework-wide as a
      rehab-tier decompression hold even without an allow_pattern; longer
      holds (15 s, 45 s) stay blocked unless an allow_pattern clears them.
    - Hang-position lift variants (hang power clean, hang snatch) are not
      bar hangs and are not matched by the hang lock.
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
    shoulder_allows = ctx.injury_lock_allows.get("shoulder", [])
    for w in workouts:
        name = _workout_name(w)
        for line in _exercise_lines(_description(w)):
            if _matches_any(line, SHOULDER_LOCK_PATTERNS):
                # Config-driven clearance (config/injury_locks.json allow_patterns)
                # — e.g. an athlete whose passive Dead Hang is physio-cleared at
                # any hold time. Pull-up/rope/traverse/campus patterns are separate
                # and stay blocked unless their own allow-pattern is configured.
                if shoulder_allows and _matches_any(line, shoulder_allows):
                    continue
                if _dead_hang_allowed(line):
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
            if _is_heavy_overhead(line):
                findings.append(Finding(
                    rule_id="R002",
                    severity=SEVERITY_ERROR,
                    workout=name,
                    message=f"Heavy overhead press despite shoulder restriction: «{line[:80]}»",
                    suggestion="Reduce load to rehab level (KB OHP 4kg = OK) or remove exercise.",
                ))
    return findings


def check_surface_required(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R003 — Run/Ride must have a surface field (shoe advisor depends on it).

    Valid values are the canonical tokens from `app.utils.surface`
    (`asphalt | forest-path | trail | track | treadmill`); legacy spellings
    (e.g. `forstweg`) stay accepted as read-aliases.
    """
    from app.utils.surface import CANONICAL_SURFACES, normalize_surface

    findings = []
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
                suggestion=f"Set surface: one of {sorted(CANONICAL_SURFACES)}",
            ))
        elif normalize_surface(surface) is None:
            findings.append(Finding(
                rule_id="R003",
                severity=SEVERITY_WARNING,
                workout=_workout_name(w),
                message=f"surface='{surface}' not in standard set — shoe advisor uses heuristic.",
                suggestion=f"Standardize: {sorted(CANONICAL_SURFACES)}",
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
                          `framework/research/plyometrics-frequency-recovery.md`,
                          `framework/research/plyometric-exercise-catalog-and-progression.md`
                          (§7: which plyo exercises stay available under a
                          tendon freeze — concentric slow-SSC — vs. contraindicated)
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
                        f"Replace '{zone_only_matches[0].group(0)}' in "
                        f"intervals_icu code with the explicit range in "
                        f"allowed grammar: convert {lo}-{hi} bpm to %LTHR "
                        f"and write 'XXm YY-ZZ% LTHR' (YY/ZZ = bound ÷ LTHR "
                        f"× 100). Arbitrary BPM suffixes are silently "
                        f"dropped by intervals.icu (see R012)."
                    ),
                ))
                break  # ein Treffer pro Workout reicht
    return findings


def check_run_hr_zone_target(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R020 — Run HR targets must use `% LTHR`, not `Zn HR`.

    A `Z<n> HR` step is resolved by the athlete's device against ITS OWN
    HR-zone config (frequently a %HRmax model), NOT the intervals.icu
    LTHR-based zones. When the two diverge, the on-watch target and the
    audible alarm are wrong — the classic case: device Z2 = 60-70 % HRmax
    sits well below the LTHR-based Z2, so an easy/recovery run runs "in
    zone" on the watch (no alarm) while intervals.icu calls it Z1. `% LTHR`
    resolves to explicit bpm the device follows verbatim, independent of its
    zone config. WARNING (a given athlete's device zones may happen to
    match); applies to every run type incl. easy/recovery — the regression
    pattern is easy runs falling back to `Zn HR` while quality uses `% LTHR`.
    """
    findings = []
    zone_only_pattern = re.compile(r"\bZ\d+\s*HR\b", flags=re.IGNORECASE)
    for w in workouts:
        if (w.get("type") or "").lower() != "run":
            continue
        intervals = w.get("intervals_icu") or ""
        matches = zone_only_pattern.findall(intervals)
        if not matches:
            continue
        findings.append(Finding(
            rule_id="R020",
            severity=SEVERITY_WARNING,
            workout=_workout_name(w),
            message=(
                f"Run HR step uses '{matches[0].strip()}' — the watch resolves the "
                f"zone against its own device HR-zone config (often %HRmax), not the "
                f"intervals.icu LTHR zones. If they diverge, the on-watch target and "
                f"alarm are wrong (e.g. an easy run never alarms)."
            ),
            suggestion=(
                "Emit the HR target as '% LTHR' so intervals.icu resolves it to "
                "explicit bpm the device follows verbatim: 'XXm YY-ZZ% LTHR' "
                "(YY/ZZ = corridor bound / LTHR * 100). Applies to every run type "
                "incl. easy/recovery."
            ),
        ))
    return findings


def check_easy_hr_ceiling(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R010 — Easy/Recovery run must not let HR ceiling creep into Z3.

    For workout_type EASY or RECOVERY, this rule checks whether the HR ceiling
    set in intervals_icu code or description exceeds the Z2 upper bound from
    athlete_status.md. Z3 territory = tempo/threshold, does not belong in
    recovery workouts.

    Detected ceiling notations:
    - explicit BPM ranges: `120-145 bpm` and `HR 120-145` (no `bpm` literal)
    - %LTHR / %HR ranges: `84-90% LTHR` — the upper bound is converted via
      the LTHR from athlete_status.md; when no LTHR is available, a WARNING
      surfaces instead of silently skipping the check
    - zone targets in intervals_icu steps: `Z3 HR` (or higher, or a
      cross-zone range ending Z3+) on an easy/recovery run → direct ERROR

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
    lthr_match = re.search(
        r"LTHR\s*(?:aktuell|current)[:\*\s]*?(\d{2,3})\s*bpm", ctx.athlete_status
    )
    lthr = int(lthr_match.group(1)) if lthr_match else None

    bpm_range_pattern = re.compile(
        r"\b(\d{2,3})\s*[-–—]\s*(\d{2,3})\s*bpm\b"
        r"|\bHR\s*(\d{2,3})\s*[-–—]\s*(\d{2,3})\b",
        flags=re.IGNORECASE,
    )
    pct_range_pattern = re.compile(
        r"\b(\d{2,3})\s*[-–—]\s*(\d{2,3})\s*%\s*(?:LTHR|HR)\b",
        flags=re.IGNORECASE,
    )
    zone_hr_pattern = re.compile(
        r"\bZ(\d)(?:\s*[-–]\s*Z?(\d))?\s*HR\b", flags=re.IGNORECASE
    )

    for w in workouts:
        if (w.get("type") or "").lower() != "run":
            continue
        wt = (w.get("workout_type") or "").upper()
        if wt not in ("EASY", "RECOVERY"):
            continue
        # Search both intervals_icu code and description; at most one
        # finding per source (first violating notation wins). Use the raw
        # description field here — _description() falls back to
        # intervals_icu when description is empty, which would re-scan the
        # same text and double-count a single ceiling violation.
        sources = [
            ("intervals_icu", w.get("intervals_icu") or ""),
            ("description", (w.get("description") or "").strip()),
        ]
        for source_name, text in sources:
            finding: Finding | None = None
            # (a) explicit BPM ceilings — `120-145 bpm` or `HR 120-145`
            for match in bpm_range_pattern.finditer(text):
                hi = int(match.group(2) or match.group(4))
                if hi > z2_upper:
                    finding = Finding(
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
                    )
                    break
            # (b) %LTHR / %HR ranges — convert the upper bound via LTHR
            if finding is None:
                for match in pct_range_pattern.finditer(text):
                    hi_pct = int(match.group(2))
                    if lthr is None:
                        finding = Finding(
                            rule_id="R010",
                            severity=SEVERITY_WARNING,
                            workout=_workout_name(w),
                            message=(
                                f"{wt} run uses %LTHR/%HR range "
                                f"'{match.group(0)}' in {source_name}, but no "
                                f"LTHR was found in athlete_status.md — cannot "
                                f"verify the ceiling against the Z2 upper bound "
                                f"({z2_upper} bpm)."
                            ),
                            suggestion=(
                                "Add 'LTHR current: NNN bpm' to athlete_status.md "
                                "so easy-run ceilings in %LTHR can be verified."
                            ),
                        )
                        break
                    hi_bpm = lthr * hi_pct / 100
                    if hi_bpm > z2_upper:
                        finding = Finding(
                            rule_id="R010",
                            severity=SEVERITY_ERROR,
                            workout=_workout_name(w),
                            message=(
                                f"{wt} run has HR ceiling {hi_pct}% LTHR "
                                f"≈ {hi_bpm:.0f} bpm in {source_name} — "
                                f"exceeds Z2 upper bound ({z2_upper} bpm) "
                                f"and creeps into Z3 (tempo). Easy/recovery "
                                f"workouts must never push into Z3+."
                            ),
                            suggestion=(
                                f"Cap the range at {z2_upper / lthr * 100:.0f}% LTHR "
                                f"(= Z2 upper bound {z2_upper} bpm) — for recovery "
                                f"character prefer a buffer below."
                            ),
                        )
                        break
            # (c) zone targets Z3+ on intervals_icu steps → direct ERROR
            # (intervals_icu only — description prose may legitimately say
            # "stay below Z3 HR")
            if finding is None and source_name == "intervals_icu":
                for match in zone_hr_pattern.finditer(text):
                    zmax = max(int(g) for g in match.groups() if g)
                    if zmax >= 3:
                        finding = Finding(
                            rule_id="R010",
                            severity=SEVERITY_ERROR,
                            workout=_workout_name(w),
                            message=(
                                f"{wt} run step targets '{match.group(0)}' in "
                                f"intervals_icu — Z3+ is tempo/threshold "
                                f"territory. Easy/recovery workouts must never "
                                f"push into Z3+."
                            ),
                            suggestion=(
                                f"Use 'Z1 HR'/'Z2 HR' (or a %LTHR range whose "
                                f"ceiling stays at or below the Z2 upper bound, "
                                f"{z2_upper} bpm) on easy/recovery steps."
                            ),
                        )
                        break
            if finding is not None:
                findings.append(finding)
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

    # Tokens that count as a "real" target.
    # For Z-zone notation we split Power vs HR/Pace because intervals.icu
    # interprets bare `Zn` as a POWER-zone reference — on Run/VirtualRun
    # there is no power zone, so `Zn` alone is silently dropped and the
    # step ends up without a target. Always require the explicit `HR` or
    # `Pace` suffix on Run steps.
    TARGET_PATTERNS_COMMON = [
        r"\d+(?:-\d+)?w\b",                  # 220w, 200-240w
        r"\d+(?:-\d+)?%\s*(?:ftp|map|mmp|lthr|hr|pace)?\b",  # 75%, 95-105% LTHR
        r"\bZ\d(?:-Z\d)?\s+(?:HR|Pace)\b",   # Z2 HR, Z2-Z3 HR, Z2 Pace — explicit suffix
        r"\d+:\d+/(?:km|100m)\s*Pace",       # 5:00/km Pace
        r"\bramp\s+\d+",                     # ramp 50%-75%
        r"\bfreeride\b",
    ]
    TARGET_PATTERNS_RIDE = TARGET_PATTERNS_COMMON + [
        r"\bZ\d(?:-Z\d)?\b",                 # Z2 (bare) is power zone on bike — valid
    ]
    # Power-bearing targets for a Ride. A Ride step needs at least ONE of
    # these — an HR-only target (`Z1 HR`, `% LTHR`, `% HR`) passes the
    # generic has_target check but Wahoo's smart-trainer plan upload rejects
    # it with the same 422. Bare `%` defaults to %FTP (power); `% LTHR/HR/
    # Pace` are explicitly NOT power.
    POWER_PATTERNS_RIDE = [
        r"\d+(?:-\d+)?w\b",                          # 220w, 200-240w
        r"\d+(?:-\d+)?%\s*(?:ftp|map|mmp)\b",        # 95% FTP, 105% MAP
        r"\d+(?:-\d+)?%(?!\s*(?:ftp|map|mmp|lthr|hr|pace))",  # bare 75% = %FTP power
        r"\bZ\d(?:-Z\d)?\b(?!\s+(?:HR|Pace))",       # bare Zn = power zone
        r"\bramp\s+\d+",
        r"\bfreeride\b",
    ]
    BARE_ZONE_RE = re.compile(r"\bZ\d(?:-Z\d)?\b(?!\s+(?:HR|Pace))", re.IGNORECASE)
    # A bare percent (`90%`, `95%`, `80-90%`) WITHOUT a unit suffix. On a
    # Run/VirtualRun there is no power meter, so intervals.icu reads it as a
    # %FTP POWER target and drops a meaningless watt goal on the watch — the
    # classic stride trap `- Stride 20s 95%`. The explicit forms (`% LTHR`,
    # `% HR`, `% Pace`, `% FTP/MAP/MMP`) are excluded by the negative
    # lookahead, so only the unit-less percent trips this.
    BARE_PCT_RUN_RE = re.compile(
        r"\d+(?:-\d+)?%(?!\s*(?:ftp|map|mmp|lthr|hr|pace))", re.IGNORECASE
    )
    # Arbitrary BPM targets — with literal `bpm` suffix, or as `HR lo-hi`
    # without the literal (both silently dropped by intervals.icu).
    BAD_BPM_RE = re.compile(
        r"\b\d+(?:-\d+)?\s*bpm\b|\bHR\s*\d{2,3}\s*[-–]\s*\d{2,3}\b",
        re.IGNORECASE,
    )
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

            target_patterns = TARGET_PATTERNS_RIDE if is_ride else TARGET_PATTERNS_COMMON
            has_target = any(re.search(p, content, re.IGNORECASE) for p in target_patterns)

            # Run/VirtualRun-specific catch: a bare percent (`90%`, `95%`) is
            # silently parsed by intervals.icu as a %FTP POWER target — junk on
            # a Run (no power meter), lands as a meaningless watt goal on the
            # watch. Classic on strides written as `- Stride 20s 95%`. A stride
            # takes NO target; the effort cue (Mile-/1km race pace) belongs in
            # the workout description. `has_target` is True here (the bare % is
            # matched as a target token), so this catch runs regardless of it.
            if not is_ride and BARE_PCT_RUN_RE.search(content):
                findings.append(Finding(
                    rule_id="R012",
                    severity=SEVERITY_ERROR,
                    workout=_workout_name(w),
                    message=(
                        f"intervals_icu step `{content[:80]}` (Run) carries a "
                        f"bare percent — intervals.icu reads it as %FTP power "
                        f"and drops a junk watt target on the watch. Runs have "
                        f"no power zone."
                    ),
                    suggestion=(
                        "Strides/surges take NO target: write `- Stride 20s` "
                        "and put the effort cue (`Mile-/1km race pace, fast "
                        "feet, no HR chasing`) in the workout description. For a "
                        "sustained effort use `% LTHR` / `Zn HR` / `m:ss/km "
                        "Pace`, never a bare percent."
                    ),
                ))
                continue

            # Run/VirtualRun-specific catch: `Zn` or `Zn-Zm` WITHOUT a `HR`/`Pace`
            # suffix is silently dropped or mis-tagged on Run. The intervals.icu
            # server parser is greedy and tags `Z4` ANYWHERE on the step line as a
            # power-zone target, including inside cue free text after an em-dash.
            # Drift incident pattern: `- Calf raises easy 1m — neuromuskuläre
            # Wake-up vor Z4` landed in workout_doc as
            # `{text: 'Calf raises easy', power: {units: 'power_zone', value: 4}}`
            # — a nonsensical Power-Z4 target on a Run step.
            # → Scan the entire content (em-dash is NOT a parser boundary on the
            # intervals.icu side).
            if not is_ride and BARE_ZONE_RE.search(content) and not has_target:
                dur_s = _step_duration_seconds(content)
                if dur_s >= 60:  # short cue steps (< 1 min) tolerated
                    findings.append(Finding(
                        rule_id="R012",
                        severity=SEVERITY_ERROR,
                        workout=_workout_name(w),
                        message=(
                            f"intervals_icu step `{content[:80]}` (Run) uses "
                            f"bare `Zn` notation — intervals.icu interprets that "
                            f"as a Power zone and silently drops it on Run. "
                            f"Step ends up without HR target on the watch."
                        ),
                        suggestion=(
                            "Append the explicit suffix: `Z2 HR`, `Z1-Z2 HR`, "
                            "`Z4 HR`. Or use `% LTHR` / `% HR` notation. "
                            "Bare `Zn` is valid only on Ride/VirtualRide (Power zone)."
                        ),
                    ))
                    continue

            # Ride-specific: a step whose ONLY target is HR/pace (no power)
            # passes intervals.icu but Wahoo's smart-trainer plan upload
            # rejects it with the same 422 (`valid 'targets' array`) — a Ride
            # step needs a POWER target. Recurrence pattern: warm-up / set-rest
            # / cool-down written as `Z1 HR` on an indoor Ride — validator
            # passed (HR counts as a target), Wahoo 422'd. After a hard
            # interval an HR-Z1 target is physiologically pointless anyway
            # (HR lags the effort by 5-10 min). Details in
            # `framework/research/intervals-icu-workout-syntax.md` Trap B.
            if is_ride and has_target:
                has_power = any(
                    re.search(p, content, re.IGNORECASE) for p in POWER_PATTERNS_RIDE
                )
                if not has_power:
                    findings.append(Finding(
                        rule_id="R012",
                        severity=SEVERITY_ERROR,
                        workout=_workout_name(w),
                        message=(
                            f"intervals_icu step `{content[:80]}` (Ride) carries "
                            f"only an HR/pace target (no watts, no %FTP, no power "
                            f"zone). Wahoo plan upload rejects HR-only targets on a "
                            f"smart-trainer ride with the same 422."
                        ),
                        suggestion=(
                            "Give every Ride step a POWER target. Convert HR steps "
                            "to watts: warm-up/recovery/cool-down → e.g. `9m 150W "
                            "90rpm`, `3m 150W`, `8m 130W`. Cadence/HR may stay as "
                            "secondary, but watts must lead on an indoor ride."
                        ),
                    ))
                    continue

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

    # Repeat header: must NOT start with a `-` (dash = list item, not a header).
    # Optional leading cue (e.g. `Strides`, `Main Set`) followed by `Nx`.
    REPEAT_HEADER_RE = re.compile(r"^\s*(?:[A-Za-zÄÖÜäöüß0-9 _]+\s+)?\d+x\s*$", re.IGNORECASE)
    # Dash-prefixed pseudo-header (`- 4x` alone on a line) — silent drift:
    # intervals.icu treats this as a list item, not a repeat header.
    DASH_PSEUDO_HEADER_RE = re.compile(r"^\s*-\s*\d+x\s*$", re.IGNORECASE)
    findings = []
    for w in workouts:
        icu = w.get("intervals_icu") or ""
        if not icu.strip():
            continue
        lines = icu.split("\n")
        for idx, raw in enumerate(lines):
            line = raw.rstrip()
            if DASH_PSEUDO_HEADER_RE.match(line):
                findings.append(Finding(
                    rule_id="R013",
                    severity=SEVERITY_ERROR,
                    workout=_workout_name(w),
                    message=(
                        f"Repeat block header `{line.strip()}` is dash-prefixed "
                        f"— intervals.icu parses this as a list item, NOT as a "
                        f"repeat header. The following `- ` items are treated as "
                        f"adjacent steps, not loop body. Step count silently "
                        f"degrades to reps=1."
                    ),
                    suggestion=(
                        f"Drop the leading `- `. Header must be standalone: "
                        f"`{line.strip().lstrip('-').strip()}` (just `Nx` or "
                        f"`<Cue> Nx`)."
                    ),
                ))
                continue
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


def _parse_exercise_progressions(text: str) -> dict[str, dict]:
    """Parse ``exercise_progressions.md`` into {name → current-state dict}.

    Returns a mapping where each value carries the documented numeric
    anchors derived from the most recent ``- **Aktueller Stand**`` line
    under a ``### <Exercise Name>`` heading:

    - ``hold_s``  — first ``\\d+s Hold`` (or ``\\d+ s Hold``) match
    - ``weight_kg`` — first ``\\d+(?:[.,]\\d+)? kg`` match
    - ``reps``    — second integer in a ``\\d+ × \\d+`` (sets × reps)
    - ``sets``    — first integer in a ``\\d+ × \\d+``
    - ``per_side`` — whether the ``Aktueller Stand`` line carries
      ``je Seite`` / ``/Seite`` / ``per side``

    Exercises whose Aktueller Stand reads "unbekannt"/"noch nicht
    isoliert"/"-" produce a stub with all numeric fields = None. R016
    skips those silently.
    """
    out: dict[str, dict] = {}
    if not text:
        return out
    HEADING_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
    matches = list(HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        name = m.group(1).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end]
        # Find Aktueller Stand line
        stand_match = re.search(
            r"^\s*-?\s*\*\*Aktueller Stand[^*]*\*\*\s*:?\s*(.*?)$",
            body,
            re.MULTILINE,
        )
        if not stand_match:
            continue
        stand_line = stand_match.group(1).strip()
        if not stand_line or stand_line.lower().startswith(("unbekannt", "noch nicht", "—", "-")):
            out[name] = {"sets": None, "reps": None, "weight_kg": None, "hold_s": None, "per_side": False, "raw": stand_line}
            continue
        # Parse values from stand_line
        sets_reps = re.search(r"(\d+)\s*[×xX]\s*(\d+)", stand_line)
        weight = re.search(r"(\d+(?:[.,]\d+)?)\s*kg\b", stand_line)
        hold = re.search(r"(\d+)\s*s\s*Hold\b", stand_line)
        per_side = bool(re.search(r"(?:je\s*Seite|/\s*Seite|per\s*side)", stand_line, re.IGNORECASE))
        out[name] = {
            "sets": int(sets_reps.group(1)) if sets_reps else None,
            "reps": int(sets_reps.group(2)) if sets_reps else None,
            "weight_kg": float(weight.group(1).replace(",", ".")) if weight else None,
            "hold_s": int(hold.group(1)) if hold else None,
            "per_side": per_side,
            "raw": stand_line,
        }
    return out


def _parse_workout_exercise_line(line: str) -> dict | None:
    """Parse a workout-description exercise line into numeric anchors.

    Recognises the conventional shape ``<Name>: <sets>x<reps>[/Seite]
    [<weight>kg] [Xs Hold] | <rest>``. Returns ``None`` when the line
    doesn't look like an exercise (no colon, or only metadata).
    """
    s = line.strip()
    if not s or s.startswith(("#", "[", "—", "-", "•")):
        return None
    # Expect a leading "<Name>:" — fall through if absent
    head_match = re.match(r"^([A-Za-zÄÖÜäöüß0-9 ()\-'\.&+/]+?)\s*:\s+(.*)$", s)
    if not head_match:
        return None
    name = head_match.group(1).strip()
    rest = head_match.group(2)
    if len(name) < 3 or len(name) > 80:
        return None
    sets_reps = re.search(r"(\d+)\s*[xX×]\s*(\d+)", rest)
    weight = re.search(r"(\d+(?:[.,]\d+)?)\s*kg\b", rest)
    hold = re.search(r"(\d+)\s*s\s*Hold\b", rest)
    return {
        "name": name,
        "sets": int(sets_reps.group(1)) if sets_reps else None,
        "reps": int(sets_reps.group(2)) if sets_reps else None,
        "weight_kg": float(weight.group(1).replace(",", ".")) if weight else None,
        "hold_s": int(hold.group(1)) if hold else None,
        "raw": s,
    }


def _estimate_session_seconds(description: str) -> tuple[int, int] | None:
    """Estimate the realistic duration (s) of a non-endurance session from
    its description exercise lines, for the R018 plausibility check.

    Handles the conventional shapes the specialists emit:
      ``3x35s/Seite``            → 3 sets × 35 s hold, bilateral (×2)
      ``3x8/Seite``              → 3 sets × 8 reps, bilateral
      ``3x7/Richtung Tempo 3-0-3`` → bilateral (per Richtung), 6 s/rep
      ``3x10/Seite 9s Hold``     → 3 sets × 10 reps × 9 s hold, bilateral

    The two error classes this catches are the ones that produced a
    half-length estimate in real use: (a) per-side / per-direction work
    not doubled, (b) isometric hold-time × reps × sets not summed.

    Conservative by design — work time plus a modest inter-set rest, so the
    R018 threshold (declared < 0.6 × estimate) only trips on gross
    underestimates, not ±20 % noise. Returns ``(seconds, exercise_count)``
    or ``None`` when no exercise line parsed.
    """
    if not description:
        return None
    DEFAULT_REP_S = 4          # a controlled rep with no tempo/hold given
    REST_PER_SET_S = 25        # inter-set reset + setup, conservative
    total = 0
    n_ex = 0
    for raw in description.split("\n"):
        line = raw.strip()
        # sets × N, capturing whether N is a timed hold ("35s") vs reps
        m = re.search(r"(\d+)\s*[xX×]\s*(\d+)\s*(s)?", line)
        if not m:
            continue
        sets = int(m.group(1))
        n = int(m.group(2))
        timed = m.group(3) == "s"
        if sets < 1 or sets > 20:
            continue
        per_side = bool(re.search(
            r"(?:je\s*(?:Seite|Richtung)|/\s*(?:Seite|Richtung)|per\s*side)",
            line, re.IGNORECASE))
        sides = 2 if per_side else 1
        if timed:
            # N is the hold duration in seconds; one hold per set
            set_work = n
        else:
            reps = n
            tempo = re.search(r"Tempo\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)", line)
            hold = re.search(r"(\d+)\s*s\s*Hold\b", line)
            if tempo:
                rep_s = sum(int(tempo.group(i)) for i in (1, 2, 3))
            elif hold:
                rep_s = int(hold.group(1)) + 2  # hold + lift/lower
            else:
                rep_s = DEFAULT_REP_S
            set_work = reps * rep_s
        total += sets * set_work * sides + sets * REST_PER_SET_S
        n_ex += 1
    if n_ex == 0:
        return None
    return total, n_ex


_REGRESSION_EXEMPTION_RE = re.compile(
    r"\b(?:deload|recovery\s*week|race[-\s]*week|taper|"
    r"symptom[-\s]*(?:stop|onset)|regression|"
    r"volumen[-\s]*(?:cut|decke)|"
    r"rhr[-\s]*(?:drift|anstieg|\+\d|hoch|peak)|"
    r"joint[-\s]*signal|last[-\s]*cap|cap[-\s]*aktiv|"
    r"stop[-\s]*kriterium\s*aktiv|"
    r"hold[-\s]*back\s+wegen|reduziert\s+wegen)\b",
    re.IGNORECASE,
)


def _match_exercise_name(planned_name: str, documented_names: list[str]) -> str | None:
    """Match a workout-line name against documented progression headings.

    The plan free-text may carry variants ("Farmer's Hold KB einarmig"
    vs the heading "Farmer's Hold (KB, einarmig)"). Strategy: exact
    case-insensitive substring in either direction, then a token-jaccard
    fallback for variant punctuation.
    """
    planned_norm = re.sub(r"[\s,'()\-]+", " ", planned_name).strip().lower()
    if not planned_norm:
        return None
    best = None
    best_score = 0.0
    for doc in documented_names:
        doc_norm = re.sub(r"[\s,'()\-]+", " ", doc).strip().lower()
        if not doc_norm:
            continue
        if planned_norm == doc_norm:
            return doc
        if doc_norm in planned_norm or planned_norm in doc_norm:
            score = min(len(doc_norm), len(planned_norm)) / max(
                len(doc_norm), len(planned_norm)
            )
            if score > best_score:
                best, best_score = doc, score
            continue
        # token-jaccard fallback
        a = set(planned_norm.split())
        b = set(doc_norm.split())
        if not a or not b:
            continue
        jacc = len(a & b) / len(a | b)
        if jacc >= 0.6 and jacc > best_score:
            best, best_score = doc, jacc
    return best


def check_exercise_regression(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R016 — Hold-time / load regression on rotation-cadence exercises.

    Catches the silent regression class where today's plan drops a
    numeric anchor (Hold-Seconds, Weight-kg, Reps) **below** the value
    documented as ``- **Aktueller Stand**`` in
    ``config/exercise_progressions.md``, without an explicit
    regression-justifying keyword in the exercise line or the workout's
    coaching_notes.

    Anchor for the canonical case: McGill Curl-up was at 8 s Hold per
    21.05. (athlete-confirmed schmerzfrei RPE 6-7). Today's plan
    proposed 7 s — silent regression that landed in the pushed event
    until the athlete spotted it. Root cause was a type-history
    tag-filter coverage gap: the 21.05.-session was tagged
    ``legs, plyo, core`` and didn't appear in the
    ``--tags ninja,grip`` history fetch the specialist relied on.

    Trigger conditions (per exercise line in each workout's
    description):

    1. A documented Aktueller Stand exists in ``exercise_progressions``
       for an exercise name matched by ``_match_exercise_name``.
    2. The planned numeric anchor (hold_s OR weight_kg OR reps) is
       strictly less than the documented value.
    3. Neither the line itself nor the workout's coaching_notes
       contain a regression-exempting keyword (deload / recovery week /
       taper / symptom / regression / Volumen-Cut / RHR-Drift /
       joint-signal / last-cap / cap aktiv / monitoring / stop-
       kriterium / on-cadence halten).

    The "exempt by keyword" path keeps legitimate volume-cuts and
    joint-cap holds out of the error stream — they must be visible in
    the plan to be respected.
    """
    documented = _parse_exercise_progressions(ctx.exercise_progressions or "")
    if not documented:
        return []
    doc_names = list(documented.keys())
    findings: list[Finding] = []
    for w in workouts:
        desc = w.get("description") or ""
        if not desc:
            continue
        coaching_notes = w.get("coaching_notes") or ""
        notes_exempt = bool(_REGRESSION_EXEMPTION_RE.search(coaching_notes))
        for raw_line in desc.split("\n"):
            parsed = _parse_workout_exercise_line(raw_line)
            if not parsed:
                continue
            match_name = _match_exercise_name(parsed["name"], doc_names)
            if not match_name:
                continue
            doc = documented[match_name]
            # Check each numeric anchor for a regression
            regressions: list[tuple[str, float, float]] = []
            for key in ("hold_s", "weight_kg", "reps"):
                doc_val = doc.get(key)
                planned_val = parsed.get(key)
                if doc_val is None or planned_val is None:
                    continue
                if planned_val < doc_val:
                    regressions.append((key, planned_val, doc_val))
            if not regressions:
                continue
            # Line-level exemption check (e.g. "Last-Cap @ 9 kg", "Cap aktiv")
            line_exempt = bool(_REGRESSION_EXEMPTION_RE.search(parsed["raw"]))
            if notes_exempt or line_exempt:
                # Document as INFO so the regression is still visible
                # in the audit trail without blocking the push.
                tags_msg = ", ".join(
                    f"{k} {planned}<{doc_val}" for k, planned, doc_val in regressions
                )
                findings.append(Finding(
                    rule_id="R016",
                    severity=SEVERITY_INFO,
                    workout=_workout_name(w),
                    message=(
                        f"Documented regression on '{match_name}' "
                        f"({tags_msg}) accepted via exemption keyword "
                        f"({'workout coaching_notes' if notes_exempt else 'exercise line'})."
                    ),
                    suggestion="No action required — keep the exemption phrase visible.",
                ))
                continue
            tags_msg = ", ".join(
                f"{k} {planned}<{doc_val}" for k, planned, doc_val in regressions
            )
            findings.append(Finding(
                rule_id="R016",
                severity=SEVERITY_ERROR,
                workout=_workout_name(w),
                message=(
                    f"Silent regression on '{match_name}': "
                    f"{tags_msg} (documented Aktueller Stand: "
                    f"{doc.get('raw') or '?'}). The plan drops a value "
                    f"below the documented current state without a "
                    f"regression-justifying keyword."
                ),
                suggestion=(
                    "Either (a) raise the planned value to the documented "
                    "Aktueller Stand, or (b) add an explicit reason to "
                    "the exercise line / workout coaching_notes — "
                    "e.g. 'Last-Cap aktiv', 'RHR-Drift +X bpm', "
                    "'Volumen-Cut wegen Y', 'Symptom-Stop seit Datum', "
                    "'Deload', 'Recovery week active', 'Taper window'."
                ),
            ))
    return findings


def check_intervals_repeat_press_lap(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R015 — Interval-recovery steps inside a repeat block may not be press_lap.

    `press lap` makes a step athlete-controlled (athlete presses the lap
    button to advance). That is the correct pattern for **warm-up** and
    **cool-down** (HF-Drift / kalter Start, athlete decides when to start
    the main set), but NOT for **interval-recovery** between repeats
    (e.g. Trab-Pause zwischen Threshold-Reps oder Stride-Recoveries).

    Inside a repeat block, every step needs a defined duration so the
    timer advances deterministically; otherwise the recovery becomes a
    lottery and the entire repeat structure loses its prescribed
    spacing.

    Drift incident pattern: A Long-Z2 plan had `Optional Surges 3x`
    followed by `- Stride 25s 80%` and `- Easy 90s press lap`. The
    `press lap` on the recovery caused the timer to wait for a manual
    lap-press between strides, instead of running the prescribed 90s
    Z1-Trab. The athlete spotted the inconsistency before the run.

    Rule: lines inside a repeat block (items starting with `- ` after a
    `Nx` header) may not contain the case-insensitive substring
    `press lap`.
    """
    REPEAT_HEADER_RE = re.compile(r"^\s*(?:[A-Za-zÄÖÜäöüß0-9 _]+\s+)?(\d+)x\s*$", re.IGNORECASE)
    PRESS_LAP_RE = re.compile(r"press\s*lap", re.IGNORECASE)
    findings = []
    for w in workouts:
        icu = w.get("intervals_icu") or ""
        if not icu.strip():
            continue
        lines = icu.split("\n")
        idx = 0
        while idx < len(lines):
            line = lines[idx].rstrip()
            m = REPEAT_HEADER_RE.match(line)
            if not m:
                idx += 1
                continue
            # Found a repeat header — walk subsequent `-` items until a blank
            # line or non-dash line.
            header_text = line.strip()
            body_idx = idx + 1
            # Skip a single blank line right after the header — R013 catches
            # that as a parser bug separately; here we still want to detect
            # press_lap if items follow further down.
            while body_idx < len(lines) and lines[body_idx].strip() == "":
                body_idx += 1
            while body_idx < len(lines):
                body_line = lines[body_idx].rstrip()
                stripped = body_line.strip()
                if not stripped:
                    break  # blank line ends the repeat body
                if not stripped.startswith("-"):
                    break  # non-dash line ends the repeat body
                if PRESS_LAP_RE.search(stripped):
                    findings.append(Finding(
                        rule_id="R015",
                        severity=SEVERITY_ERROR,
                        workout=_workout_name(w),
                        message=(
                            f"`press lap` inside repeat block `{header_text}` — "
                            f"item: `{stripped}`. Interval-recovery must have a "
                            f"defined duration; press_lap turns the timer into "
                            f"an athlete-controlled wait and breaks repeat "
                            f"spacing."
                        ),
                        suggestion=(
                            "Replace `press lap` with a deterministic recovery "
                            "spec: `Easy {N}s Z1 HR` (locker traben) for a "
                            "fixed-duration trab between Strides/intervals, or "
                            "an explicit zone target. `press lap` is reserved "
                            "for warm-up/cool-down (athlete-controlled start of "
                            "the next block, OK due to HF-Drift)."
                        ),
                    ))
                body_idx += 1
            idx = body_idx
    return findings


# ── Phase-band anchor for R014 (competition_plan.md "Lauf-Dauer-Logik pro Phase") ──
# Canonical easy-run-duration anchor: the per-phase band keyed by CTL, NOT a
# rolling-median heuristic. A markdown table whose rows carry a `CTL lo–hi`
# label and an easy-run `lo–hi min` cell defines the band; the first
# `lo–hi min` cell in the row is the Easy/Z2 column (the Long-Run column that
# follows uses larger numbers and frequently an arrow `→`, not a dash). The
# floor (band lower bound) is the threshold below which an easy run is
# over-conservative unless a documented recovery trigger applies.
_PHASE_CTL_RANGE_RE = re.compile(r"CTL\s*(\d+)\s*[–\-]\s*(\d+)", re.IGNORECASE)
_EASY_BAND_MIN_RE = re.compile(r"(\d+)\s*[–\-]\s*(\d+)\s*min", re.IGNORECASE)


def _easy_run_phase_floor(ctx: Context) -> int | None:
    """Lower bound (min) of the current phase's easy-run band, or None.

    Returns None when competition_plan.md carries no parseable phase-band
    table, or when CTL is unavailable (offline / fetch failed) — in which
    case R014 falls back to the rolling-median heuristic. Opt-in: athletes
    without a documented phase-band table are unaffected.
    """
    if ctx.ctl is None or not ctx.competition_plan:
        return None
    best: tuple[int, int, int] | None = None  # (lo, hi, easy_floor)
    last: tuple[int, int, int] | None = None
    for line in ctx.competition_plan.splitlines():
        if "|" not in line:
            continue
        m_ctl = _PHASE_CTL_RANGE_RE.search(line)
        if not m_ctl:
            continue
        m_easy = _EASY_BAND_MIN_RE.search(line)
        if not m_easy:
            continue
        lo, hi = int(m_ctl.group(1)), int(m_ctl.group(2))
        easy_floor = int(m_easy.group(1))
        last = (lo, hi, easy_floor)
        if lo <= ctx.ctl < hi:
            best = (lo, hi, easy_floor)
            break
    chosen = best or (last if (last and ctx.ctl >= last[1]) else None)
    return chosen[2] if chosen else None


def check_easy_run_conservatism(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R014 — Easy/Z2-Run Conservatism Guard.

    Primary anchor (when available): the per-phase easy-run band in
    `competition_plan.md` keyed by current CTL ("Lauf-Dauer-Logik pro
    Phase"). An easy run shorter than the phase-band floor with no
    documented recovery/symptom trigger is an ERROR (the canonical anchor
    per the `No silent conservatism` rule — duration is derived from the
    phase band, not a per-day default or a recent-session median).

    Fallback anchor (no phase-band table or CTL offline): the rolling
    easy-run median of the last ~30 days; an easy run below 70 % of it
    with no documented trigger is a WARNING.

    Drift incident pattern: an easy run was set well below the documented
    Aufbau-II phase floor (60 min) on a green-physiology day; the
    median-only guard computed 86 % of the recent median and stayed
    silent, so a sub-phase-floor run passed unflagged.
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

    RECOVERY_REASON_RE = re.compile(
        r"\b(recovery\s*week|deload|taper|active\s*injury|symptom|"
        r"acute\s*fatigue|abandoned|🔴|red\s*flag|reha\s*phase|"
        r"phase\s*[123]\s*aufbau|achilles[-\s]*schutz|"
        r"hrv.*🔴|intensityreadiness.*🔴|"
        r"morgensteifigkeit|nach\s*quality|post[-\s]*quality)\b",
        re.IGNORECASE,
    )

    def _is_exempt(w: dict) -> bool:
        """Indoor / brick / recovery runs have their own duration roles
        (competition_plan.md) and are exempt from the easy-run floor."""
        if w.get("indoor"):
            return True
        name = (w.get("name") or "").lower()
        notes = (w.get("description") or "") + " " + (w.get("coaching_notes") or "")
        if "brick" in name or "brick" in notes.lower():
            return True
        return bool(RECOVERY_REASON_RE.search(notes))

    # ── Primary anchor: per-phase band floor (ERROR) ──
    phase_floor = _easy_run_phase_floor(ctx)
    if phase_floor is not None:
        for w in easy_runs:
            planned = w.get("duration_min") or 0
            if planned <= 0 or _is_exempt(w):
                continue
            if planned < phase_floor:
                findings.append(Finding(
                    rule_id="R014",
                    severity=SEVERITY_ERROR,
                    workout=_workout_name(w),
                    message=(
                        f"Easy run {planned} min is below the phase floor "
                        f"({phase_floor} min, current CTL {ctx.ctl:.1f}) — "
                        f"competition_plan.md derives easy-run duration from "
                        f"the per-phase band, not a per-day default."
                    ),
                    suggestion=(
                        "Raise the easy run to at least the phase-band floor "
                        "(CLAUDE.md §No silent conservatism). Heat is a reason "
                        "to run slower (HR-capped), not shorter. Shorten below "
                        "the floor only with a documented trigger in "
                        "coaching_notes/description (recovery week, red-flag "
                        "wellness, achilles morning stiffness, acute symptom) "
                        "or mark the run indoor/brick."
                    ),
                ))
        return findings

    # ── Fallback anchor: rolling easy-run median (WARNING) ──
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

    for w in easy_runs:
        planned = w.get("duration_min") or 0
        if planned <= 0:
            continue
        if not median_dur:
            continue
        ratio = planned / median_dur
        if ratio >= 0.7:
            continue  # within 30% of baseline
        if _is_exempt(w):
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


def check_weekly_hardreize_cap(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R017 — Weekly Hard-Reize cap (cross-training-slot semantics).

    Errors when today's plan contains structured Z4+ intervals in a system
    whose Hard-Reiz is already logged in the rolling 7d window per
    `context.weeklyHardReizeBalance`, with no active taper window to
    legitimise an extra Quality session.

    Cross-training-slot semantics (CLAUDE.md Pre-planning health check §4):
    a cross-training slot exists *for* cross-training (sparing
    tendons/joints, varying the metabolic vector). When the athlete waives
    the cross-training Reiz of the week, the open slot **defers** to the
    next week — it does not substitute into the primary system as a
    second same-system Hard-Reiz.

    Trigger conditions (all must hold for ERROR):
    1. `ctx.weekly_hard_reize_balance` is present.
    2. That balance shows `✓` for the workout's system (Run or Ride).
    3. The workout has a Hard-Reiz signature: `intervals` tag OR
       intervals_icu text contains `Z4 HR`/`Z5 HR` OR `% LTHR` ≥ 95.
    4. No active taper window detected in `athlete_status` or
       `training_paradigms` (regex: `taper\\s+(active|aktiv|window\\s*open)`
       OR `RACE_A\\s*in\\s*\\d+d` with `d ≤ taper_length_default`).

    The rule is opt-in via the presence of `weeklyHardReizeBalance` —
    athletes without a defined Hard-Reize-Strategy (signal absent or
    empty) bypass this check silently.

    Drift incident pattern: athlete waived cross-training Hard-Reiz of
    the week ("rather run today, weather is too good"); head coach
    repurposed the open slot into a second Run-Z4 Quality despite
    Run-Threshold already logged earlier in the same rolling 7d window.
    The athlete caught the double-load.
    """
    findings = []
    balance = (ctx.weekly_hard_reize_balance or "").strip()
    if not balance:
        return findings  # signal absent → rule does not fire (opt-in)

    # Parse the balance string for completed Hard-Reize per system.
    run_done = False
    ride_done = False
    for line in balance.splitlines():
        s = line.strip()
        if s.startswith("✓") and "run" in s.lower():
            run_done = True
        elif s.startswith("✓") and ("bike" in s.lower() or "ride" in s.lower()):
            ride_done = True

    if not (run_done or ride_done):
        return findings  # nothing in the week to cap against

    # Taper-window override: if athlete_status / training_paradigms / coaching
    # notes acknowledge an active taper, the cap is waived for race-spec work.
    taper_re = re.compile(
        r"\btaper\s+(?:active|aktiv|window\s*(?:open|aktiv))\b|"
        r"\brace[-\s]?week\s+(?:active|aktiv)\b",
        re.IGNORECASE,
    )
    if taper_re.search(ctx.athlete_status or "") or taper_re.search(ctx.training_paradigms or ""):
        return findings

    HARD_SIG_RE = re.compile(
        r"\bZ4\s*HR\b|\bZ5\s*HR\b|(?<!\d)(?:9[5-9]|1\d\d)\s*%\s*LTHR\b",
        re.IGNORECASE,
    )

    for w in workouts:
        w_type = (w.get("type") or "")
        tags = [str(t).lower() for t in (w.get("tags") or [])]
        intervals_text = w.get("intervals_icu") or ""
        coaching_notes = (w.get("coaching_notes") or "")

        # Per-workout taper acknowledgment (head coach documents the override)
        if taper_re.search(coaching_notes):
            continue

        is_intervals = "intervals" in tags
        is_z4_plus = bool(HARD_SIG_RE.search(intervals_text))
        if not (is_intervals or is_z4_plus):
            continue

        is_run = w_type in {"Run", "VirtualRun"}
        is_ride = w_type in {"Ride", "VirtualRide"}

        if is_run and run_done:
            findings.append(Finding(
                rule_id="R017",
                severity=SEVERITY_ERROR,
                workout=_workout_name(w),
                message=(
                    "Second Run Hard-Reiz in rolling 7d — primary-system "
                    "Hard-Reiz already logged this week per "
                    "weeklyHardReizeBalance. The cross-training-slot "
                    "semantics rule (CLAUDE.md Pre-planning health check §4) "
                    "says: defer, don't substitute."
                ),
                suggestion=(
                    "Move structured Z4+ Run-block to next week as that "
                    "week's Hard-Reiz. Today: replace with Z2/Long/Recovery "
                    "in the run, or swap into a Ride-VO2max if the "
                    "cross-training slot is what's open. If a true taper "
                    "window is active, document it in athlete_status.md or "
                    "the workout's coaching_notes (regex: "
                    "`taper active`/`race-week active`)."
                ),
            ))
        elif is_ride and ride_done:
            findings.append(Finding(
                rule_id="R017",
                severity=SEVERITY_ERROR,
                workout=_workout_name(w),
                message=(
                    "Second Ride Hard-Reiz in rolling 7d — primary-system "
                    "Hard-Reiz already logged this week per "
                    "weeklyHardReizeBalance."
                ),
                suggestion=(
                    "Move structured Z4+ Ride-block to next week. Today: "
                    "replace with Z2/Endurance or swap to Run-Threshold if "
                    "that slot is open. Taper override via coaching_notes "
                    "if applicable."
                ),
            ))
    return findings


# Plugin registry: register new rules here as explicit (rule_id, check_fn)
# pairs. `--rule` selection matches on the rule_id, not on docstring
# substrings — keep ids unique (enforced by tests/test_validate_plan_registry.py).
def check_duration_plausibility(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R018 — Non-endurance duration_min must roughly match the structure.

    Endurance sessions are duration-checked by R011 (intervals_icu total).
    Strength / core / reha sessions had no equivalent guard, so an
    eyeballed ``duration_min`` could land at half the real time — the
    intervals.icu time block then lies, and the athlete plans the day
    around a wrong number.

    The estimator (``_estimate_session_seconds``) sums sets × reps ×
    (tempo|hold seconds) with explicit ×2 for per-Seite / per-Richtung
    work plus inter-set rest. WARNING (not ERROR) when the declared time
    is below 60 % of the estimate — it is an estimate, the athlete may
    train faster, but a 2× gap is a planning bug worth surfacing.
    """
    findings: list[Finding] = []
    for w in workouts:
        if (w.get("type") or "") in ("Run", "Ride", "VirtualRun", "VirtualRide"):
            continue  # covered by R011 + intervals_icu carries its own duration
        declared_min = w.get("duration_min") or 0
        if not declared_min:
            continue  # rest day / no time block
        est = _estimate_session_seconds(w.get("description") or "")
        if not est:
            continue
        est_s, n_ex = est
        if n_ex < 2 or est_s < 12 * 60:
            continue  # too small / too little structure to estimate reliably
        if declared_min * 60 < 0.6 * est_s:
            est_min = round(est_s / 60)
            findings.append(Finding(
                rule_id="R018",
                severity=SEVERITY_WARNING,
                workout=_workout_name(w),
                message=(
                    f"Declared duration {declared_min} min is implausibly short vs "
                    f"the structure estimate ~{est_min} min ({n_ex} exercises, "
                    f"per-Seite/Richtung doubled + holds summed). intervals.icu "
                    f"will display a too-short time block."
                ),
                suggestion=(
                    f"Set duration_min ≈ {est_min}. Compute bottom-up: per exercise "
                    f"sets × reps × (Tempo- or Hold-Sekunden), ×2 for /Seite or "
                    f"/Richtung, plus inter-set rest. Isometric holds and bilateral "
                    f"doubling dominate core/reha sessions — they are the usual cause "
                    f"of a half-length estimate."
                ),
            ))
    return findings


def check_quality_warmup_priming(workouts: list[dict], ctx: Context) -> list[Finding]:
    """R019 — VO2max short-interval sessions must prime the warm-up.

    A pure easy warm-up does not prime VO2 on-kinetics: the first work reps
    run under a slow primary-VO2 response and fall below the
    time-above-90%-VO2max window — which for short-rep formats (30/15,
    30/30) is the entire stimulus. Evidence + protocol:
    ``framework/research/warmup-priming-intervals.md``.

    Scope: only VO2max-SHORT sessions (a loop body with a work rep ≤ 45 s
    carrying a target) — there priming is MANDATORY. Threshold / long-rep
    interval sessions have minutes-long reps where priming is merely
    optional, so they are skipped. The warm-up region (everything before
    the first loop header) must contain at least one priming spike: a
    short step (10–120 s) that carries an intensity target. Missing → a
    WARNING (advisory, overridable via ``priming-exempt`` in
    ``coaching_notes``), never a hard block.
    """
    import re

    DUR_MIN = re.compile(r"\b(\d+)m\b", re.IGNORECASE)
    DUR_SEC = re.compile(r"\b(\d+)s\b", re.IGNORECASE)
    LOOP = re.compile(r"\b\d+x\b", re.IGNORECASE)
    PRESS = re.compile(r"\bpress\s+lap\b", re.IGNORECASE)
    TARGET = re.compile(
        r"\d+(?:-\d+)?w\b"            # watts: 330w, 300-340w
        r"|\d+(?:-\d+)?\s*%"          # any percentage: 95%, 90% FTP, 95-99% LTHR
        r"|\bZ\d(?:-Z\d)?\b"          # zone: Z2, Z4-Z5
        r"|\d+:\d+/(?:km|100m)",      # pace: 4:05/km
        re.IGNORECASE,
    )

    def _dur_s(text: str) -> int:
        secs = 0
        m = DUR_MIN.search(text)
        if m:
            secs += int(m.group(1)) * 60
        s = DUR_SEC.search(text)
        if s:
            secs += int(s.group(1))
        return secs

    findings: list[Finding] = []
    for w in workouts:
        if (w.get("type") or "") not in ("Run", "Ride", "VirtualRun", "VirtualRide"):
            continue
        icu = w.get("intervals_icu") or ""
        if not icu.strip():
            continue
        lines = icu.split("\n")

        # First standalone loop header (`Nx`) marks the start of the main set.
        first_loop = None
        for i, raw in enumerate(lines):
            ls = raw.strip()
            if ls and not ls.startswith("-") and LOOP.search(ls):
                first_loop = i
                break
        if first_loop is None:
            continue  # no rep loop → not an interval session

        # VO2max-SHORT? loop body (dash lines right after the header) has a
        # work step ≤ 45 s with a target.
        is_short = False
        for raw in lines[first_loop + 1:]:
            ls = raw.strip()
            if ls == "" or not ls.startswith("-"):
                break  # end of the loop body
            content = ls.lstrip("-").strip()
            d = _dur_s(content)
            if 0 < d <= 45 and TARGET.search(content):
                is_short = True
                break
        if not is_short:
            continue  # threshold / long-rep → priming optional, skip

        notes = ((w.get("coaching_notes") or "") + " " + (w.get("description") or "")).lower()
        if "priming-exempt" in notes:
            continue

        # Warm-up region = everything before the first loop header. Look for
        # at least one short heavy spike (press-lap and target-free drills
        # do not count).
        has_spike = False
        for raw in lines[:first_loop]:
            ls = raw.strip()
            if not ls.startswith("-"):
                continue
            content = ls.lstrip("-").strip()
            if PRESS.search(content):
                continue
            d = _dur_s(content)
            if 10 <= d <= 120 and TARGET.search(content):
                has_spike = True
                break

        if not has_spike:
            findings.append(Finding(
                rule_id="R019",
                severity=SEVERITY_WARNING,
                workout=_workout_name(w),
                message=(
                    "VO2max short-interval session has no priming spike in the "
                    "warm-up — the first work reps run under a slow primary-VO2 "
                    "response and fall below the time-above-90%-VO2max window."
                ),
                suggestion=(
                    "Add 2-3 short heavy spikes before the first work rep "
                    "(Ride e.g. `- Spike 60s 330W`; Run e.g. `- Stride 20s` — "
                    "fast, effort cue in the description, NO bare percent), "
                    "60-90s easy between, then 3-5 min easy into Set 1. See "
                    "research/warmup-priming-intervals.md. Override with "
                    "`priming-exempt` in coaching_notes if intentional."
                ),
            ))
    return findings


RULES: list[tuple[str, Callable[[list[dict], Context], list[Finding]]]] = [
    ("R001", check_reps_ceiling),
    ("R002", check_injury_locks_shoulder),
    ("R003", check_surface_required),
    ("R004", check_glute_doms),
    ("R005", check_achilles_plyo_surface),
    ("R006", check_lthr_settings_drift),
    ("R007", check_pillar_rotation),
    ("R008", check_intervals_lthr_format),
    ("R009", check_hr_range_consistency),
    ("R010", check_easy_hr_ceiling),
    ("R011", check_intervals_duration_sanity),
    ("R012", check_intervals_step_targets),
    ("R013", check_intervals_repeat_block_adjacency),
    ("R014", check_easy_run_conservatism),
    ("R015", check_intervals_repeat_press_lap),
    ("R016", check_exercise_regression),
    ("R017", check_weekly_hardreize_cap),
    ("R018", check_duration_plausibility),
    ("R019", check_quality_warmup_priming),
    ("R020", check_run_hr_zone_target),
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


async def _fetch_ctl(target_date: str) -> float | None:
    """Fetch current CTL from intervals.icu wellness for R014's phase-band floor."""
    client = IntervalsClient(settings.intervals_icu_athlete_id)
    wellness = await client.get_wellness(target_date)
    ctl = (wellness or {}).get("ctl")
    return float(ctl) if ctl is not None else None


async def _fetch_raw_activities_for_hardreize(target_date: str) -> list[dict]:
    """Fetch raw activities (rolling 7d) including tags + zone times for R017.

    Returns the unmapped intervals.icu activity dicts (`start_date_local`,
    `type`, `name`, `tags`, `icu_hr_zone_times`) so the shared helper
    `_compute_weekly_hard_reize_balance` can detect Hard-Reize per system.
    """
    client = IntervalsClient(settings.intervals_icu_athlete_id)
    end = datetime.fromisoformat(target_date).date()
    start = end - timedelta(days=7)
    return await client.get_activities(start.isoformat(), end.isoformat())


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


def _load_injury_lock_allows() -> dict[str, list[str]]:
    """Load per-zone allow_patterns from config/injury_locks.json.

    Optional schema key — a zone may carry `allow_patterns: [regex, ...]`
    listing exercise patterns that are explicitly cleared and must NOT trip
    the lock (athlete-specific clearance). Absent/empty by default."""
    from app.utils.paths import resolve_config
    try:
        path = resolve_config("injury_locks.json")
        data = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    result: dict[str, list[str]] = {}
    for zone, cfg in data.items():
        if isinstance(cfg, dict) and cfg.get("allow_patterns"):
            result[zone] = cfg["allow_patterns"]
    return result


def load_context(target_date: str, fetch_remote: bool = True) -> Context:
    ctx = Context(
        target_date=target_date,
        athlete_static=_read_config("athlete_static.md"),
        athlete_status=_read_config("athlete_status.md"),
        training_paradigms=_read_config("training_paradigms.md"),
        exercise_progressions=_read_config("exercise_progressions.md"),
        competition_plan=_read_config("competition_plan.md"),
        injury_locks=_load_injury_locks(),
        injury_lock_allows=_load_injury_lock_allows(),
    )
    if fetch_remote:
        # Fail-soft per source: a failed fetch never crashes the validator,
        # but it MUST surface as a WARNING finding — otherwise the rules
        # depending on that source silently self-deactivate.
        def _degraded(source: str, impact: str, exc: Exception) -> None:
            ctx.load_warnings.append(Finding(
                rule_id="VALIDATOR",
                severity=SEVERITY_WARNING,
                workout="(global)",
                message=f"{impact} inactive: {source} fetch failed: {exc}",
                suggestion=(
                    "Validator runs degraded (fail-soft) — the listed rule "
                    "silently passes. Check intervals.icu connectivity/"
                    "credentials, or run with --no-remote to acknowledge "
                    "offline mode."
                ),
            ))

        try:
            ctx.recent_notes = asyncio.run(_fetch_recent_notes(target_date))
        except Exception as exc:  # noqa: BLE001
            ctx.recent_notes = []
            _degraded("recent-notes", "R004 (glute DOMS)", exc)
        try:
            ctx.sport_settings = asyncio.run(_fetch_sport_settings())
        except Exception as exc:  # noqa: BLE001
            ctx.sport_settings = []
            _degraded("sport-settings", "R006 (LTHR drift)", exc)
        try:
            ctx.recent_activities = asyncio.run(_fetch_recent_activities(target_date))
        except Exception as exc:  # noqa: BLE001
            ctx.recent_activities = []
            _degraded("recent-activities", "R014 (easy-run conservatism)", exc)
        try:
            ctx.ctl = asyncio.run(_fetch_ctl(target_date))
        except Exception as exc:  # noqa: BLE001
            ctx.ctl = None
            _degraded("wellness/CTL", "R014 (phase-band easy-run floor)", exc)
        try:
            raw = asyncio.run(_fetch_raw_activities_for_hardreize(target_date))
            from app.graphs.sub_athlete_context.context_builder import _compute_weekly_hard_reize_balance
            ctx.weekly_hard_reize_balance = _compute_weekly_hard_reize_balance(
                raw, datetime.fromisoformat(target_date).date()
            )
        except Exception as exc:  # noqa: BLE001
            ctx.weekly_hard_reize_balance = ""
            _degraded("hard-reize activities", "R017 (weekly hard-reize cap)", exc)
    return ctx


# ─────────────────────────── Main ───────────────────────────

def run_validation(workouts: list[dict], ctx: Context, only_rule: str = "") -> list[Finding]:
    # Degraded-context warnings (failed remote fetches) always surface,
    # so silently self-deactivated rules are visible in the output.
    findings = list(ctx.load_warnings)
    for rule_id, rule in RULES:
        if only_rule and only_rule.strip().upper() != rule_id:
            continue
        try:
            findings.extend(rule(workouts, ctx))
        except Exception as exc:  # noqa: BLE001
            findings.append(Finding(
                rule_id="VALIDATOR",
                severity=SEVERITY_WARNING,
                workout="(global)",
                message=f"Rule {rule_id} ({rule.__name__}) crashed: {exc}",
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
