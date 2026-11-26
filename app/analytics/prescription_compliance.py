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
- **Execution** — the completed activities themselves: the session name, and
  for strength sessions the exercises `exercise_parser` reads out of the
  activity description. That is a real execution log and needs no extra
  bookkeeping from the athlete.

Two optional fields widen what counts as an execution, for prescriptions
whose parts are logged under other names than the prescription itself:

- ``**Zählt als Ausführung:**`` — comma-separated names of the parts (the
  exercises inside a block, or an alternative block name). Any of them in a
  logged exercise, a session name or — for non-endurance activities — the
  description text counts as the prescription having run.
- ``**Tags:**`` — the planned-workout tags the prescription carries (same
  vocabulary as ``covers`` in ``external_coverage.json``). A completed
  external session (therapy appointment, class, gym hall) that
  ``external_coverage.json`` says covers one of those tags — and whose
  ``workout_match`` fits the prescription name — counts as an execution on
  its day, the same rule the plan validator applies in the other direction.

The output is advisory. It never blocks a plan; it makes a silent omission
loud enough to be a decision.
"""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, timedelta

from app.utils.activity_helpers import activity_date

# Activity types whose description lists exercises. Run / ride descriptions
# are prose and intervals, parsing them would only add noise names.
STRENGTH_ACTIVITY_TYPES = frozenset({"WeightTraining", "Workout"})

# `### Exercise name` or `#### Exercise name` — the heading a prescription
# block hangs under. Level is not meaningful here, only the title.
_HEADING_RE = re.compile(r"^#{3,4}\s+(.+?)\s*$")
# `- **Soll-Frequenz:** 2x/Woche` — bold or plain, German or English key.
_ALIAS_RE = re.compile(
    r"\*\*Zählt als Ausführung\s*:?\*\*\s*(.+?)\s*$"
    r"|^\s*-?\s*Zählt als Ausführung\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)
_TAGS_RE = re.compile(
    r"\*\*Tags\s*:?\*\*\s*(.+?)\s*$" r"|^\s*-?\s*Tags\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)
# Endurance sessions carry prose and intervals; a description search for an
# alias there would match incidental mentions ("skipped the wall angels").
ENDURANCE_ACTIVITY_TYPES = frozenset({
    "Run", "VirtualRun", "TrailRun", "Ride", "VirtualRide", "GravelRide",
    "MountainBikeRide", "EBikeRide", "Swim", "OpenWaterSwim", "Walk", "Hike",
    "Rowing", "NordicSki",
})
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


def _split_list(raw: str) -> list[str]:
    """Split a comma/semicolon list; drop prose after a dash and empties."""
    raw = re.split(r"\s+[—–]\s+", raw)[0]
    return [x.strip() for x in re.split(r"[;,]", raw) if x.strip()]


def parse_prescriptions(progressions_md: str) -> list[dict]:
    """Extract one record per entry that declares a cadence.

    Each record is ``{name, raw_frequency, max_gap_days, aliases, tags}``;
    ``aliases`` (``**Zählt als Ausführung:**``) and ``tags`` (``**Tags:**``)
    are optional lists, empty when the entry does not declare them.
    """
    out: list[dict] = []
    current: dict | None = None

    def flush() -> None:
        if current is not None and current.get("max_gap_days") is not None:
            out.append(current)

    for line in progressions_md.splitlines():
        heading = _HEADING_RE.match(line)
        if heading:
            flush()
            name = heading.group(1).strip()
            # Headings carry documentation alongside the name: a trailing
            # parenthetical qualifier ("(Kernlift-Option A)") and everything
            # after a dash separator ("— Physio-Protokoll ab …"). Both would
            # wreck the match against the logged exercise name, which only
            # ever contains the exercise itself.
            name = re.split(r"\s+[—–]\s+", name)[0].strip()
            name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
            current = {
                "name": name, "raw_frequency": "", "max_gap_days": None,
                "aliases": [], "tags": [],
            }
            continue
        if current is None:
            continue
        m = _FREQ_RE.search(line)
        if m and current["max_gap_days"] is None:  # one declaration per entry
            raw = (m.group(1) or m.group(2) or "").strip()
            # Drop trailing prose after a sentence separator: the cadence is
            # the leading clause, anything after an em dash is rationale.
            raw = re.split(r"\s+[—–-]\s+", raw)[0].strip()
            gap = parse_frequency(raw)
            if gap is not None:
                current["raw_frequency"] = raw
                current["max_gap_days"] = gap
            continue
        m = _ALIAS_RE.search(line)
        if m:
            current["aliases"] += _split_list(m.group(1) or m.group(2) or "")
            continue
        m = _TAGS_RE.search(line)
        if m:
            current["tags"] += [
                t.lower() for t in _split_list(m.group(1) or m.group(2) or "")
            ]
    flush()
    return out


def _remember(index: dict[str, date], name: str, day: date) -> None:
    if name and (name not in index or index[name] < day):
        index[name] = day


def _load_logged_names(
    activities: list[dict], today: date, lookback_days: int
) -> tuple[dict[str, date], dict[str, date]]:
    """Return (exercise names, session names) → most recent execution date.

    Session names are kept apart because some prescriptions are whole blocks
    (a mobility routine, a physio protocol): the block runs as its own
    session, its parts are listed under their own names, and the block name
    never appears as an exercise. Without the session index such a block reads
    as "never executed" while it ran every other day — a false alarm that
    pushes the block into days where other sessions already cover it.

    Only the coach-written exercise name is indexed. An alias table that
    collapses variants (a single-leg glute bridge and a single-leg hip thrust
    under one key) would mark a never-executed prescription as satisfied,
    which is the one failure this checker must not have.
    """
    from app.analytics.exercise_parser import parse_description

    seen: dict[str, date] = {}
    sessions_seen: dict[str, date] = {}
    cutoff = today - timedelta(days=lookback_days)
    for activity in activities:
        try:
            day = date.fromisoformat(activity_date(activity))
        except ValueError:
            continue
        if day < cutoff or day > today:
            continue
        _remember(sessions_seen, _normalise(str(activity.get("name") or "")), day)
        if activity.get("type") not in STRENGTH_ACTIVITY_TYPES:
            continue
        parsed, _unparsed = parse_description(str(activity.get("description") or ""))
        for ex in parsed:
            norm = _normalise(ex.name or "")
            # One- and two-letter fragments would "contain" half the
            # prescriptions in the substring match below.
            if len(norm) >= 3:
                _remember(seen, norm, day)
    return seen, sessions_seen


def _match_session(name: str, sessions: dict[str, date]) -> date | None:
    """Latest session whose name *starts with* the prescribed block name.

    Prefix, not containment: "Schulter-Mobilisation + Atemübungen
    (Urlaubsfassung)" is that block, while a session that merely mentions an
    exercise somewhere in its title is not proof the exercise ran.
    """
    target = _normalise(name)
    if not target:
        return None
    best: date | None = None
    for logged, day in sessions.items():
        if logged == target or logged.startswith(target + " "):
            if best is None or day > best:
                best = day
    return best


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


def load_external_coverage() -> list[dict]:
    """Load ``config/external_coverage.json`` (missing/invalid = no coverage).

    Same file and entry shape as validator rule R042; regexes are compiled
    case-insensitive and entries with an invalid regex are dropped.
    """
    import json

    from app.utils.paths import resolve_config

    try:
        data = json.loads(resolve_config("external_coverage.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    raw = data.get("sessions") if isinstance(data, dict) else data
    out: list[dict] = []
    for e in raw if isinstance(raw, list) else []:
        if not isinstance(e, dict):
            continue
        covers = {str(c).lower() for c in e.get("covers") or [] if str(c).strip()}
        tags_any = {str(t).lower() for t in e.get("tags_any") or [] if str(t).strip()}
        match, wm = str(e.get("match") or ""), str(e.get("workout_match") or "")
        if not covers or not (match or tags_any):
            continue
        try:
            out.append({
                "covers": covers,
                "tags_any": tags_any,
                "match_re": re.compile(match, re.IGNORECASE) if match else None,
                "workout_re": re.compile(wm, re.IGNORECASE) if wm else None,
            })
        except re.error:
            continue
    return out


def _in_window(activity: dict, today: date, lookback_days: int) -> date | None:
    try:
        day = date.fromisoformat(activity_date(activity))
    except ValueError:
        return None
    if day < today - timedelta(days=lookback_days) or day > today:
        return None
    return day


def _latest_alias_execution(
    aliases: list[str], activities: list[dict], today: date, lookback_days: int
) -> date | None:
    """Latest day an activity shows one of the declared part names.

    Three places count: a parsed exercise name (substring, as for the
    prescription's own name), the session name, and — for activities that are
    not endurance sessions — the description text, so a part that is logged
    in prose ("Wall Angel, No-Wall Slide 2x8") or under a non-strength
    activity type still registers. Aliases shorter than four characters are
    ignored; they would match half the log.
    """
    from app.analytics.exercise_parser import parse_description

    targets = [t for t in (_normalise(a) for a in aliases) if len(t) >= 4]
    if not targets:
        return None
    best: date | None = None
    for activity in activities:
        day = _in_window(activity, today, lookback_days)
        if day is None or (best is not None and day <= best):
            continue
        hay = [f" {_normalise(str(activity.get('name') or ''))} "]
        description = str(activity.get("description") or "")
        if activity.get("type") in STRENGTH_ACTIVITY_TYPES:
            parsed, _ = parse_description(description)
            hay += [f" {_normalise(ex.name or '')} " for ex in parsed]
        if activity.get("type") not in ENDURANCE_ACTIVITY_TYPES:
            hay.append(f" {_normalise(description)} ")
        if any(f" {t} " in h for t in targets for h in hay):
            best = day
    return best


def _latest_coverage_execution(
    p: dict, coverage: list[dict], activities: list[dict], today: date,
    lookback_days: int,
) -> date | None:
    """Latest day an external session covered this prescription's tags.

    Mirrors R042 from the other side: that rule drops a planned block when an
    external session already covers it, this one stops the counter from
    calling the block "never executed" when such a session took its place.
    Needs ``**Tags:**`` on the prescription; without them nothing is credited.
    """
    tags = set(p.get("tags") or [])
    if not tags or not coverage:
        return None
    best: date | None = None
    for activity in activities:
        day = _in_window(activity, today, lookback_days)
        if day is None or (best is not None and day <= best):
            continue
        name = str(activity.get("name") or "")
        a_tags = {str(t).lower() for t in activity.get("tags") or []}
        for e in coverage:
            if not (e["covers"] & tags):
                continue
            if e["workout_re"] is not None and not e["workout_re"].search(p["name"]):
                continue
            if e["match_re"] is not None and not e["match_re"].search(name):
                continue
            if e["tags_any"] and not (e["tags_any"] & a_tags):
                continue
            best = day
            break
    return best


def compute_prescription_compliance(
    progressions_md: str,
    today: date,
    activities: list[dict],
    lookback_days: int = 60,
    coverage: list[dict] | None = None,
) -> list[dict]:
    """Return one finding per prescription that is overdue or never executed.

    ``activities`` are intervals.icu activity dicts (``start_date_local``,
    ``name``, ``type``, ``tags``, ``description``) covering at least
    ``lookback_days``. ``coverage`` is the parsed ``external_coverage.json``
    (see ``load_external_coverage``); None or empty credits no external
    session.
    """
    prescriptions = parse_prescriptions(progressions_md)
    if not prescriptions:
        return []
    executions, sessions = _load_logged_names(activities, today, lookback_days)

    findings: list[dict] = []
    for p in prescriptions:
        candidates = [
            d
            for d in (
                _match_execution(p["name"], executions),
                _match_session(p["name"], sessions),
                _latest_alias_execution(
                    p["aliases"], activities, today, lookback_days
                ),
                _latest_coverage_execution(
                    p, coverage or [], activities, today, lookback_days
                ),
            )
            if d is not None
        ]
        last = max(candidates) if candidates else None
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
        "Prescription compliance (per exercise, from the activity descriptions — "
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
