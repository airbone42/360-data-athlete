"""Port of n8n 'Parse Workout' and 'Split Workouts' JS nodes."""

from __future__ import annotations

import logging
import re

from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Matches time patterns that intervals.icu parses as workout step durations.
# Used only to strip from non-endurance descriptions where step durations are controlled
# via workout_doc.steps instead.
_ICU_TIME_RE = re.compile(r"\d+\s*(?:Minuten|Sekunden|Min\.?|Sek\.?|minutes?|seconds?|min|m|s)\b")

# intervals.icu only renders \n\n as visible line breaks, not single \n.
# This re normalizes single newlines to double newlines in non-endurance descriptions.
_SINGLE_NEWLINE_RE = re.compile(r"(?<!\n)\n(?!\n)")

# Detects ambiguous "X rounds / X Runden" + "Yx" set notation in the same
# description block. e.g. "2 rounds" combined with "3x8" implies 6 total sets
# — likely unintended. Bilingual: German "Runden" + English "rounds".
_RUNDEN_RE = re.compile(r"\b\d+\s*(?:[Rr]unden|[Rr]ounds?)\b")
_SETS_RE = re.compile(r"\b\d+\s*[x×]\s*\d+")
# Detects static stretch durations > 30s, e.g. "45s/side", "60s", "2x45s".
# Keywords are bilingual to detect stretches written in German or English.
_STRETCH_KEYWORDS_RE = re.compile(
    r"\b(?:stretch|stretching|dehnen|dehnung|hip stretch|piriformis|figure.4|taubenpose|kindhaltung"
    r"|hüftbeuger|hip flexor|foamroller|foam roller|mobilisation|mobility|child[\s-]?pose|pigeon)\b",
    re.IGNORECASE,
)
_STRETCH_DURATION_RE = re.compile(r"\b([4-9]\d|[1-9]\d{2,})\s*s\b")  # ≥40s

VALID_TYPES = ["Run", "Ride", "WeightTraining", "Workout"]
REQUIRED_FIELDS = ["type", "name", "duration_min", "workout_type"]
VALID_TAGS: set[str] = {
    "run", "ride", "core", "legs", "plyo", "balance", "mobility",
    "intervals", "ninja", "grip", "upperbody",
    # Legacy tag — accepted on read for backward-compat with historic
    # intervals.icu data; new plans must emit "legs". Remove once all
    # historic sessions have been migrated.
    "beine",
}

REST_DAY = {
    "type": "Workout",
    "name": "Rest day 🛋️",
    "duration_min": 0,
    "intensity": "low",
    "workout_type": "RECOVERY",
    "indoor": True,
    "structure": [],
}


def parse_workouts(llm_output: dict | list) -> tuple[str, list[dict]]:
    """Parse and validate LLM JSON output. Returns (coaching_notes, workouts)."""
    coaching_notes = ""
    if isinstance(llm_output, list):
        workouts = llm_output
    elif isinstance(llm_output, dict):
        if "workouts" in llm_output:
            coaching_notes = llm_output.get("coaching_notes") or ""
            raw_workouts = llm_output["workouts"]
            workouts = raw_workouts if isinstance(raw_workouts, list) else [raw_workouts]
        elif "data" in llm_output and isinstance(llm_output["data"], list):
            workouts = llm_output["data"]
        else:
            workouts = [llm_output]
    else:
        workouts = [llm_output]

    if not workouts:
        workouts = [REST_DAY.copy()]

    result = []
    for i, w in enumerate(workouts):
        missing = [f for f in REQUIRED_FIELDS if f not in w or w[f] is None]
        if missing:
            raise ValueError(
                f"❌ Workout {i + 1} incomplete. Missing fields: {', '.join(missing)}"
            )
        if w["type"] not in VALID_TYPES:
            raise ValueError(
                f"❌ Workout {i + 1}: invalid type \"{w['type']}\". "
                f"Allowed: {', '.join(VALID_TYPES)}"
            )
        # Normalize: if structure was passed as a plain string, move it to description
        if isinstance(w.get("structure"), str):
            w = {**w, "description": w["structure"], "structure": []}
        structure_text = _structure_to_text(w.get("structure") or []) or w.get("description", "")
        raw_tags = [str(t).lower() for t in (w.get("tags") or [])]
        filtered_tags = [t for t in raw_tags if t in VALID_TAGS]
        dropped = [t for t in raw_tags if t not in VALID_TAGS]
        if dropped:
            logger.warning("Workout %d '%s': tags dropped %s", i + 1, w.get("name"), dropped)
        _validate_structure(w, i + 1)
        _lint_intervals_icu(w, i + 1)
        result.append({**w, "tags": filtered_tags, "structureText": structure_text, "index": i + 1})

    return coaching_notes, result


