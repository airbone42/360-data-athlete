"""One-NOTE-per-day upsert for date-scoped athlete notes.

Repeated NOTE writes used to stack a new NOTE event per write; the
calendar filled with parallel notes for the same day and older ones had
to be deleted by hand. The day NOTE is now a single event whose
description is organised in ``## <Section>`` blocks (one per feedback
category — e.g. HRV-Review, Mental-Coach, Athleten-Feedback):

- writing a section that already exists **replaces** that block,
- a new section is **appended**,
- all other sections stay untouched.

A single-section day NOTE keeps the section name as its event name (same
look as the historical one-note-per-write behaviour); as soon as a second
section joins, the event is renamed to ``Coach-Log <date>``.

Downstream contract: consumers that detect a note topic by substring
(e.g. the ``HRV-Review`` pending check in ``context_builder``) keep
working because the section heading carries the topic name inside the
description.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

DAY_NOTE_PREFIX = "Coach-Log"

_SECTION_RE = re.compile(r"^##\s+(?P<name>.+?)\s*$", re.MULTILINE)


def split_sections(description: str, fallback_name: str) -> list[tuple[str, str]]:
    """Split a day-note description into ordered ``(heading, body)`` pairs.

    A legacy description without ``## `` headings becomes a single section
    under ``fallback_name`` (the event name of the note it came from), so
    pre-upsert notes merge cleanly on their first update.
    """
    description = (description or "").strip()
    if not description:
        return []
    matches = list(_SECTION_RE.finditer(description))
    if not matches:
        return [(fallback_name.strip() or "Notiz", description)]
    sections: list[tuple[str, str]] = []
    # Text before the first heading keeps the fallback name.
    preamble = description[: matches[0].start()].strip()
    if preamble:
        sections.append((fallback_name.strip() or "Notiz", preamble))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(description)
        body = description[m.end():end].strip()
        sections.append((m.group("name"), body))
    return sections


def merge_section(
    description: str, fallback_name: str, section: str, text: str
) -> tuple[str, list[str]]:
    """Replace-or-append ``section`` in ``description``.

    Returns ``(merged_description, section_names)`` — the section list lets
    the caller decide the event name (single section keeps its name, a
    multi-topic note gets the ``Coach-Log <date>`` name).
    """
    sections = split_sections(description, fallback_name)
    text = text.strip()
    replaced = False
    merged: list[tuple[str, str]] = []
    for name, body in sections:
        if name.strip().casefold() == section.strip().casefold():
            merged.append((name, text))
            replaced = True
        else:
            merged.append((name, body))
    if not replaced:
        merged.append((section, text))
    out = "\n\n".join(f"## {name}\n{body}" for name, body in merged)
    return out, [name for name, _ in merged]


async def upsert_day_note(client, date_str: str, section: str, text: str) -> dict:
    """Create or update the single day NOTE for ``date_str``.

    ``client`` needs ``get_notes``, ``post_events_bulk`` and
    ``update_event`` (both the raw and the cached intervals client
    qualify). Returns ``{"action": "created"|"updated", "event": {...}}``.
    """
    notes = await client.get_notes(date_str, date_str)
    day_notes = [
        n for n in notes
        if (n.get("start_date_local") or n.get("start_date") or "")[:10] == date_str
    ]

    if not day_notes:
        event = {
            "category": "NOTE",
            "start_date_local": f"{date_str}T08:00:00",
            "name": section,
            "description": text.strip(),
        }
        result = await client.post_events_bulk([event])
        created = result[0] if isinstance(result, list) and result else result
        return {"action": "created", "event": created}

    # Oldest note is the canonical day note; later duplicates are surfaced
    # for manual cleanup rather than silently merged or deleted.
    target = min(day_notes, key=lambda n: n.get("id") or 0)
    merged, names = merge_section(
        target.get("description") or "", target.get("name") or section, section, text
    )
    name = names[0] if len(names) == 1 else f"{DAY_NOTE_PREFIX} {date_str}"
    payload = {
        "category": "NOTE",
        "start_date_local": target.get("start_date_local") or f"{date_str}T08:00:00",
        "name": name,
        "description": merged,
    }
    updated = await client.update_event(target["id"], payload)
    if len(day_notes) > 1:
        extras = [n.get("id") for n in day_notes if n.get("id") != target.get("id")]
        logger.warning(
            "one-NOTE-per-day: %d weitere NOTE-Events am %s (ids %s) — "
            "konsolidieren via delete_workouts --event-ids",
            len(extras), date_str, extras,
        )
    return {"action": "updated", "event": updated}
