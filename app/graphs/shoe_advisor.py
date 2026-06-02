"""Shoe advisor — recommendation, rotation, gap detection.

Input:
    shoes       — list of enriched shoe dicts from StravaClient.list_shoes()
    activities  — last 14 days of intervals.icu activities (for rotation)
    workouts    — planned workouts for today (list of workout dicts from planner)
    weather     — weatherInfo string from context_builder
    race_in_days — int | None

Output (all fields optional / empty on error):
    shoes               — active shoe list with computed fields
    shoeRecommendation  — {primary: {...}, alternative: {...}}
    shoeWarnings        — list of warning dicts (≥ 80 % threshold)
    shoeFleetWarning    — {missing_types, soon_missing, suggestions}
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.utils.paths import resolve_config

logger = logging.getLogger(__name__)


def _equipment_md_path() -> Path:
    """Resolve equipment.md via CONFIG_DIR → CONFIG_FALLBACK."""
    try:
        return resolve_config("equipment.md")
    except FileNotFoundError:
        return Path()  # non-existent path; downstream code already handles missing file

# Terrain signal words (from weatherInfo or workout tags/notes)
_RAIN_WORDS = {"regen", "rain", "schauer", "nass", "schnee", "snow", "eis", "ice", "glatt"}

# Intensity → pace-range buckets (min/km)
_PACE_BUCKETS: dict[str, tuple[float, float]] = {
    "race": (2.5, 4.0),
    "tempo": (3.0, 4.5),
    "intervals": (3.0, 4.5),
    "z4": (3.0, 4.5),
    "easy": (4.5, 6.5),
    "z2": (4.5, 6.5),
    "long": (4.8, 7.0),
    "recovery": (5.5, 8.0),
    "z1": (5.5, 8.0),
}


# ── Profile loading ───────────────────────────────────────────────────────────

def load_shoe_profiles() -> list[dict]:
    """Parse shoe profiles from config/equipment.md.

    Profiles are YAML-like bullet lists under '## Laufschuhe'. A profile
    entry starts with an id line — `icu_gear_id:` (intervals.icu backend,
    the default), `strava_id:` (legacy Strava backend), or the neutral
    `gear_id:`. A profile may carry both ids during the migration window:
        - icu_gear_id: 'b1234567'
          strava_id: g123          # legacy, kept for reference
          name: "..."
          type: tempo
          role: daily
          ...
    """
    if not _equipment_md_path().exists():
        return []
    raw = _equipment_md_path().read_text()
    # Strip HTML comments before parsing
    text = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)

    # Extract section between '## Laufschuhe' / '## Running shoes' / '## Shoes'
    # and the next '##' heading.
    m = re.search(
        r"## (?:Laufschuhe|Running\s+shoes|Shoes)\b[^\n]*\n(.*?)(?=^##|\Z)",
        text, re.DOTALL | re.MULTILINE | re.IGNORECASE,
    )
    if not m:
        return []
    section = m.group(1)

    profiles: list[dict] = []
    current: dict | None = None

    for line in section.splitlines():
        # New profile starts with an id line: icu_gear_id / strava_id / gear_id
        if re.match(r"^\s*-\s+(?:icu_gear_id|strava_id|gear_id):", line):
            if current:
                profiles.append(current)
            current = {}
            _parse_kv(line.lstrip("- ").strip(), current)
        elif current is not None and re.match(r"^\s+\S", line):
            _parse_kv(line.strip(), current)
        elif line.strip() == "" and current:
            continue  # blank lines inside block ok

    if current:
        profiles.append(current)

    # Coerce types
    for p in profiles:
        if "threshold_km" in p:
            try:
                p["threshold_km"] = float(p["threshold_km"])
            except (ValueError, TypeError):
                p["threshold_km"] = 800.0
        if "race_prep_days" in p:
            try:
                p["race_prep_days"] = int(p["race_prep_days"])
            except (ValueError, TypeError):
                p["race_prep_days"] = 7
        if "pace_range_min_km" in p and isinstance(p["pace_range_min_km"], str):
            try:
                nums = re.findall(r"[\d.]+", p["pace_range_min_km"])
                p["pace_range_min_km"] = [float(nums[0]), float(nums[1])]
            except Exception:
                p["pace_range_min_km"] = [3.0, 8.0]
        if "recommended_tags" in p and isinstance(p["recommended_tags"], str):
            p["recommended_tags"] = re.findall(r"\w+", p["recommended_tags"])

    return profiles


def _parse_kv(line: str, target: dict) -> None:
    """Parse 'key: value  # comment' into target dict."""
    m = re.match(r"^([\w_-]+)\s*:\s*(.+?)(?:\s*#.*)?$", line)
    if not m:
        return
    k, v = m.group(1).strip(), m.group(2).strip().strip('"').strip("'")
    target[k] = v


# ── Backend-agnostic gear key ───────────────────────────────────────────────────

def profile_gear_key(profile: dict, backend: str) -> str:
    """Return the id a profile joins on for the active backend.

    intervals backend → `icu_gear_id` (fallback neutral `gear_id`).
    strava backend    → `strava_id`.
    """
    if backend == "strava":
        return str(profile.get("strava_id") or profile.get("gear_id") or "")
    return str(profile.get("icu_gear_id") or profile.get("gear_id") or "")


def gear_to_shoes(gear_list: list[dict]) -> list[dict]:
    """Map intervals.icu gear objects to the advisor's shoe-dict shape.

    Keeps only `type == "Shoes"`. intervals.icu gear `distance` is in metres
    (same as the Strava gear API), converted to km here. The gear `id`
    becomes `gear_key` (the join key) — and is also mirrored to `strava_id`
    so legacy field reads keep working in the intervals path.
    """
    shoes: list[dict] = []
    for g in gear_list:
        if (g.get("type") or "") != "Shoes":
            continue
        gid = str(g.get("id") or "")
        if not gid:
            continue
        shoes.append({
            "gear_key": gid,
            "strava_id": gid,  # generic id alias for legacy field reads
            "name": g.get("name") or "",
            "distance_km": round((g.get("distance") or 0) / 1000, 1),
            "retired": bool(g.get("retired", False)),
            "primary": bool(g.get("primary", False)),
        })
    return shoes


# ── Last-used lookup ──────────────────────────────────────────────────────────

def _compute_last_used(activities: list[dict]) -> dict[str, str]:
    """Return {strava_id: last_used_date_str} from intervals.icu activities.

    intervals.icu activities may carry gear info as 'gear_id' (Strava gear ID).
    Falls back gracefully if field is absent.
    """
    last: dict[str, str] = {}
    for a in sorted(activities, key=lambda x: (x.get("start_date_local") or ""), reverse=False):
        gear_id = a.get("gear_id") or a.get("icu_gear_id") or ""
        if not gear_id:
            continue
        date_str = (a.get("start_date_local") or "")[:10]
        if date_str:
            last[str(gear_id)] = date_str
    return last


from app.utils.paths import DATA_DIR as _DATA_DIR_ALIAS
_SHOE_LOG = _DATA_DIR_ALIAS / "shoe_log.json"


def _merge_shoe_log(last_used: dict[str, str], today_str: str) -> dict[str, str]:
    """Fill gaps in last_used (from Strava gear_id) with local shoe-log fallback.

    Strava gear_id is the source of truth for what was actually worn. The local
    log only tracks coach *recommendations* and is therefore used solely to
    fill in shoes that the Strava lookup did not cover (e.g. shoes not worn in
    the activities window, or Strava temporarily unavailable).
    """
    try:
        if not _SHOE_LOG.exists():
            return last_used
        import json
        log: dict[str, str] = json.loads(_SHOE_LOG.read_text())
        merged = dict(last_used)
        for sid, log_date in log.items():
            if sid not in merged:
                merged[sid] = log_date
        return merged
    except Exception:
        return last_used


def write_shoe_log(strava_id: str, date_str: str) -> None:
    """Persist recommended shoe as fallback when Strava activities are unavailable.

    Only call this when recent Strava activities could not be fetched — otherwise
    the recommendation log would shadow the real `gear_id` data and skew rotation
    (every recommendation would count as 'worn today').
    """
    import json
    try:
        _SHOE_LOG.parent.mkdir(parents=True, exist_ok=True)
        log: dict[str, str] = {}
        if _SHOE_LOG.exists():
            log = json.loads(_SHOE_LOG.read_text())
        if log.get(strava_id, "") < date_str:
            log[strava_id] = date_str
        _SHOE_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.warning("shoe_log write failed: %s", e)


# ── Terrain detection ─────────────────────────────────────────────────────────

def _detect_terrain_from_context(workout: dict, weather_info: str) -> str:
    """Return 'trail', 'track', or 'asphalt'.

    Priority order:
      1. Explicit `surface` field on the workout (set by specialist-endurance):
         asphalt | forstweg | trail | track | treadmill
      2. Tags ('trail' or 'track')
      3. Coaching-notes keyword scan (fallback only — explicit field preferred)
    """
    surface = (workout.get("surface") or "").lower().strip()
    if surface:
        if surface in ("trail", "weichboden"):
            return "trail"
        if surface in ("track", "bahn"):
            return "track"
        # asphalt, forstweg (fest gepackt), treadmill → asphalt-equivalent
        return "asphalt"

    tags = [t.lower() for t in (workout.get("tags") or [])]
    notes = (workout.get("coaching_notes") or "").lower()
    # Bilingual trail-surface keywords — match coaching notes regardless of
    # whether the coach wrote them in German or English.
    _TRAIL_WORDS = {
        "trail", "cross", "off-road", "dirt",
        # English
        "forest path", "meadow", "soft ground", "terrain",
        # German
        "waldweg", "wald", "wiese", "weichboden", "gelände",
    }
    if "trail" in tags or any(w in notes for w in _TRAIL_WORDS):
        return "trail"
    if "track" in tags or "bahn" in notes or "track" in notes:
        return "track"
    return "asphalt"


def _is_wet_weather(weather_info: str) -> bool:
    w = weather_info.lower()
    return any(word in w for word in _RAIN_WORDS)


# ── Pace bucket ───────────────────────────────────────────────────────────────

def _derive_pace_bucket(workout: dict) -> tuple[float, float] | None:
    """Return (min_pace, max_pace) in min/km from workout metadata."""
    tags = [t.lower() for t in (workout.get("tags") or [])]
    intensity = (workout.get("intensity") or "").lower()
    wtype = (workout.get("workout_type") or "").lower()

    for key in (*tags, intensity, wtype):
        if key in _PACE_BUCKETS:
            return _PACE_BUCKETS[key]
    return None


# ── Candidate scoring ─────────────────────────────────────────────────────────

def _days_ago(date_str: str, today_str: str) -> int:
    from datetime import date
    try:
        d1 = date.fromisoformat(today_str)
        d2 = date.fromisoformat(date_str)
        return (d1 - d2).days
    except Exception:
        return 0


def _score_shoe(
    profile: dict,
    shoe: dict,
    terrain: str,
    wet: bool,
    pace_bucket: tuple[float, float] | None,
    race_in_days: int | None,
    today_str: str,
    last_used: dict[str, str],
    workout_type: str = "",
) -> float | None:
    """Return a score ≥ 0 or None if the shoe is disqualified.

    Higher score = better recommendation.
    """
    role = profile.get("role", "daily")
    sid = profile.get("gear_key") or str(profile.get("strava_id") or "")
    threshold = float(profile.get("threshold_km", 800))
    distance_km = shoe.get("distance_km", 0)
    pct = distance_km / threshold if threshold else 0

    # ── Hard filters (return None = disqualified) ──────────────────────

    # 1. Race-day lock
    if role == "race":
        race_prep_days = int(profile.get("race_prep_days", 7))
        is_race_workout = workout_type.upper() == "RACE"
        in_prep_window = race_in_days is not None and race_in_days <= race_prep_days
        if not (is_race_workout or in_prep_window):
            return None

    # 2. required_workout_type (e.g. recovery-only shoes)
    req_wt = profile.get("required_workout_type", "")
    if req_wt and workout_type.upper() != req_wt.upper():
        return None

    # 4. Terrain match
    shoe_terrain = profile.get("terrain", "asphalt")
    if terrain == "trail" and shoe_terrain not in ("trail", "mixed"):
        return None
    if terrain in ("asphalt", "track") and shoe_terrain == "trail":
        return None

    # 5. Pace match
    if pace_bucket:
        pace_range = profile.get("pace_range_min_km")
        if pace_range and len(pace_range) == 2:
            shoe_min, shoe_max = pace_range
            req_min, req_max = pace_bucket
            # Require ≥ 50 % overlap between required pace range and shoe range
            overlap = min(shoe_max, req_max) - max(shoe_min, req_min)
            if overlap < (req_max - req_min) * 0.5:
                return None

    # ── Scoring (higher = better) ──────────────────────────────────────

    score = 0.0

    # Wet weather: prefer trail/mixed terrain
    if wet and shoe_terrain in ("trail", "mixed"):
        score += 10.0

    # Mileage penalty: deprioritise worn shoes for hard sessions
    if pct >= 0.9:
        score -= 20.0
    elif pct >= 0.8:
        score -= 8.0

    # Rotation bonus: reward longest rest
    last = last_used.get(sid)
    if last:
        days_rest = _days_ago(last, today_str)
        score += min(days_rest, 14) * 2.0  # up to +28
    else:
        score += 14.0  # never used → treat as longest rest

    return score


# ── Main entry point ──────────────────────────────────────────────────────────

def build_shoe_context(
    shoes: list[dict],
    profiles: list[dict],
    activities: list[dict],
    planned_workouts: list[dict],
    weather_info: str,
    race_in_days: int | None,
    today_str: str,
    backend: str = "strava",
) -> dict:
    """Build shoe context dict for context_builder output.

    `backend` selects the join key between shoe data and equipment.md
    profiles: 'intervals' joins on `icu_gear_id`, 'strava' on `strava_id`
    (see `profile_gear_key`). Both reduce to a per-item `gear_key`, so the
    scoring/rotation logic below is backend-agnostic.

    Returns:
        shoes, shoeRecommendation, shoeWarnings, shoeFleetWarning
    """
    # Reduce every profile and shoe to a single join key for the backend.
    for p in profiles:
        p["gear_key"] = profile_gear_key(p, backend)
    for s in shoes:
        s.setdefault("gear_key", str(s.get("strava_id") or ""))

    profile_map = {p["gear_key"]: p for p in profiles if p.get("gear_key")}
    shoe_map = {s["gear_key"]: s for s in shoes if s.get("gear_key")}

    # Active shoes only: exclude retired + equipment.md active:false
    active_shoes = [
        s for s in shoes
        if not s.get("retired")
        and profile_map.get(s["gear_key"], {}).get("active", "true") not in ("false", False)
    ]

    last_used = _compute_last_used(activities)
    # Merge local shoe log (fallback when intervals.icu gear_id is absent)
    last_used = _merge_shoe_log(last_used, today_str)

    # Enrich active shoes with computed fields
    enriched: list[dict] = []
    for s in active_shoes:
        sid = s["gear_key"]
        p = profile_map.get(sid, {})
        threshold = float(p.get("threshold_km", 800))
        dist = s.get("distance_km", 0)
        pct = round(dist / threshold * 100, 1) if threshold else 0
        lu = last_used.get(sid)
        enriched.append({
            **s,
            "type": p.get("type", ""),
            "role": p.get("role", "daily"),
            "primary_race": p.get("primary_race") in (True, "true"),
            "terrain": p.get("terrain", "asphalt"),
            "threshold_km": threshold,
            "pct_used": pct,
            "last_used_date": lu,
            "days_since_used": _days_ago(lu, today_str) if lu else None,
        })

    # ── Warnings (≥ 80 %) ────────────────────────────────────────────
    warnings: list[dict] = []
    for s in enriched:
        if s["role"] == "race":
            continue  # race shoes: higher threshold, don't warn on standard %
        if s["pct_used"] >= 80:
            warnings.append({
                "strava_id": s["strava_id"],
                "name": s["name"],
                "distance_km": s["distance_km"],
                "threshold_km": s["threshold_km"],
                "pct_used": s["pct_used"],
                "msg": (
                    f"⚠ {s['name']}: {s['distance_km']:.0f} km von {s['threshold_km']:.0f} km "
                    f"({s['pct_used']:.0f} %) — bald erneuern."
                ),
            })

    # ── Recommendation (for first run workout found) ─────────────────
    recommendation: dict = {}
    run_workout = next(
        (w for w in planned_workouts if w.get("type") in ("Run",)), None
    )
    if run_workout and enriched:
        wet = _is_wet_weather(weather_info)
        terrain = _detect_terrain_from_context(run_workout, weather_info)
        pace_bucket = _derive_pace_bucket(run_workout)

        scored: list[tuple[float, dict]] = []
        for s in enriched:
            p = profile_map.get(s["gear_key"], {})
            sc = _score_shoe(
                p, s, terrain, wet, pace_bucket,
                race_in_days, today_str, last_used,
                workout_type=run_workout.get("workout_type") or "",
            )
            if sc is not None:
                scored.append((sc, s))

        scored.sort(key=lambda x: x[0], reverse=True)

        def _rec_entry(score: float, s: dict) -> dict:
            p = profile_map.get(s["gear_key"], {})
            reasons = []
            if s.get("days_since_used") is not None:
                reasons.append(f"{s['days_since_used']} days unused")
            if wet and s.get("terrain") in ("trail", "mixed"):
                reasons.append("grip in the wet")
            if not reasons:
                reasons.append(f"type: {p.get('type', '?')}, terrain: {p.get('terrain', '?')}")
            return {
                "gear_id": s["gear_key"],
                "strava_id": s.get("strava_id"),  # legacy alias
                "name": s["name"],
                "distance_km": s["distance_km"],
                "pct_used": s["pct_used"],
                "reason": ", ".join(reasons),
            }

        if scored:
            recommendation["primary"] = _rec_entry(*scored[0])
        if len(scored) >= 2:
            recommendation["alternative"] = _rec_entry(*scored[1])

    # ── Fleet gap detection ───────────────────────────────────────────
    active_types = {profile_map.get(s["gear_key"], {}).get("type", "") for s in enriched}
    active_types.discard("")

    all_types = {"tempo", "easy", "long", "trail", "recovery"}
    missing_types = sorted(all_types - active_types)

    # Soon-missing: sole shoe of its type and > 80 %
    type_counts: dict[str, list[dict]] = {}
    for s in enriched:
        t = profile_map.get(s["gear_key"], {}).get("type", "")
        if t:
            type_counts.setdefault(t, []).append(s)

    soon_missing: list[str] = []
    for t, shoes_of_type in type_counts.items():
        if len(shoes_of_type) == 1 and shoes_of_type[0]["pct_used"] >= 80:
            soon_missing.append(t)

    # Suggestions from equipment.md '## Bevorzugte Modelle' section
    suggestions = _load_preferred_models(missing_types + soon_missing)

    fleet_warning: dict[str, Any] = {}
    if missing_types or soon_missing:
        fleet_warning = {
            "missing_types": missing_types,
            "soon_missing": soon_missing,
            "suggestions": suggestions,
        }

    return {
        "shoes": enriched,
        "shoeRecommendation": recommendation,
        "shoeWarnings": warnings,
        "shoeFleetWarning": fleet_warning,
    }


def _load_preferred_models(types: list[str]) -> dict[str, str]:
    """Extract preferred model suggestions from config/equipment.md."""
    if not types or not _equipment_md_path().exists():
        return {}
    text = _equipment_md_path().read_text()
    m = re.search(
        r"## Bevorzugte Modelle pro Kategorie\b(.*?)(?=^##|\Z)", text, re.DOTALL | re.MULTILINE
    )
    if not m:
        return {}
    section = m.group(1)
    result: dict[str, str] = {}
    for line in section.splitlines():
        for t in types:
            if re.search(rf"^\s*[-*]\s*{re.escape(t)}\s*:", line, re.IGNORECASE):
                # Strip bullet and "type: " prefix → keep only model names
                clean = re.sub(rf"^\s*[-*]\s*{re.escape(t)}\s*:\s*", "", line, flags=re.IGNORECASE).strip()
                if clean:
                    result[t] = clean
    return result
