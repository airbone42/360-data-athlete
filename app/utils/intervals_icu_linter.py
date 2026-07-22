"""Linter for intervals.icu workout description format.

Rules from .claude/agents/specialist-endurance.md:109-126.
"""
from __future__ import annotations

import re

# Matches distance-as-duration (forbidden): 1000m, 5km, 2.5km
_DISTANCE_DURATION_RE = re.compile(
    r"^\s*-\s+.*?\b(\d+(?:\.\d+)?)\s*(km|[Kk][Mm]|\d{3,}m)\b",
    re.MULTILINE,
)
# A "step line": starts with "- " and has a duration
_STEP_RE = re.compile(r"^\s*-\s+(.+)$", re.MULTILINE)
# Duration extraction: matches Xm, Xs, Xm Ys patterns
_DURATION_RE = re.compile(r"(\d+)\s*m(?:in)?(?:\s*(\d+)\s*s)?|(\d+)\s*s\b")
# HR target pattern — matches a %LTHR target (range "68-75% LTHR" or single
# "80% LTHR"), a Z1-Z5 zone, an explicit BPM range (e.g. "154-166 HR"), or a
# single-bpm threshold (e.g. "<140 bpm"). Linter treats any of these as a valid
# HR target on a step ≥60s.
#
# %LTHR must be listed: it is the preferred target form (intervals.icu resolves
# it to concrete bpm, which the watch then follows verbatim), while "Zn HR"
# resolves against the watch's own zone model and is deprecated. Without the
# %LTHR alternative every correctly-targeted step reported as target-less,
# which buries real findings under false positives.
_HR_ZONE_RE = re.compile(
    r"\d{1,3}\s*[-–—]\s*\d{1,3}\s*%\s*LTHR|\d{1,3}\s*%\s*LTHR"
    r"|Z[1-5]\s*HR|\d{2,3}\s*[-–—]\s*\d{2,3}\s*HR|\d{2,3}\s*bpm"
    r"|HR\s*\d{2,3}\s*[-–—]\s*\d{2,3}",
    re.IGNORECASE,
)
# press lap marker
_PRESS_LAP_RE = re.compile(r"press\s*lap", re.IGNORECASE)
# spm (forbidden for cadence — must be rpm)
_SPM_RE = re.compile(r"cadence\s+\d+\s*spm", re.IGNORECASE)
# Space before rpm (forbidden): "178 rpm" → should be "178rpm"
_RPM_SPACE_RE = re.compile(r"\d+\s+rpm\b")


def _parse_duration_seconds(step_line: str) -> int | None:
    """Return duration in seconds for a step line, or None if not parseable."""
    m = _DURATION_RE.search(step_line)
    if not m:
        return None
    if m.group(1):  # Xm or XmYs
        mins = int(m.group(1))
        secs = int(m.group(2)) if m.group(2) else 0
        return mins * 60 + secs
    if m.group(3):  # Xs
        return int(m.group(3))
    return None


# Loop-Header: "Hauptteil 5x", "Steigerungen 4x" — multiplier in front of x.
_LOOP_HEADER_RE = re.compile(r"\b(\d+)\s*x\b", re.IGNORECASE)


def compute_intervals_total_seconds(text: str) -> int:
    """Estimate total duration in seconds from an intervals.icu workout description.

    Heuristic matches intervals.icu's own parser:
    - Lines starting with `-` are steps; their duration is extracted via _parse_duration_seconds.
    - Non-step lines are headers. Headers containing `Nx` open a loop with N repetitions
      applied to the following step lines, until a blank line or the next header.
    - Headers without `Nx` reset the multiplier to 1.

    Returns 0 if text is empty or no parseable durations are found.
    """
    if not text or not text.strip():
        return 0

    total = 0
    current_mult = 1
    pending_steps_sum = 0

    def _flush():
        nonlocal total, pending_steps_sum, current_mult
        total += current_mult * pending_steps_sum
        pending_steps_sum = 0
        current_mult = 1

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            _flush()
            continue
        if stripped.startswith("-"):
            content = stripped[1:].strip()
            secs = _parse_duration_seconds(content)
            if secs is not None:
                pending_steps_sum += secs
            continue
        # Header line — flush previous, then check for Nx multiplier.
        _flush()
        m = _LOOP_HEADER_RE.search(stripped)
        current_mult = int(m.group(1)) if m else 1

    _flush()
    return total


