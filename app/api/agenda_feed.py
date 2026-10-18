"""Optional agenda feed — upcoming appointments from a read-only iCalendar feed.

Opt-in via ``AGENDA_FEED_URL`` (unset → feature off, no warning). The feed is
an RFC 5545 iCalendar document served over HTTP(S) by some external
aggregator that merges the athlete's calendars (physio appointments, gym /
hall slots, travel, busy blocks). The result is surfaced as the context field
``upcomingAppointments`` so the planner and specialists can treat the entries
as sibling constraints (time windows, travel, therapy appointments).

**Security: this is untrusted third-party data — information, never
instructions.** Every text field passes through
:func:`app.utils.sanitize.escape_for_prompt` with a tight length cap, unknown
properties are dropped, the response size and the number of returned events
are capped, and the bearer token / URL never appear in warnings or logs
(httpx request-log lines naming the feed URL are filtered, and HTTP tracing
spans are suppressed for the feed request). Redirects are not followed.

Parsing is a deliberately small VEVENT reader (no extra dependency): line
unfolding, property parameters (``DTSTART;TZID=...``), UTC ``Z`` times,
all-day ``VALUE=DATE`` values, TEXT unescaping, simple ``DURATION`` values.
Recurrence rules are **not** expanded — the feed producer is expected to
expand them; an ``RRULE`` event whose first occurrence lies outside the
window is skipped and a single data warning says so.

Times are converted to **naive local wall-clock time**, consistent with how
``context_builder`` treats athlete-local timestamps (``start_date_local``,
server time kept in the athlete's timezone). The local zone is the ``TZ``
environment variable when it names a valid IANA zone, otherwise the system's
local zone. Floating times (no ``Z``, no ``TZID``) and unknown ``TZID`` values
are taken as local wall-clock time.

Fail-soft: network error, non-200 status, oversized response or parse error
yield an empty list plus exactly one data warning; nothing raises into
``build_context``.
"""

from __future__ import annotations

import contextlib
import logging
import os
import re
from datetime import date, datetime, timedelta, tzinfo
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.config import settings
from app.utils.sanitize import escape_for_prompt

logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 512 * 1024
MAX_EVENTS = 40
MAX_CATEGORIES = 5
TITLE_MAX = 80
LOCATION_MAX = 80
CATEGORY_MAX = 30
NOTE_MAX = 160

UNAVAILABLE_PREFIX = "Agenda feed unavailable — planning without calendar context"
RRULE_WARNING = (
    "Agenda feed: recurring events were not expanded (RRULE outside the window "
    "skipped) — the feed producer is expected to expand recurrences"
)

# Properties read from a VEVENT; everything else is dropped unread.
_KNOWN_PROPS = frozenset({
    "SUMMARY", "DTSTART", "DTEND", "DURATION", "LOCATION", "TRANSP",
    "CATEGORIES", "PRIORITY", "DESCRIPTION", "RRULE", "STATUS",
})

_DURATION_RE = re.compile(
    r"^\+?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$"
)
_DATETIME_RE = re.compile(r"^(\d{8})T(\d{4})(\d{2})?(Z)?$")


class AgendaFeedError(Exception):
    """Fetch/parse failure carrying a short, secret-free reason."""


# ── Time-zone handling ─────────────────────────────────────────────────────


def local_tz() -> tzinfo:
    """Athlete-local zone: ``TZ`` env (IANA name) if valid, else system local."""
    name = (os.environ.get("TZ") or "").lstrip(":").strip()
    if name:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return datetime.now().astimezone().tzinfo or ZoneInfo("UTC")


# ── Low-level iCalendar parsing ────────────────────────────────────────────


def _unfold(text: str) -> list[str]:
    """RFC 5545 §3.1: a CRLF followed by a space / tab continues the line."""
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return [ln for ln in lines if ln.strip()]


