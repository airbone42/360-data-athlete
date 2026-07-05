"""Safety net: capture full event content before deletion.

Every delete path (the pre-push dedup sweep in ``push_workouts.py`` and the
explicit ``delete_workouts.py``) appends the *complete* JSON of each event to
a JSONL backup log BEFORE the event is removed from intervals.icu. This makes
deletions recoverable: a type-based dedup sweep that removes a planned block
which was not meant to be regenerated (e.g. a shifted physio/core block left
out of the current push array) no longer loses its content silently — the
full description, structure and metadata remain in ``deleted_events.jsonl``.

Recovery: read the JSONL, find the entry by ``event.name`` / ``event.id`` /
``backed_up_at``, and re-push its ``event.description``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.utils.paths import DATA_DIR

logger = logging.getLogger(__name__)

BACKUP_PATH = DATA_DIR / "deleted_events.jsonl"


def backup_events_before_delete(
    events: list[dict],
    reason: str,
    backup_path: Path = BACKUP_PATH,
) -> int:
    """Append the full JSON of each event to the backup log before deletion.

    Args:
        events: full event dicts (as returned by ``IntervalsClient.get_events``)
            about to be deleted. Falsy entries are skipped.
        reason: short provenance string (e.g. ``"push-dedup 2026-07-05"``)
            recorded alongside each backed-up event.
        backup_path: override the JSONL target (tests).

    Returns:
        Number of events written.

    Fail-soft: a backup write error is logged at ERROR level but never raises —
    a broken backup path must not wedge the whole push/delete path. The caller
    still deletes; the ERROR log surfaces that content may be unrecoverable.
    """
    events = [e for e in (events or []) if e]
    if not events:
        return 0
    try:
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).isoformat()
        with backup_path.open("a", encoding="utf-8") as fh:
            for ev in events:
                fh.write(
                    json.dumps(
                        {"backed_up_at": stamp, "reason": reason, "event": ev},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        logger.info(
            "Backed up %d event(s) to %s before delete (reason: %s)",
            len(events),
            backup_path,
            reason,
        )
        return len(events)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Event backup FAILED before delete (reason: %s) — proceeding, "
            "content may be unrecoverable: %s",
            reason,
            exc,
        )
        return 0
