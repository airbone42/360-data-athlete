"""Shared date parsing for config-facing date strings.

Config files (athlete_status.md recovery-week block, break notes, gates)
may carry dates either as ISO (``YYYY-MM-DD``) or as the German
``DD.MM.YYYY`` format. Every consumer must accept both — silent
format-mismatch skips have caused checks to deactivate themselves
(deload expiry parsed ISO-only in two independent places).
"""
from __future__ import annotations

import re
from datetime import date

_ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_GERMAN_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")


def parse_config_date(raw: str | None) -> date | None:
    """Parse ``YYYY-MM-DD`` or ``DD.MM.YYYY`` into a date.

    Returns None for empty/placeholder ("—", "-") or unparseable input —
    callers decide whether None is an error or an inactive state.
    """
    if not raw:
        return None
    text = raw.strip()
    if text in {"", "—", "-", "–"}:
        return None
    m = _ISO_RE.match(text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = _GERMAN_RE.match(text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None