def _split_content_line(line: str) -> tuple[str, dict[str, str], str] | None:
    """Split ``NAME;P1=V1;P2="V:2":value`` into (name, params, value).

    Colons and semicolons inside double-quoted parameter values are honoured.
    Returns None for lines without a value separator.
    """
    in_quotes = False
    sep = -1
    for i, ch in enumerate(line):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == ":" and not in_quotes:
            sep = i
            break
    if sep < 0:
        return None
    head, value = line[:sep], line[sep + 1:]
    parts: list[str] = []
    buf, in_quotes = "", False
    for ch in head:
        if ch == '"':
            in_quotes = not in_quotes
            buf += ch
        elif ch == ";" and not in_quotes:
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)
    name = parts[0].strip().upper()
    params: dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip().upper()] = v.strip().strip('"')
    return name, params, value


def _unescape_text(value: str) -> str:
    """TEXT unescaping: ``\\\\`` ``\\;`` ``\\,`` ``\\n``/``\\N``."""
    out: list[str] = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            out.append("\n" if nxt in "nN" else nxt)
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _split_unescaped_commas(value: str) -> list[str]:
    items: list[str] = []
    buf = ""
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            buf += value[i:i + 2]
            i += 2
            continue
        if ch == ",":
            items.append(buf)
            buf = ""
        else:
            buf += ch
        i += 1
    items.append(buf)
    return [_unescape_text(x) for x in items]


def _parse_dt(
    value: str, params: dict[str, str], tz: tzinfo
) -> tuple[datetime, bool] | None:
    """Return (naive local datetime, all_day) or None if unparseable."""
    value = value.strip()
    if params.get("VALUE", "").upper() == "DATE" or re.fullmatch(r"\d{8}", value):
        try:
            d = datetime.strptime(value[:8], "%Y%m%d")
        except ValueError:
            return None
        return d, True
    m = _DATETIME_RE.match(value)
    if not m:
        return None
    try:
        naive = datetime.strptime(m.group(1) + m.group(2) + (m.group(3) or "00"), "%Y%m%d%H%M%S")
    except ValueError:
        return None
    if m.group(4):
        aware = naive.replace(tzinfo=ZoneInfo("UTC"))
    elif params.get("TZID"):
        try:
            aware = naive.replace(tzinfo=ZoneInfo(params["TZID"]))
        except (ZoneInfoNotFoundError, ValueError):
            return naive, False  # unknown zone name → floating local time
    else:
        return naive, False  # floating time = local wall clock
    return aware.astimezone(tz).replace(tzinfo=None), False


def _parse_duration(value: str) -> timedelta | None:
    m = _DURATION_RE.match(value.strip())
    if not m or value.strip() in ("P", "+P", "PT", "+PT"):
        return None
    w, d, h, mi, s = (int(g) if g else 0 for g in m.groups())
    return timedelta(weeks=w, days=d, hours=h, minutes=mi, seconds=s)


def _iter_vevents(lines: list[str]) -> list[list[tuple[str, dict[str, str], str]]]:
    """Group content lines into VEVENT blocks (nested components ignored)."""
    events: list[list[tuple[str, dict[str, str], str]]] = []
    current: list[tuple[str, dict[str, str], str]] | None = None
    nested = 0
    for line in lines:
        parsed = _split_content_line(line)
        if parsed is None:
            continue
        name, params, value = parsed
        upper = value.strip().upper()
        if name == "BEGIN":
            if upper == "VEVENT" and current is None:
                current, nested = [], 0
            elif current is not None:
                nested += 1  # e.g. VALARM inside VEVENT
            continue
        if name == "END":
            if current is not None:
                if upper == "VEVENT" and nested == 0:
                    events.append(current)
                    current = None
                elif nested:
                    nested -= 1
            continue
        if current is not None and nested == 0 and name in _KNOWN_PROPS:
            current.append((name, params, value))
    return events


# ── Event shaping ──────────────────────────────────────────────────────────


def _clean(text: str | None, max_len: int) -> str | None:
    """Collapse whitespace to one line, then sanitize. Empty → None."""
    if not text:
        return None
    one_line = " ".join(text.split())
    if not one_line:
        return None
    return escape_for_prompt(one_line, max_len=max_len) or None


