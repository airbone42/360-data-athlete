"""Shared date extraction for intervals.icu activity/event/note dicts."""

from __future__ import annotations


def activity_date(a: dict) -> str:
    """Return the ISO ``YYYY-MM-DD`` date-of-activity/event, or ``""``.

    Canonical extraction: prefer ``start_date_local`` (athlete-local
    timestamp, present on activities and most events/notes), fall back to
    ``start_date`` (present on some events that lack a local timestamp),
    and finally ``""`` when neither is set. Callers that need a different
    default (e.g. today's date, or ``"-"``) or that key on a different
    field (e.g. wellness records keyed by ``"id"``) must not use this
    helper — it is specifically the ``start_date_local``/``start_date``
    fallback chain used across the intervals.icu cache and context layers.
    """
    return (a.get("start_date_local") or a.get("start_date") or "")[:10]