def _validate_structure(w: dict, index: int) -> None:
    """Detect common LLM formatting errors before pushing to intervals.icu."""
    structure = w.get("structure") or []
    if not isinstance(structure, list):
        return  # string/other — treated as description elsewhere, skip validation
    for step in structure:
        desc = step.get("description") or ""
        # "X rounds / Runden" + "Yx" sets in same block → ambiguous total volume
        if _RUNDEN_RE.search(desc) and _SETS_RE.search(desc):
            runden = _RUNDEN_RE.search(desc).group()
            raise ValueError(
                f"❌ Workout {index} '{w.get('name')}', step '{step.get('step')}': "
                f"conflict '{runden}' + set notation (e.g. '3x8') — "
                f"use either 'rounds' OR per-exercise 'sets', not both. "
                f"Correct the structure before pushing."
            )
        # Static stretch duration > 30s violates the athlete-preference cap
        if _STRETCH_KEYWORDS_RE.search(desc):
            bad = _STRETCH_DURATION_RE.search(desc)
            if bad:
                raise ValueError(
                    f"❌ Workout {index} '{w.get('name')}', step '{step.get('step')}': "
                    f"stretch hold time {bad.group()} exceeds the 30s maximum. "
                    f"Shorten to 30s."
                )


def _lint_intervals_icu(w: dict, index: int) -> None:
    """Warn on intervals_icu format violations (non-blocking)."""
    icu_text = w.get("intervals_icu") or ""
    if not icu_text:
        return
    from app.utils.intervals_icu_linter import validate_intervals_icu
    violations = validate_intervals_icu(icu_text)
    for v in violations:
        logger.warning("Workout %d '%s': intervals_icu — %s", index, w.get("name"), v)


def _sort_key(w: dict) -> int:
    """Kraft/Plyo vor Lauf/Ride."""
    if w.get("type") in ("WeightTraining", "Workout"):
        return 0
    return 1


_STRENGTH_TYPES = {"WeightTraining", "Workout"}
_ENDURANCE_TYPES = {"Run", "Ride"}
# Bilingual leg-tag synonyms ("beine" = legacy German, "legs" = new canonical).
_LEG_TAGS = {"beine", "legs", "plyo"}


def _interference_gap_min(prev: dict, curr: dict) -> int:
    """Minimum gap in minutes between two workouts (interference rule).

    WeightTraining/Workout → Run/Ride:
      - leg-focused (legs/beine/plyo tags): 360 min (6h)
      - other: 180 min (3h)
    All other transitions: 120 min (2h default).
    """
    if prev.get("type") in _STRENGTH_TYPES and curr.get("type") in _ENDURANCE_TYPES:
        prev_tags = set(str(t).lower() for t in (prev.get("tags") or []))
        if prev_tags & _LEG_TAGS:
            return 360
        return 180
    return 120


def prepare_workout_events(workouts: list[dict], date: str) -> list[dict]:
    """Convert parsed workouts to intervals.icu event format (port of 'Split Workouts').

    Calls the intervals_icu linter on each workout so format issues land in the
    push log even when the upstream `parse_workouts()` (which also lints) was
    skipped. The Refactor von 04d56f5 hat parse_workouts und prepare_workout_events
    getrennt — push_workouts.py ruft nur letztere, also musste der Linter hier
    rein, sonst rottet er als toter Code.
    """
    sorted_workouts = sorted(workouts, key=_sort_key)
    for i, w in enumerate(sorted_workouts):
        _lint_intervals_icu(w, i + 1)
    events = []
    start_minutes = 6 * 60  # first workout always at 06:00
    prev_start_minutes = start_minutes
    for i, w in enumerate(sorted_workouts):
        if i > 0:
            prev = sorted_workouts[i - 1]
            gap = _interference_gap_min(prev, w)
            start_minutes = prev_start_minutes + prev.get("duration_min", 0) + gap
        prev_start_minutes = start_minutes
        start_time = f"{start_minutes // 60:02d}:{start_minutes % 60:02d}:00"

        # Normalize: if structure was passed as a plain string, move it to description
        if isinstance(w.get("structure"), str):
            w = {**w, "description": w["structure"], "structure": []}
        _validate_structure(w, i + 1)
        structure_text = _structure_to_text(w.get("structure") or [])
        if not structure_text:
            structure_text = w.get("structureText") or w.get("description") or w.get("coaching_notes") or ""
        # For Run/Ride: use intervals_icu text as description so intervals.icu can parse it for Garmin sync.
        # Fall back to human-readable structure_text if no intervals_icu text available.
        is_endurance = w.get("type") in ("Run", "Ride")
        intervals_icu = w.get("intervals_icu") or ""
        extra: dict = {}
        if is_endurance:
            description = (intervals_icu or structure_text) or ""
            # Same defensive locales=[] for endurance — protects against a
            # future heuristic change on intervals.icu mis-flagging the
            # German description / intervals_icu text. The server still
            # parses our intervals_icu syntax to build the steps; we just
            # override the locales hint.
            extra["workout_doc"] = {"locales": []}
        else:
            structure = w.get("structure") or []
            if structure:
                # Build explicit workout_doc so intervals.icu uses our step durations
                # instead of parsing time patterns from the description text.
                total_secs = sum(s.get("duration_min", 0) * 60 for s in structure)
                doc_steps = [
                    {
                        # Human-readable text with time annotations (athlete-facing)
                        "text": _structure_to_text([s]),
                        "duration": s.get("duration_min", 0) * 60,
                    }
                    for s in structure
                ]
                extra["workout_doc"] = {
                    "steps": doc_steps,
                    "duration": total_secs,
                    # Explicit empty locales — without this the intervals.icu
                    # server runs its own language-detection heuristic on the
                    # description text and sometimes mis-flags German workouts
                    # as Japanese ("ja") when the text contains onomatopoeia
                    # like 'Tss!' or other ambiguous tokens. A non-empty locales
                    # tag causes the intervals.icu UI to render some labels in
                    # that language, which looks like random CJK characters to
                    # a German-language athlete.
                    "locales": [],
                }
                # Human-readable description with time annotations (30s, 45s etc.).
                # intervals.icu respects the explicit workout_doc over description parsing
                # when both are sent, so time patterns here don't corrupt the duration.
                description = _structure_to_text(structure)
            else:
                description = structure_text or ""
                # No explicit structure → still send an empty workout_doc with
                # locales=[] to suppress the server-side language-detection
                # heuristic (same rationale as above).
                extra["workout_doc"] = {
                    "steps": [],
                    "duration": 0,
                    "locales": [],
                }
            description = _normalize_newlines(description)
        events.append(
            {
                "uid": f"coach-{date}-{i}",
                "category": "WORKOUT",
                "start_date_local": f"{date}T{start_time}",
                "name": w["name"],
                "description": description,
                "type": w["type"],
                "moving_time": w["duration_min"] * 60,
                "indoor": w.get("indoor", False),
                "workout_type": w.get("workout_type", "EASY"),
                "intensity": w.get("intensity", "low"),
                "tags": w.get("tags", []),
                **extra,
            }
        )
    return events