def _distance_in_step(content: str) -> bool:
    """True if a step line contains a distance token (km, ≥3-digit m) that
    intervals.icu may mis-parse as minutes."""
    if not re.search(r"\b\d+\s*km\b|\b\d{2,}\s*m\b", content, re.IGNORECASE):
        return False
    # Exclude prefixed approximations like "≈ 1000m" in free text.
    if re.search(r"[≈~]\s*\d", content):
        return False
    # Exclude pure-minute notations like "5m", "10m" — only flag 100m, 200m, …, or km
    # where the "m" is unambiguously distance because it has 3+ digits or a km suffix.
    if re.search(r"\b\d+\s*km\b", content, re.IGNORECASE):
        return True
    if re.search(r"\b\d{3,}\s*m\b", content):
        return True
    # "100m" matches both \d{3,}m and the bug case — covered above.
    return False


def intervals_icu_blocking_errors(text: str) -> list[str]:
    """Return blocking-severity violations only (Distance-as-duration ambiguity).

    push_workouts.py treats these as hard ERRORs and aborts the push.
    Other findings (cadence, HR-target) remain WARNINGs via validate_intervals_icu().
    """
    if not text or not text.strip():
        return []
    blockers: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-") and not _LOOP_HEADER_RE.search(stripped):
            # Skip non-step / non-loop-header lines.
            continue
        content = stripped[1:].strip() if stripped.startswith("-") else stripped
        if _distance_in_step(content):
            blockers.append(
                f"Distance format forbidden: '{stripped}' — intervals.icu interprets "
                f"'100m'/'1km' as minutes, not as distance. Use seconds for "
                f"strides (`- 20s`), no distance in the intervals_icu block."
            )
    return blockers


def validate_intervals_icu(text: str) -> list[str]:
    """Return list of rule violations. Empty list = valid."""
    if not text or not text.strip():
        return []

    errors: list[str] = []
    lines = text.splitlines()

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue

        content = stripped[1:].strip()

        # Rule: distance format forbidden
        if _distance_in_step(content):
            errors.append(
                f"Distance format forbidden: '{stripped}' — use time (Xm/Xs) instead of distance"
            )

        # Rule: step lines must start with an alphabetic label (drill name,
        # "Easy", "Warmup", "Cool-down", "Warm-up jog", "Stride", "Einlaufen",
        # ...). intervals.icu extracts the leading token as the Garmin step
        # label. When a step starts with a duration ("- 30s Hip Flexor"),
        # Garmin sees no label and just shows "Run".
        # Exception: steps WITH an HR target — the HR zone fills in as label
        # ("- 4m Z4 HR" → Garmin shows "Z4 HR").
        has_hr_here = bool(_HR_ZONE_RE.search(content))
        if re.match(r"^\d", content) and not has_hr_here:
            errors.append(
                f"Step starts with duration instead of label: '{stripped}' — format is "
                f"'<label> <duration> [<target>]' (e.g. 'Hip Flexor 30s', "
                f"'Easy 5m press lap'). Otherwise intervals.icu extracts no step "
                f"label for Garmin sync and Garmin shows just 'Run'."
            )

        # Rule: cadence must use rpm, not spm
        if _SPM_RE.search(content):
            errors.append(f"Cadence: 'spm' forbidden — use 'rpm': '{stripped}'")

        # Rule: no space before rpm
        if _RPM_SPACE_RE.search(content):
            errors.append(f"No space before 'rpm': '{stripped}' → '178rpm'")

        # Duration-dependent rules
        duration_s = _parse_duration_seconds(content)
        has_hr = bool(_HR_ZONE_RE.search(content))
        has_press_lap = bool(_PRESS_LAP_RE.search(content))

        if duration_s is not None:
            # Warm-up / cool-down label detection — bilingual (German +
            # English) so both wordings are recognised.
            is_warmup_cooldown = bool(
                re.search(
                    r"\b(einlaufen|auslaufen|warm[-\s]?up\s*jog|cool[-\s]?down\s*jog)\b",
                    content,
                    re.IGNORECASE,
                )
            )

            if is_warmup_cooldown:
                # Warm-up / cool-down: must use press lap, no HR target
                if has_hr:
                    errors.append(
                        f"Warm-up / cool-down jog must not have an HR target: '{stripped}' — remove Z* HR"
                    )
            elif duration_s >= 60 and not has_hr and not has_press_lap:
                # Steps ≥60s: must have an HR zone (unless press lap)
                errors.append(
                    f"Step ≥60s without HR target: '{stripped}' — add an HR zone (Z1-Z5 HR) or 'press lap'"
                )
            elif duration_s < 60 and has_hr:
                # Steps <60s: no HR target
                errors.append(
                    f"Step <60s should not have an HR target: '{stripped}'"
                )

    return errors
