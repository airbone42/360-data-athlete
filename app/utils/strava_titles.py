"""Strava title cleaning + Strava↔intervals.icu matching helpers.

Lifted from the (now retired) `scripts/sync_strava_titles.py` so both the
new `scripts/strava_pending.py` helper and any future caller can share
the same regex set.

- `clean_name(name)` — strip a home-town prefix, hashtags, whitespace.
- `is_indoor_activity(iv)` — intervals.icu indoor detection (trainer flag
  or Virtual* type).
- `detect_surface_mismatch(iv, cleaned)` — indoor activity, but title
  carries an outdoor-surface term → replace with the indoor equivalent
  (Treadmill, Trainer, Indoor). Returns `(new_name, reason)` or
  `(None, None)`.
- `parse_iso(s)` — robust ISO datetime parser, assumes UTC if naive.
- `find_strava_match(iv_start, strava_acts, tolerance_s)` — match by
  start-time tolerance.

The home-town list is generic (default empty) — callers that want to
strip athlete-specific home-towns call `clean_name(name, locations=[…])`
with their own list. The default strip only touches hashtags + whitespace.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from app.config import settings

_HASHTAG_RE = re.compile(r"\s*#[\w\-]+", re.UNICODE)

# Surface terms that should not appear in indoor activity titles
# (trainer=True / VirtualRun / VirtualRide) — otherwise "forest path" or
# "trail" goes out to Strava even though the session happened on a
# treadmill / trainer. Word-boundary + case-insensitive. Detection
# patterns are bilingual (German + English) so the cleanup works on
# titles written in either language; the replacement value is English
# (framework default).
_OUTDOOR_SURFACE_REPLACEMENTS_RUN = [
    # German tokens
    (re.compile(r"\bForstwege?\b", re.IGNORECASE), "Treadmill"),
    (re.compile(r"\bWald\b", re.IGNORECASE), "Treadmill"),
    (re.compile(r"\bStraße\b|\bStrasse\b", re.IGNORECASE), "Treadmill"),
    (re.compile(r"\bBahn\b", re.IGNORECASE), "Treadmill"),
    # English / shared tokens
    (re.compile(r"\bTrail\b", re.IGNORECASE), "Treadmill"),
    (re.compile(r"\bAsphalt\b", re.IGNORECASE), "Treadmill"),
    (re.compile(r"\bForest\s*Path\b", re.IGNORECASE), "Treadmill"),
    (re.compile(r"\bRoad\b", re.IGNORECASE), "Treadmill"),
    (re.compile(r"\bTrack\b", re.IGNORECASE), "Treadmill"),
    (re.compile(r"\bOutdoor\b", re.IGNORECASE), "Indoor"),
]
_OUTDOOR_SURFACE_REPLACEMENTS_RIDE = [
    # German tokens
    (re.compile(r"\bStraße\b|\bStrasse\b", re.IGNORECASE), "Trainer"),
    (re.compile(r"\bForstwege?\b", re.IGNORECASE), "Trainer"),
    # English / shared tokens
    (re.compile(r"\bTrail\b", re.IGNORECASE), "Trainer"),
    (re.compile(r"\bRoad\b", re.IGNORECASE), "Trainer"),
    (re.compile(r"\bOutdoor\b", re.IGNORECASE), "Indoor"),
]


def is_indoor_activity(iv: dict) -> bool:
    """intervals.icu detects indoor sessions via the trainer flag and/or Virtual type."""
    if iv.get("trainer") is True:
        return True
    atype = (iv.get("type") or "").lower()
    return atype in {"virtualrun", "virtualride", "virtualrow"}


def detect_surface_mismatch(iv: dict, cleaned: str) -> tuple[str | None, str | None]:
    """If the activity is indoor but the title contains outdoor-surface terms,
    replace them with indoor equivalents. Returns (new_name, reason) or
    (None, None) when no mismatch is found.
    """
    if not is_indoor_activity(iv):
        return None, None
    atype = (iv.get("type") or "").lower()
    if atype in {"virtualride", "ride"}:
        patterns = _OUTDOOR_SURFACE_REPLACEMENTS_RIDE
    else:
        patterns = _OUTDOOR_SURFACE_REPLACEMENTS_RUN
    new_name = cleaned
    replaced: list[str] = []
    for pat, repl in patterns:
        if pat.search(new_name):
            replaced.append(f"{pat.pattern}→{repl}")
            new_name = pat.sub(repl, new_name)
    if not replaced:
        return None, None
    return new_name, ", ".join(replaced)


def clean_name(name: str, locations: list[str] | None = None) -> str:
    """Strip a home-town prefix (if a list is given), hashtags and whitespace."""
    if not name:
        return ""
    out = name
    for loc in locations or []:
        out = re.sub(
            rf"^{re.escape(loc)}\s*[-–—]\s*",
            "",
            out,
            count=1,
            flags=re.IGNORECASE,
        )
    out = _HASHTAG_RE.sub("", out)
    return out.strip()


def parse_iso(s: str) -> datetime:
    """Parse ISO datetime; assume UTC if naive."""
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def find_strava_match(
    iv_start: datetime,
    strava_acts: list[dict],
    tolerance_s: int = 120,
) -> dict | None:
    """Match by UTC start time. Both sides use `start_date` (real UTC).
    intervals.icu emits it with a `Z` suffix; Strava likewise."""
    for s in strava_acts:
        s_start_str = s.get("start_date")
        if not s_start_str:
            continue
        try:
            s_start = parse_iso(s_start_str)
        except Exception:
            continue
        if abs((iv_start - s_start).total_seconds()) <= tolerance_s:
            return s
    return None


# ── Insights / marker constants (used by strava_pending + strava_apply) ──

#: Idempotency anchor: the signature of the insights footer. Every
#: insights block written by the coach pipeline ends with
#: `{Gerund} {INSIGHTS_ANCHOR}` — the fixed suffix phrase serves as
#: the marker that the pipeline has already processed this activity.
#: Default `by 360° Data Athlete` (project brand; light attribution in
#: the followers' feed); configurable via ENV
#: `STRAVA_PUBLISHER_FOOTER_SUFFIX` — wrappers can override for their
#: own branding.
INSIGHTS_ANCHOR = settings.strava_publisher_footer_suffix

#: Legacy marker from earlier sync scripts. Stripped from the description
#: by `strava_apply.py` on the first apply — case-insensitive, only when
#: at the very end of the description, so old pushed blocks don't appear
#: twice on re-sync.
LEGACY_MARKER_RE = re.compile(
    r"\n*powered by 360° Data Athlete\s*$",
    re.IGNORECASE,
)

#: Activity types for which an insights block is built.
INSIGHTS_TYPES = frozenset({"Run", "VirtualRun", "Ride", "VirtualRide"})

#: Global insights-block toggle. Off → agent does pure title sync, no
#: body, no footer. Default on; can be disabled via ENV
#: `STRAVA_PUBLISHER_FOOTER_ENABLED=false`.
INSIGHTS_ENABLED = settings.strava_publisher_footer_enabled

#: Strava description limit. The actual API limit is around 10k; we
#: leave room for later appends.
STRAVA_DESCRIPTION_MAX = 4500
