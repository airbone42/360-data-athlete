"""Shared date-window arithmetic for lookback/cutoff computations.

The dominant duplicated pattern across the codebase is a single ISO-date
cutoff N days before some base date (``(base - timedelta(days=n)).isoformat()``),
used both for fixed lookback windows (90d HRV reference, 7d rolling
windows, ...) and for per-iteration date computation inside a loop (the
same expression with a loop variable in place of the literal N). Both
call shapes are covered by ``cutoff_iso`` — it does not care whether ``n``
is a constant or a loop variable.
"""

from __future__ import annotations

from datetime import date, timedelta


def cutoff_iso(today: date, n: int) -> str:
    """Return the ISO date ``n`` days before ``today``.

    Equivalent to ``(today - timedelta(days=n)).isoformat()``. ``today``
    is any base date, not necessarily the actual current day — callers
    also use this to compute a cutoff relative to an arbitrary reference
    date (e.g. a historical day being classified).
    """
    return (today - timedelta(days=n)).isoformat()
