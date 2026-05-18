"""Sync athlete-edited workout descriptions back into config/exercise_progressions.md.

The athlete may modify a strength session's description in intervals.icu — either
on the event before the training (e.g. "5 kg too heavy → 4 kg") or on the
activity after the training ("only 12 reps instead of 15"). The reasons matter
(lower weight, different form), but the edits never reach the local config and
are silently overwritten on the next planning cycle.

This script reads the activity description, parses each exercise via the
existing `app.analytics.exercise_parser`, looks up the matching section in
`config/exercise_progressions.md`, and updates the `**Aktueller Stand:**` line
for the affected exercise — leaving form notes, progression vector, and pflicht-
setup blocks untouched.

Out of scope (per architectural decision):
  - `config/exercise_log.md` form/technique findings
  - Endurance sessions (Run/Ride)
  - Creating new exercise sections (unmapped exercises are logged but not added)

Usage:
    python3 scripts/sync_description_drift.py --activity-id i12345678
    python3 scripts/sync_description_drift.py --activity-id i12345678 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from datetime import date as date_cls
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.analytics.exercise_parser import (  # noqa: E402
    ParsedExercise,
    match_to_mapping_key,
    normalise_exercise_name,
    parse_description,
    parse_line,
)
from app.utils.paths import CONFIG_DIR, resolve_config  # noqa: E402

PROGRESSIONS_PATH = CONFIG_DIR / "exercise_progressions.md"
STRENGTH_ACTIVITY_TYPES = {"WeightTraining", "Workout"}

WEIGHT_EPS = 0.05  # kg
DURATION_EPS = 0.5  # seconds


@dataclass
class Section:
    header: str  # raw text after "### "
    header_line: int  # 0-based index of "### …" line
    stand_line: int | None  # 0-based index of "**Aktueller Stand:**" line, if any
    end_line: int  # exclusive boundary (next section / `---` / EOF)


@dataclass
class Drift:
    section_header: str
    stand_line_idx: int
    old_line: str
    new_line: str
    changes: list[str]  # short human-readable diff descriptors


# ── progressions.md parsing ──────────────────────────────────────────────────


def _parse_sections(text: str) -> list[Section]:
    """Walk markdown, return one Section per `### Header` block."""
    lines = text.splitlines()
    sections: list[Section] = []
    current: Section | None = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if line.startswith("### "):
            if current is not None:
                current.end_line = i
                sections.append(current)
            current = Section(
                header=line[4:].strip(),
                header_line=i,
                stand_line=None,
                end_line=len(lines),
            )
            continue
        # Section break: next `## `, `--- `, or new H1/H2 — close current
        if line.startswith("## ") or stripped == "---" or line.startswith("# "):
            if current is not None:
                current.end_line = i
                sections.append(current)
                current = None
            continue
        if current is not None and current.stand_line is None:
            # First occurrence wins; later "Aktueller Stand"-mentions in long
            # sections (e.g. inside a quoted block) are ignored.
            if "**Aktueller Stand:**" in line:
                current.stand_line = i

    if current is not None:
        sections.append(current)

    return sections


def _section_mapping_key(header: str, mapping: dict) -> str | None:
    """Map a markdown section header to a mapping_key via alias normalisation.

    Strips parentheticals so "Pinch Grip Plates (Hantelscheiben)" matches
    the same alias as the plain "Pinch Grip Plates" exercise line.
    """
    cleaned = re.sub(r"\s*\([^)]*\)", "", header).strip()
    normalised = normalise_exercise_name(cleaned)
    return match_to_mapping_key(normalised, mapping)


# ── diff & rewrite ───────────────────────────────────────────────────────────


def _has_range(text: str, value: float, kind: str) -> bool:
    """Check if the line specifies a numeric range covering `value`.

    kind: "reps" → matches `8–10`, `8-10`. "duration" → `20–30s`, `30-45s`.
    "weight" → `8–10 kg`. Returns True if value is within the range.
    """
    if kind == "weight":
        pattern = r"(\d+(?:\.\d+)?)\s*[–\-]\s*(\d+(?:\.\d+)?)\s*kg"
    elif kind == "duration":
        pattern = r"(\d+(?:\.\d+)?)\s*[–\-]\s*(\d+(?:\.\d+)?)\s*(?:s(?:ec)?|min)"
    else:  # reps
        pattern = r"\d+\s*[x×]\s*(\d+(?:\.\d+)?)\s*[–\-]\s*(\d+(?:\.\d+)?)"
    for m in re.finditer(pattern, text):
        try:
            lo, hi = float(m.group(1)), float(m.group(2))
        except (ValueError, IndexError):
            continue
        if lo <= value <= hi:
            return True
    return False


def _format_num(x: float) -> str:
    """Pretty-print numerics: 5.0 → "5", 4.5 → "4.5"."""
    if x == int(x):
        return str(int(x))
    return f"{x:g}"


def _replace_weight(line: str, weight_kg: float) -> str:
    pattern = re.compile(r"\d+(?:\.\d+)?\s*kg")
    return pattern.sub(f"{_format_num(weight_kg)} kg", line, count=1)


# Pattern matches an isometric hold-time annotation in the stand-line.
# Captures: "2s Hold", "3 s Hold am Druckpunkt", "Hold 5s", "halten für 7s".
# Used by _replace_hold to swap the numeric value in-place without disturbing
# the surrounding text (e.g. "am Druckpunkt" qualifier stays).
_HOLD_REPLACE_RE = re.compile(
    r"(?P<pre>\b)(?P<num>\d+(?:[.,]\d+)?)(?P<mid>\s*s(?:ek|ec)?\s*[-\s]?\s*)(?P<word>hold|hal[bt]|halten)\b",
    re.IGNORECASE,
)
_HOLD_REVERSE_RE = re.compile(
    r"\b(?P<word>hold|halten|halt|halte)\s+(?:für\s+|von\s+)?(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>s(?:ek|ec)?)\b",
    re.IGNORECASE,
)


def _replace_hold(line: str, hold_s: float) -> str:
    """Replace the isometric hold-time in the stand-line with a new value.

    Returns the line with the FIRST hold-time occurrence updated. Preserves the
    rest of the line (qualifier text like "am Druckpunkt", surrounding notes).
    If no hold-pattern matches, returns the line unchanged — the caller already
    decided a drift exists, so this would be a parser/formatter mismatch worth
    surfacing rather than silently appending.
    """
    new_num = _format_num(hold_s)
    if _HOLD_REPLACE_RE.search(line):
        return _HOLD_REPLACE_RE.sub(
            lambda m: f"{m.group('pre')}{new_num}{m.group('mid')}{m.group('word')}",
            line, count=1,
        )
    if _HOLD_REVERSE_RE.search(line):
        return _HOLD_REVERSE_RE.sub(
            lambda m: f"{m.group('word')} {new_num}{m.group('unit') or 's'}",
            line, count=1,
        )
    return line


def _replace_sets_reps_or_duration(
    line: str,
    sets: int | None,
    reps: float | None,
    duration_s: float | None,
) -> str:
    if sets is None:
        return line
    # Build the replacement pattern
    if duration_s is not None:
        if duration_s >= 60 and duration_s % 60 == 0:
            unit_val = duration_s / 60.0
            unit = "min"
        else:
            unit_val = duration_s
            unit = "s"
        target = f"{sets}×{_format_num(unit_val)}{unit}"
    elif reps is not None:
        target = f"{sets}×{_format_num(reps)}"
    else:
        return line
    # First "N×M[unit]" pattern, possibly with a range — replace the entire token.
    # Whitespace before an optional unit is only consumed when the unit actually
    # follows; otherwise we'd swallow the space between "3×8" and the next word.
    pattern = re.compile(
        r"\d+\s*[x×]\s*\d+(?:\.\d+)?(?:\s*(?:s(?:ec)?|min))?(?:\s*[–\-]\s*\d+(?:\.\d+)?(?:\s*(?:s(?:ec)?|min))?)?",
        re.IGNORECASE,
    )
    return pattern.sub(target, line, count=1)


def _stamp_date(line: str, date_de: str, activity_id: str) -> str:
    """Update or append `(DD.MM.YYYY, iNNNNNN, Athlet-Edit)`.

    Replaces a trailing parenthetical with a German-format date if present;
    otherwise appends a new one.
    """
    stamp = f"({date_de}, {activity_id}, Athlet-Edit)"
    trailing_de = re.compile(r"\s*\(\d{2}\.\d{2}\.\d{4}[^)]*\)\s*$")
    trailing_iso = re.compile(r"\s*\(\d{4}-\d{2}-\d{2}[^)]*\)\s*$")
    if trailing_de.search(line):
        return trailing_de.sub(f" {stamp}", line).rstrip()
    if trailing_iso.search(line):
        return trailing_iso.sub(f" {stamp}", line).rstrip()
    return line.rstrip() + f" {stamp}"


def _compute_drift(
    old: ParsedExercise | None,
    new: ParsedExercise,
    stand_line: str,
) -> tuple[list[str], dict[str, bool]]:
    """Return (human-readable change list, fields-to-rewrite flags).

    Ranges in the original line (e.g. "3×8–10", "30–45s") absorb the new
    value if it falls within them — no drift reported. This protects
    intentional progression bands from collapsing to a single point.
    """
    changes: list[str] = []
    flags = {"weight": False, "sets_reps_duration": False, "hold": False}

    # Weight
    if new.weight_kg is not None:
        old_w = old.weight_kg if old else None
        if old_w is None:
            # Stand-line has no weight (bodyweight section?) → don't inject
            pass
        elif abs(new.weight_kg - old_w) > WEIGHT_EPS:
            if _has_range(stand_line, new.weight_kg, "weight"):
                pass  # within documented range
            else:
                changes.append(
                    f"Last: {_format_num(old_w)} kg → {_format_num(new.weight_kg)} kg"
                )
                flags["weight"] = True

    # Duration (timed exercises) — checked before reps; an exercise is timed XOR rep-based
    if new.duration_s is not None:
        old_d = old.duration_s if old else None
        if old_d is not None and abs(new.duration_s - old_d) > DURATION_EPS:
            if _has_range(stand_line, new.duration_s, "duration"):
                pass
            else:
                changes.append(
                    f"Dauer: {_format_num(old_d)}s → {_format_num(new.duration_s)}s"
                )
                flags["sets_reps_duration"] = True
        # Sets too?
        if new.sets is not None and old is not None and old.sets is not None:
            if new.sets != old.sets:
                changes.append(f"Sätze: {old.sets} → {new.sets}")
                flags["sets_reps_duration"] = True

    # Reps (only when not timed)
    elif new.reps is not None:
        old_r = old.reps if old else None
        old_s = old.sets if old else None
        if old_r is not None and abs(new.reps - old_r) > 0.5:
            if _has_range(stand_line, new.reps, "reps"):
                pass
            else:
                changes.append(
                    f"Wdh: {_format_num(old_r)} → {_format_num(new.reps)}"
                )
                flags["sets_reps_duration"] = True
        if new.sets is not None and old_s is not None and new.sets != old_s:
            changes.append(f"Sätze: {old_s} → {new.sets}")
            flags["sets_reps_duration"] = True

    # Isometric Hold-time (independent of sets/reps/duration — describes the
    # TUT progression axis for grip/core/stabi exercises like Gripmaster
    # Fingers, McGill Curl-up, Bird Dog Hold). Without this check, a stand-line
    # like "3×20 Wdh, 2s Hold" survives unchanged when the athlete progresses
    # to 3s Hold — the classic TUT-progression drift pattern.
    if new.hold_s is not None:
        old_h = old.hold_s if old else None
        if old_h is None:
            # Stand-line has no hold-token (parser couldn't extract or section
            # genuinely doesn't track hold) — don't inject one out of nowhere
            pass
        elif abs(new.hold_s - old_h) >= 0.5:
            if _has_range(stand_line, new.hold_s, "duration"):
                pass
            else:
                changes.append(
                    f"Hold: {_format_num(old_h)}s → {_format_num(new.hold_s)}s"
                )
                flags["hold"] = True

    return changes, flags


def _aggregate_per_exercise(
    parsed: list[ParsedExercise],
    mapping: dict,
) -> dict[str, ParsedExercise]:
    """Reduce multiple lines for the same exercise to one canonical entry.

    When an exercise appears more than once in the description, the **last**
    occurrence wins — closest to the athlete's most recent edit.
    """
    by_key: dict[str, ParsedExercise] = {}
    for pe in parsed:
        if not pe.name:
            continue
        key = match_to_mapping_key(pe.name, mapping)
        if key is None:
            continue
        by_key[key] = pe
    return by_key


def compute_drifts(
    description: str,
    progressions_text: str,
    mapping: dict,
    activity_id: str,
    activity_date: str,
) -> tuple[list[Drift], list[str], list[str]]:
    """Compute drifts, return (drifts, skipped_with_no_mapping, skipped_other).

    `activity_date` is ISO (YYYY-MM-DD); used to stamp the new line in
    German DD.MM.YYYY format to stay consistent with existing entries.
    """
    sections = _parse_sections(progressions_text)
    section_by_key: dict[str, Section] = {}
    for sec in sections:
        if sec.stand_line is None:
            continue
        mk = _section_mapping_key(sec.header, mapping)
        if mk and mk not in section_by_key:
            section_by_key[mk] = sec

    parsed_exercises, _unmapped_raw = parse_description(description)
    aggregated = _aggregate_per_exercise(parsed_exercises, mapping)

    # Map of unmapped names (parsed but not in exercise_muscle_mapping.json)
    unmapped_names: list[str] = []
    for pe in parsed_exercises:
        if not pe.name:
            continue
        if match_to_mapping_key(pe.name, mapping) is None:
            if pe.name not in unmapped_names:
                unmapped_names.append(pe.name)

    # Format activity date as DD.MM.YYYY
    try:
        y, m, d = activity_date.split("-")
        date_de = f"{d}.{m}.{y}"
    except ValueError:
        date_de = date_cls.today().strftime("%d.%m.%Y")

    drifts: list[Drift] = []
    skipped_no_section: list[str] = []  # known mapping but no section in progressions.md

    progressions_lines = progressions_text.splitlines()

    for key, new_pe in aggregated.items():
        sec = section_by_key.get(key)
        if sec is None:
            skipped_no_section.append(key)
            continue
        old_line = progressions_lines[sec.stand_line]
        # Parse the existing stand-line as an exercise line. The parser
        # tolerates noise (free-form annotations); only the numeric fields
        # matter for diff purposes.
        old_pe = parse_line(old_line)
        if old_pe is None or not old_pe.parse_ok:
            # Couldn't parse the existing line — skip rather than guess
            continue

        changes, flags = _compute_drift(old_pe, new_pe, old_line)
        if not changes:
            continue

        new_line = old_line
        if flags["sets_reps_duration"]:
            new_line = _replace_sets_reps_or_duration(
                new_line, new_pe.sets, new_pe.reps, new_pe.duration_s
            )
        if flags["weight"]:
            new_line = _replace_weight(new_line, new_pe.weight_kg)  # type: ignore[arg-type]
        if flags["hold"]:
            new_line = _replace_hold(new_line, new_pe.hold_s)  # type: ignore[arg-type]
        new_line = _stamp_date(new_line, date_de, activity_id)

        if new_line == old_line:
            continue

        drifts.append(
            Drift(
                section_header=sec.header,
                stand_line_idx=sec.stand_line,
                old_line=old_line,
                new_line=new_line,
                changes=changes,
            )
        )

    return drifts, skipped_no_section, unmapped_names


# ── file IO ──────────────────────────────────────────────────────────────────


def _apply_drifts(text: str, drifts: list[Drift]) -> str:
    lines = text.splitlines(keepends=True)
    for d in drifts:
        line_ending = "\n"
        original = lines[d.stand_line_idx]
        if original.endswith("\r\n"):
            line_ending = "\r\n"
        lines[d.stand_line_idx] = d.new_line + line_ending
    return "".join(lines)


def _load_mapping() -> dict:
    with open(resolve_config("exercise_muscle_mapping.json")) as f:
        data = json.load(f)
    data.pop("_meta", None)
    return data


# ── orchestration ────────────────────────────────────────────────────────────


async def _sync(activity_id: str, dry_run: bool) -> int:
    from app.api.intervals_client import IntervalsClient

    norm_id = activity_id if activity_id.startswith("i") else f"i{activity_id}"

    client = IntervalsClient()
    activity = await client.get_activity(norm_id)

    activity_type = activity.get("type", "")
    if activity_type not in STRENGTH_ACTIVITY_TYPES:
        # Silent skip — endurance sessions don't carry exercise lists
        return 0

    description = activity.get("description") or ""
    # Fallback: if activity description is empty, try the paired event
    if not description.strip():
        paired_event_id = activity.get("paired_event_id")
        if paired_event_id:
            try:
                ev = await client.get_event(str(paired_event_id))
                description = ev.get("description") or ""
            except Exception:
                pass

    if not description.strip():
        print(f"[sync] no description on {norm_id} — nothing to compare")
        return 0

    if not PROGRESSIONS_PATH.exists():
        print(f"[sync] {PROGRESSIONS_PATH} not found — skipped")
        return 0

    progressions_text = PROGRESSIONS_PATH.read_text(encoding="utf-8")
    mapping = _load_mapping()
    activity_date = (activity.get("start_date_local") or "")[:10] or date_cls.today().isoformat()

    drifts, skipped_no_section, unmapped_names = compute_drifts(
        description=description,
        progressions_text=progressions_text,
        mapping=mapping,
        activity_id=norm_id,
        activity_date=activity_date,
    )

    if not drifts and not unmapped_names and not skipped_no_section:
        print(f"[sync] {norm_id} — no description drift detected")
        return 0

    if drifts:
        verb = "would update" if dry_run else "updates"
        print(f"[sync] config/exercise_progressions.md {verb}:")
        for d in drifts:
            print(f"  - {d.section_header}: {', '.join(d.changes)}")

    if skipped_no_section:
        print(f"[sync] mapped but no progressions section: {', '.join(skipped_no_section)}")

    if unmapped_names:
        print(f"[sync] unmapped (skipped): {', '.join(unmapped_names)}")

    if drifts and not dry_run:
        new_text = _apply_drifts(progressions_text, drifts)
        PROGRESSIONS_PATH.write_text(new_text, encoding="utf-8")
        print(f"[sync] wrote {PROGRESSIONS_PATH}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync athlete-edited workout description back into config/exercise_progressions.md",
    )
    parser.add_argument("--activity-id", required=True, help="Activity-ID (e.g. i12345678)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print drift report without modifying config/exercise_progressions.md",
    )
    args = parser.parse_args()
    asyncio.run(_sync(args.activity_id, args.dry_run))


if __name__ == "__main__":
    main()
