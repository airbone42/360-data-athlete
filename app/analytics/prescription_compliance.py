"""Execution tracking for standing prescriptions, at exercise granularity.

The complementary due-warnings in `context_builder` work on **activity
tags**: they answer "when did a `core` session last happen?". A prescription
that lives as one exercise *inside* another block is invisible to them — the
session runs, the tag is satisfied, and the missing element leaves no trace.
That gap is not hypothetical: a prescribed lift was dropped from three
consecutive sessions, each time for a same-day reason, and nothing surfaced
it because the block it belonged to had run every time.

This module closes it by comparing declared prescriptions against what was
actually executed:

- **Declaration** — an exercise entry in `exercise_progressions.md` carries a
  `**Soll-Frequenz:**` line (`täglich`, `alle 2 Tage`, `2x/Woche`, …). Only
  entries that declare one are tracked; everything else is ignored, so the
  check stays opt-in per exercise.
- **Execution** — the muscle logs under `data/muscles/*.json` record the
  exercises actually parsed out of each completed session. That is a real
  execution log and needs no extra bookkeeping from the athlete.

The output is advisory. It never blocks a plan; it makes a silent omission
loud enough to be a decision.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from app.utils.paths import DATA_DIR

# `### Exercise name` or `#### Exercise name` — the heading a prescription
# block hangs under. Level is not meaningful here, only the title.
_HEADING_RE = re.compile(r"^#{3,4}\s+(.+?)\s*$")
# `- **Soll-Frequenz:** 2x/Woche` — bold or plain, German or English key.
_FREQ_RE = re.compile(
    r"\*\*(?:Soll-Frequenz|Soll-Frequenz)\s*:?\*\*\s*(.+?)\s*$"
    r"|^\s*-?\s*(?:Soll-Frequenz)\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)


# Umlauts reach this code in both spellings: workout descriptions are
# sometimes written with real umlauts and sometimes transliterated to the
# ASCII digraph. Folding to the digraph makes "Rücken" and "Ruecken" the same
# token; naive accent-stripping would produce "rucken" vs "ruecken" and miss.
_UMLAUT_FOLD = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "ae", "Ö": "oe", "Ü": "ue", "ß": "ss"}
)


def _normalise(text: str) -> str:
    """Lowercase, fold umlauts and collapse punctuation for loose matching."""
    out = text.lower().translate(_UMLAUT_FOLD)
    out = "".join(
        c for c in unicodedata.normalize("NFKD", out) if not unicodedata.combining(c)
    )
    out = re.sub(r"[^a-z0-9]+", " ", out)
    return " ".join(out.split())


def parse_frequency(raw: str) -> int | None:
    """Translate a prescription cadence into a maximum tolerated gap in days.

    Returns None when the text cannot be read, so an unparseable declaration
    is skipped rather than silently treated as satisfied.
    """
    text = _normalise(raw)
    if not text:
        return None

    # `_normalise` folds umlauts to digraphs, so "täglich" arrives as
    # "taeglich". Both spellings are accepted so a hand-edited config that
    # already used the ASCII form still parses.
    if any(k in text for k in ("taeglich", "taglich", "daily", "jeden tag")):
        return 1

    # "alle 2 tage" / "every 2 days"
    m = re.search(r"(?:alle|every)\s+(\d+)\s*(?:tage?|days?)", text)
    if m:
        return max(1, int(m.group(1)))

    # "2x/woche", "2 x pro woche", "3x per week"
    m = re.search(r"(\d+)\s*(?:x|mal)\s*(?:/|pro|per|in der|a)?\s*(?:woche|week)", text)
    if m:
        per_week = max(1, int(m.group(1)))
        # A 2x/week prescription may legitimately sit 3-4 days apart. Allow the
        # even spacing rounded up, plus a day of slack, so ordinary scheduling
        # jitter does not raise a finding.
        return math.ceil(7 / per_week) + 1

    # "1x/woche" is handled above; this catches the bare adverb.
    if any(k in text for k in ("woechentlich", "wochentlich", "weekly")):
        return 8
    return None


def parse_prescriptions(progressions_md: str) -> list[dict]:
    """Extract `{name, raw_frequency, max_gap_days}` for every declaring entry."""
    out: list[dict] = []
    current: str | None = None
    for line in progressions_md.splitlines():
        heading = _HEADING_RE.match(line)
        if heading:
            current = heading.group(1).strip()
            # Headings carry documentation alongside the name: a trailing
            # parenthetical qualifier ("(Kernlift-Option A)") and everything
            # after a dash separator ("— Physio-Protokoll ab …"). Both would
            # wreck the match against the logged exercise name, which only
            # ever contains the exercise itself.
            current = re.split(r"\s+[—–]\s+", current)[0].strip()
            current = re.sub(r"\s*\([^)]*\)\s*$", "", current).strip()
            continue
        if current is None:
            continue
        m = _FREQ_RE.search(line)
        if not m:
            continue
        raw = (m.group(1) or m.group(2) or "").strip()
        # Drop trailing prose after a sentence separator: the cadence is the
        # leading clause, anything after an em dash is rationale.
        raw = re.split(r"\s+[—–-]\s+", raw)[0].strip()
        gap = parse_frequency(raw)
        if gap is None:
            continue
        out.append({"name": current, "raw_frequency": raw, "max_gap_days": gap})
        current = None  # one declaration per entry
    return out


def _load_executions(today: date, lookback_days: int) -> dict[str, date]:
    """Map normalised exercise name → most recent execution date."""
    muscles_dir = Path(DATA_DIR) / "muscles"
    seen: dict[str, date] = {}
    if not muscles_dir.is_dir():
        return seen
    cutoff = today - timedelta(days=lookback_days)
    for path in sorted(muscles_dir.glob("*.json")):
        stem = path.stem
        try:
            day = date.fromisoformat(stem)
        except ValueError:
            continue  # _e1rm_state.json and friends
        if day < cutoff or day > today:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for session in payload.get("sessions") or []:
            for ex in session.get("exercises") or []:
                # Index the coach-written name ONLY, never the mapping key.
                # Mapping keys deliberately collapse variants for muscle-load
                # purposes — a single-leg glute bridge and a single-leg hip
                # thrust share `hip_thrust`. Treating that as identity marks a
                # never-executed prescription as satisfied, which is the one
                # failure this checker must not have.
                name = ex.get("name")
                if not name:
                    continue
                norm = _normalise(str(name))
                if not norm:
                    continue
                if norm not in seen or seen[norm] < day:
                    seen[norm] = day
    return seen


def _match_execution(name: str, executions: dict[str, date]) -> date | None:
    """Find the latest execution whose logged name plausibly is this exercise.

    Logged names carry the coach's phrasing from the workout description
    ("Side Plank mit Hüft-Abduktion"), so an exact match is the exception.
    Substring containment in either direction is the workable rule; on a tie
    the most recent date wins.
    """
    target = _normalise(name)
    if not target:
        return None
    best: date | None = None
    for logged, day in executions.items():
        if target in logged or logged in target:
            if best is None or day > best:
                best = day
    return best


def compute_prescription_compliance(
    progressions_md: str,
    today: date,
    lookback_days: int = 60,
) -> list[dict]:
    """Return one finding per prescription that is overdue or never executed."""
    prescriptions = parse_prescriptions(progressions_md)
    if not prescriptions:
        return []
    executions = _load_executions(today, lookback_days)

    findings: list[dict] = []
    for p in prescriptions:
        last = _match_execution(p["name"], executions)
        if last is None:
            findings.append(
                {
                    "exercise": p["name"],
                    "frequency": p["raw_frequency"],
                    "max_gap_days": p["max_gap_days"],
                    "last_execution": None,
                    "days_since": None,
                    "status": "never",
                }
            )
            continue
        days_since = (today - last).days
        if days_since > p["max_gap_days"]:
            findings.append(
                {
                    "exercise": p["name"],
                    "frequency": p["raw_frequency"],
                    "max_gap_days": p["max_gap_days"],
                    "last_execution": last.isoformat(),
                    "days_since": days_since,
                    "status": "overdue",
                }
            )
    return findings


def format_findings(findings: list[dict], lookback_days: int = 60) -> str | None:
    """Render findings as a planningConstraints block, or None when clean."""
    if not findings:
        return None
    lines = [
        "Prescription compliance (per exercise, from the muscle logs — "
        "these are NOT covered by the tag-level due-warnings above):"
    ]
    for f in findings:
        if f["status"] == "never":
            lines.append(
                f"🔴 {f['exercise']} — prescribed {f['frequency']}, "
                f"NEVER executed in the last {lookback_days}d. "
                "If it is being deferred, name the replacement slot."
            )
        else:
            lines.append(
                f"🔴 {f['exercise']} — prescribed {f['frequency']}, "
                f"last executed {f['last_execution']} ({f['days_since']}d ago, "
                f"tolerated gap {f['max_gap_days']}d)."
            )
    lines.append(
        "→ Dropping one of these again needs a named replacement slot, not "
        "just a same-day reason. Three same-day reasons in a row are a "
        "silently dropped prescription."
    )
    return "\n".join(lines)