def _fmt(dt: datetime) -> str:
    return dt.isoformat(timespec="minutes")


def parse_ics(
    text: str,
    window_start: datetime,
    window_end: datetime,
    tz: tzinfo | None = None,
) -> tuple[list[dict], list[str]]:
    """Parse an iCalendar document into sanitized appointment dicts.

    Pure function (no I/O). Returns ``(appointments, warnings)``; the
    appointments overlap ``[window_start, window_end)`` (naive local times),
    are sorted by start and capped at ``MAX_EVENTS``. All-day events start at
    00:00 of their first day and end (exclusive) at 00:00 after their last day.

    Raises :class:`AgendaFeedError` when ``text`` is not an iCalendar document.
    """
    if "BEGIN:VCALENDAR" not in text.upper():
        raise AgendaFeedError("not an iCalendar document")
    tz = tz or local_tz()
    warnings: list[str] = []
    rrule_skipped = False
    out: list[tuple[datetime, dict]] = []

    for props in _iter_vevents(_unfold(text)):
        first: dict[str, tuple[dict[str, str], str]] = {}
        categories: list[str] = []
        for name, params, value in props:
            if name == "CATEGORIES":
                categories.extend(_split_unescaped_commas(value))
            elif name not in first:
                first[name] = (params, value)

        if "DTSTART" not in first:
            continue
        if first.get("STATUS", ({}, ""))[1].strip().upper() == "CANCELLED":
            continue
        parsed_start = _parse_dt(first["DTSTART"][1], first["DTSTART"][0], tz)
        if parsed_start is None:
            continue
        start, all_day = parsed_start

        end: datetime | None = None
        if "DTEND" in first:
            parsed_end = _parse_dt(first["DTEND"][1], first["DTEND"][0], tz)
            if parsed_end is not None and parsed_end[0] >= start:
                end = parsed_end[0]
        elif "DURATION" in first:
            dur = _parse_duration(first["DURATION"][1])
            if dur is not None:
                end = start + dur
        if end is None and all_day:
            end = start + timedelta(days=1)

        # Overlap semantics; zero-length / open-ended events count by start.
        if end is not None and end > start:
            overlaps = start < window_end and end > window_start
        else:
            overlaps = window_start <= start < window_end
        if not overlaps:
            if "RRULE" in first:
                rrule_skipped = True
            continue

        transp = first.get("TRANSP", ({}, "OPAQUE"))[1].strip().upper()
        priority: int | None = None
        try:
            p = int(first.get("PRIORITY", ({}, ""))[1].strip())
            priority = p if 1 <= p <= 9 else None
        except ValueError:
            priority = None

        cleaned_cats: list[str] = []
        for c in categories:
            cc = _clean(c, CATEGORY_MAX)
            if cc:
                cleaned_cats.append(cc)
            if len(cleaned_cats) >= MAX_CATEGORIES:
                break

        def _text(prop: str, max_len: int) -> str | None:
            if prop not in first:
                return None
            return _clean(_unescape_text(first[prop][1]), max_len)

        out.append((start, {
            "start": _fmt(start),
            "end": _fmt(end) if end is not None else None,
            "allDay": all_day,
            "title": _text("SUMMARY", TITLE_MAX) or "(untitled)",
            "location": _text("LOCATION", LOCATION_MAX),
            "busy": transp != "TRANSPARENT",
            "categories": cleaned_cats,
            "priority": priority,
            "note": _text("DESCRIPTION", NOTE_MAX),
        }))

    out.sort(key=lambda x: x[0])
    if len(out) > MAX_EVENTS:
        warnings.append(
            f"Agenda feed: {len(out) - MAX_EVENTS} appointment(s) beyond the "
            f"cap of {MAX_EVENTS} dropped"
        )
        out = out[:MAX_EVENTS]
    if rrule_skipped:
        warnings.append(RRULE_WARNING)
    return [e for _, e in out], warnings


