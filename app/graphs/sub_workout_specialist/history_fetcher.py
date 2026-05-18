"""Fetch last N sessions of same workout type + their activity messages."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from app.api.intervals_client import IntervalsClient

logger = logging.getLogger(__name__)

# "beine" is the legacy German form of "legs" — both are accepted during the
# migration so historical activities still match.
COMPLEMENTARY_TAGS = {"legs", "beine", "plyo", "core", "balance", "mobility", "grip", "ninja", "upperbody"}
ENDURANCE_TYPES = {"Run", "Ride"}

# Activity-type aliases — intervals.icu stores indoor sessions under Virtual* types,
# but the planner / specialist directive uses the simple "Run" / "Ride" labels. Without
# this map, indoor sessions silently disappear from type history. The documented failure
# mode: a Rønnestad 30/15 logged as VirtualRide became invisible to fetch_type_history
# --type Ride, leading to the same protocol being re-prescribed despite a compliance
# drop in the prior session.
TYPE_ALIASES: dict[str, set[str]] = {
    "Run": {"Run", "VirtualRun", "TrailRun"},
    "Ride": {"Ride", "VirtualRide"},
}


def _matches_type(act_type: str, dir_type: str) -> bool:
    aliases = TYPE_ALIASES.get(dir_type, {dir_type})
    return act_type in aliases


def _compute_primary_zone(activity: dict) -> str | None:
    """Return the HR zone label with the most time (e.g. 'Z2'), or None."""
    zone_times = activity.get("icu_hr_zone_times")
    if not zone_times or not any(t for t in zone_times if t):
        return None
    max_idx = max(range(len(zone_times)), key=lambda i: zone_times[i] or 0)
    return f"Z{max_idx + 1}"


def _pace_min_km(pace_ms: float | None) -> str | None:
    """Convert pace in m/s to human-readable min/km string (e.g. '5:23/km')."""
    if not pace_ms or pace_ms <= 0:
        return None
    total_s = 1000 / pace_ms
    mins = int(total_s // 60)
    secs = int(total_s % 60)
    return f"{mins}:{secs:02d}/km"


# Canonical exercise keywords for main-set-only scanning (the matcher
# strips warm-up / cool-down sections). Used by the per-session
# `exercises_seen` field so a specialist can answer "when was exercise X
# last performed?" without scanning prose. Add new keywords as new
# exercises enter rotation. Keep entries lowercase; the matcher
# lowercases the description.
_EXERCISE_KEYWORDS: dict[str, list[str]] = {
    # Pull
    "TRX Row": ["trx row"],
    "Lat-Zug Gummiband": ["latzug gummiband", "lat-zug gummiband"],
    "Row Gummiband": ["row gummiband"],
    "Face Pulls": ["face pull"],
    # Push
    "Push-up": ["push-up", "pushup", "kneeling push"],
    "Dips": ["dips"],
    "KB Overhead Press": ["kb overhead press", "overhead press"],
    # Bizeps
    "Bizeps-Curl (KB/Kurzhantel)": ["bicep curl", "bizeps-curl", "bizeps curl"],
    "Hammer Curl": ["hammer curl"],
    "Reverse Curl": ["reverse curl"],
    # Schulter-AR / Physio
    "Schulter-Außenrotation Band": ["außenrotation", "external rotation", "schulter-ar"],
    "Banded Pull-Apart": ["banded pull-apart", "pull-apart"],
    "Scapular Depression Lift": ["scapular depression lift", "scapula depression lift"],
    # Grip
    "Farmer's Hold": ["farmer's hold", "farmer hold", "farmer's walk"],
    "Pinch Grip": ["pinch grip", "pinch plate"],
    "Wrist Curls": ["wrist curl"],
    "Finger-Extensoren Band": ["finger-extensoren", "finger extensoren"],
    "Towel Hang": ["towel hang", "towel grip"],
    # Core
    "L-Sit Tuck Hold": ["l-sit tuck", "l-sit"],
    "Hollow Rock": ["hollow rock", "hollow hold"],
    "Pallof Press": ["pallof press"],
    "Dead Bug": ["dead bug"],
    "Bird Dog": ["bird dog"],
    "Side Plank": ["side plank"],
    # Plyo / Explosive
    "Pogo Hops": ["pogo hops", "mini-pogo", "pogo"],
    "Box Jump": ["box jump"],
    "Lateral Bound": ["lateral bound"],
    "Knie-zur-Wand": ["knie-zur-wand", "knee-to-wall"],
    # Mobility / WU markers (excluded from main scan)
}

# Markers that delimit warm-up / cool-down so a wrist-curl in the WU doesn't
# count as a Grip-session anchor. Same logic as `_strip_warmup_cooldown` in
# the context builder — duplicated here so the type-history scanner does
# not depend on the context-builder module.
_WU_MARKERS = ("warm-up", "warmup")
_CD_MARKERS = ("cool-down", "cooldown")
_MAIN_MARKERS = ("hauptteil", "main")


def _hauptteil_text(notes: str) -> str:
    """Return only the HAUPTTEIL / Main portion of a workout description."""
    if not notes:
        return ""
    lower = notes.lower()
    # Cut off cool-down first
    for cd in _CD_MARKERS:
        idx = lower.find(cd)
        if idx > 0:
            notes = notes[:idx]
            lower = lower[:idx]
            break
    # Start at HAUPTTEIL / Main if present
    for main in _MAIN_MARKERS:
        idx = lower.find(main)
        if idx > 0:
            return notes[idx:]
    # Fallback: strip the first warm-up block (everything up to first blank
    # line after WARM-UP) — heuristic, conservative.
    for wu in _WU_MARKERS:
        idx = lower.find(wu)
        if idx >= 0:
            blank = notes.find("\n\n", idx + len(wu))
            if blank >= 0:
                return notes[blank:]
    return notes


def _extract_exercises_seen(description: str | None) -> list[str]:
    """Return the canonical exercise names mentioned in the HAUPTTEIL portion.

    Surfaces the "what was actually trained" signal that specialists need to
    answer "when did the athlete last do exercise X?" — the field reaches
    the specialist briefing unfiltered, so a glance at `exercises_seen` per
    session avoids re-scanning prose. Ordered alphabetically for stable
    diffing across runs.
    """
    if not description:
        return []
    haupt = _hauptteil_text(description).lower()
    if not haupt:
        return []
    seen: set[str] = set()
    for canonical, keywords in _EXERCISE_KEYWORDS.items():
        if any(kw in haupt for kw in keywords):
            seen.add(canonical)
    return sorted(seen)


def _slim_activity(activity: dict, *, is_endurance: bool = False) -> dict:
    """Reduce a full activity to the fields specialists actually need.

    Base (all types): date, name, duration_min, description, tags, primary_zone.
    Endurance extra: average_heartrate, decoupling, avg_pace_min_km.
    Messages (endurance only) are preserved if already attached.

    `description` and `messages` flow directly into the specialist briefing.
    Since both coach-authored content and Strava-roundtrip-writeable fields
    are mixed in, external text fields are sanitised before the briefing
    (LLM injection hardening — same vector as athleteFeedback).
    """
    from app.utils.sanitize import escape_for_prompt

    description_raw = activity.get("description")
    # Full workout descriptions (Pull + Grip + Schulter-AR + Bizeps + Core) regularly
    # reach 2–4 KB. The previous 1200-char cap silently dropped trailing blocks —
    # the specialist then saw only WU + start of HAUPTTEIL, missed e.g. Bizeps-Curl
    # in the Schulter-AR section, and mis-cited "letzte Bizeps-Einheit" by one
    # session. 5000 chars covers the longest historical session in this repo
    # with headroom; sanitization (zero-width-char strip, control-char escape)
    # still runs.
    description = (
        escape_for_prompt(description_raw, max_len=5000) if description_raw else None
    )

    slim: dict = {
        "date": (activity.get("start_date_local") or "")[:10],
        "name": escape_for_prompt(activity.get("name") or "", max_len=120) or None,
        "duration_min": round(activity.get("moving_time", 0) / 60) or None,
        "description": description,
        "tags": activity.get("tags"),
        "primary_zone": _compute_primary_zone(activity),
        "exercises_seen": _extract_exercises_seen(description_raw),
    }
    if is_endurance:
        slim["average_heartrate"] = activity.get("average_heartrate")
        slim["decoupling"] = activity.get("decoupling")
        slim["avg_pace_min_km"] = _pace_min_km(activity.get("pace"))
    if "messages" in activity:
        # Activity-Messages (coach-feedback) — gleicher Sanitization-Pfad.
        slim["messages"] = [
            {
                **m,
                "content": escape_for_prompt(m.get("content") or "", max_len=1500),
            }
            for m in (activity["messages"] or [])
        ]
    return slim


def _is_endurance(directive: dict) -> bool:
    return directive.get("type") in ENDURANCE_TYPES


def _match_complementary(activity: dict, directive_tags: list[str]) -> bool:
    """Return True if activity shares at least one tag with the directive."""
    activity_tags = set(str(t).lower() for t in (activity.get("tags") or []))
    directive_tag_set = set(t.lower() for t in directive_tags)
    # Match on complementary tags only
    return bool(activity_tags & directive_tag_set & COMPLEMENTARY_TAGS)


def _match_endurance(activity: dict, directive: dict) -> bool:
    """Return True if activity type matches the directive type (via TYPE_ALIASES)."""
    act_type = activity.get("type", "")
    dir_type = directive.get("type", "")
    return _matches_type(act_type, dir_type)


def _filter_activities(activities: list[dict], directive: dict) -> list[dict]:
    """Filter activities list to matching workout type/tags, sorted newest-first."""
    directive_tags = directive.get("tags") or []
    if _is_endurance(directive):
        matches = [a for a in activities if _match_endurance(a, directive)]
    else:
        matches = [a for a in activities if _match_complementary(a, directive_tags)]
    # Sort newest first
    return sorted(matches, key=lambda a: a.get("start_date_local", ""), reverse=True)


async def _fetch_extended_activities(athlete_id: str, current_date: str, weeks: int = 8) -> list[dict]:
    """Fetch activities for a wider window if needed."""
    today = date.fromisoformat(current_date)
    oldest = (today - timedelta(weeks=weeks)).isoformat()
    client = IntervalsClient(athlete_id)
    return await client.get_activities(oldest, current_date)


async def fetch_type_history(
    athlete_id: str,
    date_str: str,
    directive: dict,
    existing_activities: list[dict],
    max_sessions: int = 3,
) -> list[dict]:
    """Return up to max_sessions most-recent activities matching directive type/tags, with messages."""
    matches = _filter_activities(existing_activities, directive)

    # If fewer than desired, extend search to 12 weeks
    if len(matches) < max_sessions:
        logger.info(
            "fetch_type_history: only %d matches in 4-week window, extending to 12 weeks", len(matches)
        )
        extended = await _fetch_extended_activities(athlete_id, date_str, weeks=12)
        matches = _filter_activities(extended, directive)

    sessions = matches[:max_sessions]

    # Messages only exist for endurance activities (Run/Ride)
    is_endurance = _is_endurance(directive)
    if not is_endurance:
        return [_slim_activity(s, is_endurance=False) for s in sessions]

    client = IntervalsClient(athlete_id)

    async def _enrich(activity: dict) -> dict:
        act_id = str(activity.get("id", ""))
        if not act_id:
            return {**activity, "messages": []}
        try:
            messages = await client.get_activity_messages(act_id)
        except Exception:
            logger.warning("fetch_type_history: could not fetch messages for activity %s", act_id)
            messages = []
        return {**activity, "messages": messages}

    enriched = await asyncio.gather(*[_enrich(s) for s in sessions])
    return [_slim_activity(a, is_endurance=True) for a in enriched]
