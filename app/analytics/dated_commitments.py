"""Surface near-term dated scheduling commitments from config prose.

Scheduling decisions belong in the competition plan's slot ledger — that is
the file the planning flow consults for dates.  In practice they also get
written where their *rationale* lives: next to the exercise entry whose
placement they justify, or into an athlete file alongside the restriction
that motivated them.

That split is the dangerous kind of bookkeeping error, because nothing about
it looks wrong.  The decision *was* recorded, everyone involved believes it is
live, and the next planning cycle still contradicts it — it read the ledger,
and the ledger never learned.  There is no missing entry to notice.

This module closes the read side: it scans config prose for dates that fall
inside the planning horizon and hands them to the planner regardless of which
file they were filed in.  The audit check fixes the filing; this makes the
filing matter less.

Pure functions only — callers supply ``{filename: text}`` so the logic stays
testable without a config directory.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

__all__ = ["find_dated_commitments", "format_commitments"]

# ``03.09.`` / ``3.9.2026`` / ``03.09.2026`` — the year is optional because
# config prose usually drops it inside the running season.
_DATE_RE = re.compile(r"\b(\d{1,2})\.\s?(\d{1,2})\.(\d{4})?")

# Lines that merely *report* a past execution are not commitments.  A German
# perfect-tense marker or a completion glyph next to the date means the entry
# documents history, and history is what these files are supposed to hold.
_RETROSPECTIVE_RE = re.compile(
    r"✅|~~|\bgelaufen\b|\bausgeführt\b|\bausgefuehrt\b|\babsolviert\b"
    r"|\berledigt\b|\bwar\b|\bhielt\b|\bstand\b|\bentfallen\b"
    r"|\bcompleted\b|\bexecuted\b|\bwas\b",
    re.IGNORECASE,
)

# Anything shorter carries no recoverable meaning once truncated into a
# constraints line.
_MIN_SNIPPET = 12


def _candidate_date(day: int, month: int, year: int | None, today: date) -> date | None:
    """Build a date from a loose ``DD.MM.[YYYY]`` match, or ``None``.

    Without an explicit year, try the current year first and roll forward to
    the next one when that lands in the past — a bare ``05.01.`` written in
    December means the coming January, not the one ten months gone.
    """
    for candidate_year in ([year] if year else [today.year, today.year + 1]):
        try:
            resolved = date(candidate_year, month, day)
        except ValueError:
            continue
        if year or resolved >= today:
            return resolved
    return None


def find_dated_commitments(
    sources: dict[str, str],
    today: date,
    horizon_days: int = 7,
) -> list[dict]:
    """Return forward-looking dated lines from ``sources``.

    ``sources`` maps a display filename to its full text.  The caller decides
    what to pass — in particular whether to include the slot ledger itself,
    which normally it should not: the planner already reads it, and echoing it
    back would bury the misfiled entries this is meant to expose.

    Only dates in ``[today, today + horizon_days]`` qualify.  That window is
    what makes the scan precise rather than noisy: these files are dense with
    historical dates, and every one of them falls outside it.
    """
    horizon = today + timedelta(days=horizon_days)
    findings: list[dict] = []

    for filename, text in sorted(sources.items()):
        if not text:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if len(stripped) < _MIN_SNIPPET:
                continue
            if _RETROSPECTIVE_RE.search(stripped):
                continue

            hits: list[date] = []
            for day_s, month_s, year_s in _DATE_RE.findall(stripped):
                resolved = _candidate_date(
                    int(day_s), int(month_s), int(year_s) if year_s else None, today
                )
                if resolved and today <= resolved <= horizon:
                    hits.append(resolved)
            if not hits:
                continue

            findings.append(
                {
                    "file": filename,
                    "line": lineno,
                    "dates": sorted(set(hits)),
                    "text": stripped,
                }
            )

    findings.sort(key=lambda f: (f["dates"][0], f["file"], f["line"]))
    return findings


def format_commitments(
    findings: list[dict],
    ledger_name: str = "competition_plan.md",
    max_lines: int = 8,
    snippet_chars: int = 160,
) -> str | None:
    """Render findings as a ``planningConstraints`` block, or ``None``.

    Deliberately phrased as *check this*, not *obey this*: the entry may be a
    stale plan that the ledger has already superseded.  The planner has to
    reconcile the two, and telling it which one wins is not this function's
    job — recency and athlete confirmation decide that, and neither is
    visible here.
    """
    if not findings:
        return None

    lines = [
        f"📌 Datierte Zusagen außerhalb von {ledger_name} "
        "(kanonischer Ort für Slots ist dort die Slot-Buchführung):"
    ]
    for finding in findings[:max_lines]:
        snippet = finding["text"]
        if len(snippet) > snippet_chars:
            snippet = snippet[: snippet_chars - 1].rstrip() + "…"
        dates = ", ".join(d.isoformat() for d in finding["dates"])
        lines.append(f"  - {finding['file']}:{finding['line']} ({dates}) — {snippet}")

    if len(findings) > max_lines:
        lines.append(f"  - … {len(findings) - max_lines} weitere")

    lines.append(
        "→ Gegen die Slot-Buchführung prüfen. Weicht eine Zusage ab, gilt der "
        "jüngere athleten-bestätigte Stand — und der Slot gehört in die "
        "Buchführung nachgetragen, nicht in der Übungsdatei belassen."
    )
    return "\n".join(lines)