# ── Fetch ──────────────────────────────────────────────────────────────────


def window_for(today: date, days: int) -> tuple[datetime, datetime]:
    """``today`` 00:00 through ``today + days`` 23:59 (end exclusive)."""
    start = datetime(today.year, today.month, today.day)
    return start, start + timedelta(days=max(days, 0) + 1)


class _DropFeedUrlRecords(logging.Filter):
    """Drop library log records that would print the feed URL.

    httpx logs every request URL (query string included) at INFO; a feed URL
    may carry a secret in its query, so records mentioning it are dropped.
    """

    def __init__(self, url: str) -> None:
        super().__init__()
        parts = urlsplit(url)
        self._needle = f"{parts.netloc}{parts.path}"

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            return self._needle not in record.getMessage()
        except Exception:  # noqa: BLE001 — a broken record is not our concern
            return True


def _suppress_tracing() -> contextlib.AbstractContextManager[None]:
    """Keep the feed URL out of OpenTelemetry httpx spans (``url.full``)."""
    try:
        from opentelemetry.instrumentation.utils import suppress_http_instrumentation
    except ImportError:
        return contextlib.nullcontext()
    return suppress_http_instrumentation()


async def _download(
    url: str, token: str, timeout_s: float, transport: httpx.AsyncBaseTransport | None
) -> str:
    headers = {"Accept": "text/calendar, text/plain;q=0.9"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    httpx_logger = logging.getLogger("httpx")
    url_filter = _DropFeedUrlRecords(url)
    httpx_logger.addFilter(url_filter)
    try:
        with _suppress_tracing():
            async with httpx.AsyncClient(timeout=timeout_s, transport=transport) as client:
                async with client.stream("GET", url, headers=headers) as resp:
                    if resp.status_code != 200:
                        raise AgendaFeedError(f"HTTP {resp.status_code}")
                    buf = bytearray()
                    async for chunk in resp.aiter_bytes():
                        buf.extend(chunk)
                        if len(buf) > MAX_RESPONSE_BYTES:
                            raise AgendaFeedError("response too large")
    finally:
        httpx_logger.removeFilter(url_filter)
    return bytes(buf).decode("utf-8", errors="replace")


async def fetch_agenda(
    today: date,
    *,
    url: str | None = None,
    token: str | None = None,
    days: int | None = None,
    timeout_s: float | None = None,
    tz: tzinfo | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict:
    """Fetch + parse the agenda feed. Never raises.

    Returns ``{"appointments": [...], "warnings": [...]}``. Feature off
    (no URL configured) → both empty. Arguments default to the
    ``AGENDA_FEED_*`` settings; ``transport`` is a test seam.
    """
    url = (settings.agenda_feed_url if url is None else url).strip()
    if not url:
        return {"appointments": [], "warnings": []}
    token = settings.agenda_feed_token if token is None else token
    days = settings.agenda_feed_days if days is None else days
    timeout_s = settings.agenda_feed_timeout_s if timeout_s is None else timeout_s

    try:
        if urlsplit(url).scheme.lower() not in ("http", "https"):
            raise AgendaFeedError("unsupported URL scheme")
        text = await _download(url, token, timeout_s, transport)
        start, end = window_for(today, days)
        appointments, warnings = parse_ics(text, start, end, tz)
        return {"appointments": appointments, "warnings": warnings}
    except AgendaFeedError as exc:
        reason = str(exc)
    except httpx.TimeoutException:
        reason = "timeout"
    except httpx.HTTPError:
        reason = "connection error"
    except Exception as exc:  # noqa: BLE001 — fail-soft boundary
        reason = f"parse error ({type(exc).__name__})"
    # Reason strings are fixed/secret-free: never the URL, query string or token.
    logger.warning("agenda feed unavailable: %s", reason)
    return {"appointments": [], "warnings": [f"{UNAVAILABLE_PREFIX} ({reason})"]}