def _structure_to_icu_description(structure: list[dict]) -> str:
    """Format structure WITHOUT time annotations for intervals.icu.

    intervals.icu parses (X min) patterns in description as workout steps,
    which causes incorrect displayed duration for non-endurance events.
    This function emits only section headings + exercise detail lines.
    """
    lines = []
    for s in structure:
        step = s.get("step", "")
        lines.append(step)
        exercises = s.get("exercises")
        if exercises:
            for ex in exercises:
                name = ex.get("name", "?")
                sets = ex.get("sets")
                reps = ex.get("reps")
                per_side = ex.get("per_side", False)
                weight = ex.get("weight_kg")
                dur_s = ex.get("duration_s")
                rpe = ex.get("rpe_target")
                notes = ex.get("notes", "")
                parts = []
                if sets:
                    parts.append(f"{sets}x")
                if reps:
                    parts.append(f"{reps} Wdh je Seite" if per_side else f"{reps} Wdh")
                elif dur_s:
                    parts.append(f"{dur_s} Sek.")
                if weight:
                    parts.append(f"{weight}kg")
                if rpe:
                    parts.append(f"RPE~{rpe}")
                detail = " ".join(parts)
                ex_line = f"  - {name}: {detail}"
                if notes:
                    clean_notes = _ICU_TIME_RE.sub('', notes).strip()
                    if clean_notes:
                        ex_line += f" ({clean_notes})"
                lines.append(ex_line)
        elif s.get("description"):
            clean = _ICU_TIME_RE.sub('', s['description']).strip()
            if clean:
                lines.append(f"  {clean}")
    return "\n".join(lines)


def _normalize_newlines(text: str) -> str:
    """Ensure all line breaks in non-endurance descriptions are double newlines.

    intervals.icu only renders \\n\\n as visible line breaks; single \\n is ignored
    and causes all exercises to run together in a single block.
    """
    return _SINGLE_NEWLINE_RE.sub("\n\n", text).strip()


def _structure_to_text(structure: list[dict]) -> str:
    lines = []
    for s in structure:
        step = s.get("step", "")
        dur = s.get("duration_min", "?")
        desc = s.get("description", "")
        line = f"{step} ({dur} min): {desc}"
        exercises = s.get("exercises")
        if exercises:
            for ex in exercises:
                name = ex.get("name", "?")
                sets = ex.get("sets")
                reps = ex.get("reps")
                per_side = ex.get("per_side", False)
                weight = ex.get("weight_kg")
                dur_s = ex.get("duration_s")
                rpe = ex.get("rpe_target")
                notes = ex.get("notes", "")
                parts = []
                if sets:
                    parts.append(f"{sets}x")
                if reps:
                    parts.append(f"{reps} Wdh je Seite" if per_side else f"{reps} Wdh")
                elif dur_s:
                    parts.append(f"{dur_s} Sek.")
                if weight:
                    parts.append(f"{weight}kg")
                if rpe:
                    parts.append(f"RPE~{rpe}")
                detail = " ".join(parts)
                ex_line = f"  - {name}: {detail}"
                if notes:
                    ex_line += f" ({notes})"
                line += f"\n{ex_line}"
        lines.append(line)
    return "\n".join(lines)
