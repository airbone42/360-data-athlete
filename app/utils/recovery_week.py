"""Parse the recovery-week status block of ``config/athlete_status.md``.

The block exists in two spellings: the German one (``## Erholungswoche-Status``
with ``aktiv`` / ``start`` / ``ende_geplant`` / ``begründung``) and the English
one ``config.example/athlete_status.md`` ships (``## Recovery week status`` with
``active`` / ``start`` / ``planned end`` / ``reason``). Both parse to one dict,
keyed the way ``context_builder`` reads it, so the context and the audit check
cannot disagree about whether a recovery week is set — the same lesson as
``date_parse``: two parsers of one block drift apart.
"""
from __future__ import annotations

import re

_SECTION_RE = re.compile(
    r"^## (?:Erholungswoche-Status|Recovery week status)[ \t]*\n(.*?)(?=\n##|\Z)",
    re.DOTALL | re.MULTILINE | re.IGNORECASE,
)

# Label as written in the file -> key in the returned dict.
_KEYS = {
    "aktiv": "aktiv",
    "active": "active",
    "start": "start",
    "ende_geplant": "ende_geplant",
    "planned end": "planned_end",
    "planned_end": "planned_end",
    "begründung": "begründung",
    "reason": "rationale",
    "rationale": "rationale",
}


def parse_recovery_week(text: str) -> dict[str, str]:
    """Return the fields of the recovery-week block, or ``{}`` without one."""
    section = _SECTION_RE.search(text)
    if not section:
        return {}
    result: dict[str, str] = {}
    for label, key in _KEYS.items():
        if key in result:
            continue
        field = re.search(
            rf"\*\*{re.escape(label)}:\*\*\s*(.+)", section.group(1), re.IGNORECASE
        )
        if field:
            result[key] = field.group(1).strip()
    return result
