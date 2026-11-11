"""Read dated rows and clock-time appointments from the slot ledger.

The slot ledger in ``config/competition_plan.md`` is the canonical home of
scheduling decisions (framework/CLAUDE.md → Persistence). Two consumers read
it mechanically:

- ``validate_plan.py`` R041 looks up tomorrow's row to see whether a quality
  session is booked there (a PAP lock is only justified by a quality session
  today or tomorrow).
- ``context_builder`` compares clock-time appointments in the ledger with the
  agenda feed (``upcomingAppointments``): an appointment that only the ledger
  knows is stale or was never entered in the calendar.

A row is a line whose leading cell carries a date — a table row
(``| Mo 09.11. | … |``), a bullet (``- 12.11.: …``) or an ISO date at the
start of the line. Dates inside the row text are not row keys.

Pure functions only — callers pass the ledger text.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from app.analytics.dated_commitments import _DATE_RE, _candidate_date

__all__ = [
    "ledger_rows",
    "ledger_appointments",
    "unmatched_ledger_appointments",
    "format_ledger_feed_gaps",
]

_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
# Width of the leading part of a non-table line that may carry the row date.
_LEAD_CHARS = 18

# A clock time. Not part of a longer number, not a ratio like 1:2:3.
_TIME_RE = re.compile(r"(?<![\d:])([01]?\d|2[0-3]):([0-5]\d)(?![\d:])")
# A time introduced by these words is a window bound, not an appointment;
# a time right after a date ("Athlet 09.11. 18:49") stamps a message.
_BOUND_BEFORE_RE = re.compile(
    r"(?:\d{1,2}\.\d{1,2}\.(?:\d{4})?|\bvor|\bnach|\bbis|\bab|\bspätestens|\bfrühestens|\bbefore|\bafter|"
    r"\buntil|\bby|\bfrom|\bno\s+later\s+than|[<>≤≥~])\s*$",
    re.IGNORECASE,
)
# A clause that cancels its appointment.
_CANCELLED_RE = re.compile(
    r"~~|entf(?:ä|ae)llt|entfallen|abgesagt|ausgefallen|gestrichen|"
    r"verschoben|cancel+ed|dropped|\bmoved\b",
    re.IGNORECASE,
)
_CLAUSE_SPLIT_RE = re.compile(r"[;,|]\s*|\.\s+(?=[A-ZÄÖÜ(])")
_LABEL_RE = re.compile(r"([^\s()][^()]{0,40}?)\s*$")


def _row_date(line: str, today: date) -> tuple[date, str] | None:
    """The row's own date and the remaining row text, or ``None``."""
    stripped = line.strip()
    if stripped.startswith("|"):
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            return None
        lead, rest = cells[0], " | ".join(cells[1:])
    else:
        body = stripped.lstrip("-*• ").strip()
        lead, rest = body[:_LEAD_CHARS], body
    iso = _ISO_RE.search(lead)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3))), rest
        except ValueError:
            return None
    m = _DATE_RE.search(lead)
    if not m:
        return None
    # Resolve a year-less date against a week back, so a row of the current
    # week that already lies in the past stays in this year.
    resolved = _candidate_date(
        int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None,
        today - timedelta(days=7),
    )
    return (resolved, rest) if resolved else None


def ledger_rows(text: str, today: date, horizon_days: int = 7) -> dict[date, str]:
    """Ledger rows dated within ``[today, today + horizon_days]``.

    Several rows on the same date are joined with a newline.
    """
    horizon = today + timedelta(days=horizon_days)
    rows: dict[date, list[str]] = {}
    for line in (text or "").splitlines():
        hit = _row_date(line, today)
        if not hit:
            continue
        d, rest = hit
        if today <= d <= horizon:
            rows.setdefault(d, []).append(rest)
    return {d: "\n".join(parts) for d, parts in rows.items()}


def ledger_appointments(text: str, today: date, horizon_days: int = 7) -> list[dict]:
    """Clock-time appointments in the ledger rows of the horizon.

    Returns ``[{"date", "time", "label"}]``. A time behind a bound word
    ("vor 10:00", "after 18:00") and a clause marked cancelled are skipped.
    """
    out: list[dict] = []
    for d, row in sorted(ledger_rows(text, today, horizon_days).items()):
        for clause in _CLAUSE_SPLIT_RE.split(row):
            if _CANCELLED_RE.search(clause):
                continue
            for m in _TIME_RE.finditer(clause):
                before = clause[: m.start()]
                if _BOUND_BEFORE_RE.search(before):
                    continue
                label_m = _LABEL_RE.search(before)
                label = (label_m.group(1) if label_m else "").strip(" *:–-")
                out.append({
                    "date": d,
                    "time": f"{int(m.group(1)):02d}:{m.group(2)}",
                    "label": label[-40:] or "(no label)",
                })
    return out


def _appointment_start(appt: dict) -> datetime | None:
    if appt.get("allDay"):
        return None
    try:
        return datetime.fromisoformat(str(appt.get("start") or ""))
    except ValueError:
        return None


def unmatched_ledger_appointments(
    ledger_text: str,
    appointments: list[dict],
    today: date,
    horizon_days: int = 7,
    tolerance_min: int = 30,
) -> list[dict]:
    """Ledger appointments with no feed entry on the same day near the same time."""
    starts = [s for s in (_appointment_start(a) for a in appointments or []) if s]
    gaps: list[dict] = []
    for appt in ledger_appointments(ledger_text, today, horizon_days):
        hh, mm = (int(x) for x in appt["time"].split(":"))
        when = datetime(appt["date"].year, appt["date"].month, appt["date"].day, hh, mm)
        if any(abs((s - when).total_seconds()) <= tolerance_min * 60 for s in starts):
            continue
        gaps.append(appt)
    return gaps


def format_ledger_feed_gaps(gaps: list[dict], max_lines: int = 5) -> str | None:
    """One ``dataWarnings`` line for ledger appointments missing in the feed."""
    if not gaps:
        return None
    items = [
        f"{g['date'].isoformat()} {g['time']} {g['label']}" for g in gaps[:max_lines]
    ]
    more = f" (+{len(gaps) - max_lines} more)" if len(gaps) > max_lines else ""
    return (
        "Slot ledger appointment(s) not in upcomingAppointments: "
        + "; ".join(items) + more
        + " — the calendar feed wins: treat as cancelled unless the athlete "
        "confirms, then fix the ledger or the calendar."
    )
