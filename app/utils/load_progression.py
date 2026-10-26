"""Load-progression rules: single-session spike, quality density, calendar deload.

One implementation for the context (``deloadDue``) and the validator
(R033 / R034 / R035) — the same split as ``impact_load``: two
implementations of one rule eventually disagree.

Evidence status (see ``research/load-management-groin-overuse-runners.md``):

- **Single-session spike** (R033): the only running-specific signal with a
  cohort behind it (prospective cohort, all overuse injuries, no groin
  statement). The 10 % bin edge is a *convention* taken from the study's
  categories; the authors themselves suggest a cut-off below 10 %. Never
  blocking, and a run under the threshold is not thereby declared safe.
- **Quality density** (R034) and **calendar deload** (R035): no prevention
  evidence for or against. These are athlete decisions (opt-in
  configuration); every parameter here (7-day window, 48 h spacing, the
  15 min block that makes a long run a quality run, 3:1 rhythm, 30 %
  reduction) is a *working assumption*. Weekly ratios (ACWR, week-to-week
  percent) are deliberately **not** implemented — the running cohorts do not
  support them as an injury gate.

Athlete configuration lives in ``config/athlete_status.md`` (machine
readable keys, parsed by :func:`parse_load_rules`).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from app.utils.activity_helpers import activity_date
from app.utils.date_parse import parse_config_date
from app.utils.impact_load import (
    IMPACT_TYPES,
    LONG_RUN_MIN_MINUTES,
    _duration_minutes,
    _is_quality,
)

# ───────────────────────── configuration ─────────────────────────

SPIKE_DEFAULT_PCT = 10.0  # convention (study bin edge); WARNING only
QUALITY_SPACING_DEFAULT_H = 48.0  # practitioner convention
DELOAD_REDUCTION_DEFAULT_PCT = 30.0  # working assumption, no injury evidence
LONG_RUN_MODES = ("block", "all", "none")
# A long run counts as a quality run when it embeds this much cumulative
# race-pace / threshold-class work. Working assumption, no source.
LONG_RUN_BLOCK_MIN_MINUTES = 15
# Non-long runs: cumulative hard-step time that makes a run a quality run
# (keeps a few Z5 strides from counting as a quality session).
QUALITY_HARD_MIN_SECONDS = 180

_UNSET = object()


def _read_key(text: str, key: str):
    """Value of ``key`` in athlete_status-style text.

    Returns ``_UNSET`` when the key is absent, ``""`` when present but empty.
    Accepts ``key: v``, ``- **key:** v`` and ``**key**: v``; trailing ``#``
    comments are stripped. Same-line only, so an empty value never swallows
    the next line.
    """
    m = re.search(
        rf"^[ \t]*(?:[-*][ \t]+)?\**{re.escape(key)}\**[ \t]*[:=]\**[ \t]*([^#\n]*)",
        text or "",
        re.IGNORECASE | re.MULTILINE,
    )
    if not m:
        return _UNSET
    return m.group(1).strip().strip("`*").strip()


def _num(text: str, key: str, default, *, off_when_empty: bool = True):
    raw = _read_key(text, key)
    if raw is _UNSET:
        return default
    if raw == "":
        return None if off_when_empty else default
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return default


def _choice(text: str, key: str, allowed: tuple[str, ...], default: str) -> str:
    raw = _read_key(text, key)
    if raw is _UNSET or raw == "":
        return default
    raw = raw.lower()
    return raw if raw in allowed else default


def parse_load_rules(status_text: str | None) -> dict:
    """Parse the load-progression keys of ``config/athlete_status.md``.

    Absent or empty opt-in keys (``quality_runs_max_7d``,
    ``deload_every_n_weeks``) are ``None`` = rule off. ``session_spike_warn_pct``
    defaults to 10 when absent and is off when present but empty.
    """
    t = status_text or ""
    max7 = _num(t, "quality_runs_max_7d", None)
    every = _num(t, "deload_every_n_weeks", None)
    return {
        "session_spike_warn_pct": _num(t, "session_spike_warn_pct", SPIKE_DEFAULT_PCT),
        "quality_runs_max_7d": int(max7) if max7 else None,
        "quality_min_spacing_h": _num(
            t, "quality_min_spacing_h", QUALITY_SPACING_DEFAULT_H, off_when_empty=False
        ),
        "long_run_quality_mode": _choice(t, "long_run_quality_mode", LONG_RUN_MODES, "block"),
        "quality_density_severity": _choice(
            t, "quality_density_severity", ("warning", "error"), "warning"
        ),
        "deload_every_n_weeks": int(every) if every else None,
        "deload_reduction_pct": _num(
            t, "deload_reduction_pct", DELOAD_REDUCTION_DEFAULT_PCT, off_when_empty=False
        ),
        "deload_severity": _choice(t, "deload_severity", ("warning", "error"), "warning"),
    }


# ───────────────────────── activity shape helpers ─────────────────────────

def _date_of(a: dict) -> str:
    """ISO date of an activity/workout dict (``date`` or ``start_date_local``)."""
    return (a.get("date") or activity_date(a) or "")[:10]


def _is_run(a: dict) -> bool:
    return (a.get("type") or "") in IMPACT_TYPES


def _text(a: dict) -> str:
    return f"{a.get('intervals_icu') or ''}\n{a.get('description') or ''}"


def _distance_km(a: dict) -> float | None:
    """Distance in km, tolerating ``distance_km`` and raw ``distance`` (metres)."""
    if a.get("distance_km") not in (None, ""):
        try:
            return float(a["distance_km"])
        except (TypeError, ValueError):
            return None
    if a.get("distance") not in (None, ""):
        try:
            return float(a["distance"]) / 1000.0
        except (TypeError, ValueError):
            return None
    return None


def is_race(a: dict) -> bool:
    tags = {str(t).lower() for t in (a.get("tags") or [])}
    wtype = (a.get("workout_type") or "").upper()
    cat = (a.get("category") or "").upper()
    return (
        "race" in tags
        or wtype == "RACE"
        or cat.startswith("RACE")
        or bool(a.get("race"))
        or bool(re.search(r"\b(race|wettkampf)\b", a.get("name") or "", re.IGNORECASE))
    )


# ───────────────────────── quality-run definition ─────────────────────────

# Hard-step signature (threshold class and harder): Z4/Z5 HR targets or
# >= 95 % LTHR. Shared by R017 and the quality-run definition below.
HARD_SIGNATURE_RE = re.compile(
    r"\bZ4\s*HR\b|\bZ5\s*HR\b|(?<!\d)(?:9[5-9]|1\d\d)\s*%\s*LTHR\b",
    re.IGNORECASE,
)
# Race-pace / threshold wording that is not an HR target.
_PACE_BLOCK_RE = re.compile(
    r"race[-\s]?pace|renntempo|wettkampftempo|\bhm[-\s]?(?:pace|tempo)\b|"
    r"halbmarathon[-\s]?tempo|\bthreshold\b|\bschwelle",
    re.IGNORECASE,
)
_STEP_MIN_RE = re.compile(r"\b(\d+)m\b", re.IGNORECASE)
_STEP_SEC_RE = re.compile(r"\b(\d+)s\b", re.IGNORECASE)
_REPEAT_RE = re.compile(r"^\s*(\d+)\s*x\b", re.IGNORECASE)


def step_duration_seconds(text: str) -> int:
    """Duration of an intervals_icu step in seconds (``8m``, ``90s``, ``1m30s``); 0 if none."""
    secs = 0
    m = _STEP_MIN_RE.search(text)
    if m:
        secs += int(m.group(1)) * 60
    s = _STEP_SEC_RE.search(text)
    if s:
        secs += int(s.group(1))
    return secs


def hard_block_seconds(text: str) -> int:
    """Cumulative duration of hard / race-pace steps in an intervals_icu text.

    Steps are ``- ...`` lines; ``Nx`` header lines multiply the steps that
    follow until the next blank line.
    """
    total = 0
    mult = 1
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            mult = 1
            continue
        rep = _REPEAT_RE.match(line)
        if rep and not line.startswith("-"):
            mult = int(rep.group(1))
            continue
        if not line.startswith("-"):
            continue
        if HARD_SIGNATURE_RE.search(line) or _PACE_BLOCK_RE.search(line):
            total += step_duration_seconds(line) * mult
    return total


def is_long_run(a: dict, long_run_min_minutes: int = LONG_RUN_MIN_MINUTES) -> bool:
    return _is_run(a) and _duration_minutes(a) >= long_run_min_minutes


def is_quality_run(a: dict, long_run_mode: str = "block") -> bool:
    """The single definition of a quality run (R034, deload gate).

    Counts: threshold class and harder, races, and a long run that embeds a
    race-pace / threshold block of at least ``LONG_RUN_BLOCK_MIN_MINUTES``.
    A pure Z2 long run does not count (it still goes through R033).

    ``long_run_mode``: ``block`` (default) = long run counts only with an
    embedded block; ``all`` = every long run counts; ``none`` = a long run
    never counts (except as a race).
    """
    if not _is_run(a):
        return False
    if is_race(a):
        return True
    if is_long_run(a):
        if long_run_mode == "all":
            return True
        if long_run_mode == "none":
            return False
        text = _text(a)
        if any(ln.strip().startswith("-") for ln in text.splitlines()):
            return hard_block_seconds(text) >= LONG_RUN_BLOCK_MIN_MINUTES * 60
        # No structured text to inspect: fall back to the explicit markers.
        tags = {str(t).lower() for t in (a.get("tags") or [])}
        return "intervals" in tags or (a.get("workout_type") or "").upper() in {
            "INTERVALS",
            "THRESHOLD",
        }
    if _is_quality(a):
        return True
    return hard_block_seconds(_text(a)) >= QUALITY_HARD_MIN_SECONDS


# ───────────────────────── R033: single-session spike ─────────────────────────

def longest_run_30d(activities: list[dict], today: date, window_days: int = 30) -> dict | None:
    """Longest run in the ``window_days`` before ``today`` (today excluded).

    Returns ``{"minutes", "km", "date"}`` (``km`` None when no run carries a
    distance) or None when there was no run in the window.
    """
    lo = (today - timedelta(days=window_days)).isoformat()
    hi = today.isoformat()
    runs = [a for a in activities or [] if _is_run(a) and lo <= _date_of(a) < hi]
    if not runs:
        return None
    longest_min = max(runs, key=_duration_minutes)
    kms = [k for k in (_distance_km(a) for a in runs) if k]
    return {
        "minutes": _duration_minutes(longest_min),
        "km": max(kms) if kms else None,
        "date": _date_of(longest_min),
    }


def spike_band(ratio: float) -> str:
    """Name of the study bin a ratio falls in (> 10-30 / > 30-100 / > 100 %)."""
    if ratio > 2.0:
        return "> 100 %"
    if ratio > 1.30:
        return "> 30-100 %"
    return "> 10-30 %"


def session_spike(planned: dict, reference: dict, warn_pct: float) -> dict | None:
    """Compare one planned run with the 30-day longest run.

    Uses distance when both the plan and the reference carry one, otherwise
    duration (a proxy — labelled as such in the result). Returns None when
    the run is not above the threshold.
    """
    measure, value, ref = "duration (proxy)", float(planned.get("duration_min") or 0), reference["minutes"]
    pk = _distance_km(planned)
    if pk and reference.get("km"):
        measure, value, ref = "distance", pk, reference["km"]
    if not value or not ref:
        return None
    ratio = value / ref
    if ratio <= 1 + warn_pct / 100.0:
        return None
    return {
        "ratio": ratio,
        "measure": measure,
        "value": value,
        "reference": ref,
        "reference_date": reference["date"],
        "band": spike_band(ratio),
    }


# ───────────────────────── R034: quality density ─────────────────────────

def _when(a: dict) -> datetime:
    """Start of an activity/workout; date at 12:00 when no clock time is known."""
    for key in ("start_date_local", "start_time", "start"):
        raw = a.get(key)
        if raw:
            try:
                return datetime.fromisoformat(str(raw).replace("Z", ""))
            except ValueError:
                pass
    d = _date_of(a)
    try:
        return datetime.fromisoformat(d + "T12:00:00")
    except ValueError:
        return datetime.min


def quality_density(
    planned_quality: list[dict],
    history: list[dict],
    today: date,
    *,
    max_7d: int,
    min_spacing_h: float,
    long_run_mode: str,
) -> dict:
    """Rolling-7-day quality count and spacing, planned plus completed.

    ``planned_quality`` are today's planned quality runs. Returns
    ``{"count_7d", "violations": [...], "done": [dates]}``; no violations =
    compliant.
    """
    lo = (today - timedelta(days=6)).isoformat()
    hi = today.isoformat()
    done = sorted(
        (a for a in history or [] if _is_run(a) and lo <= _date_of(a) <= hi
         and is_quality_run(a, long_run_mode)),
        key=_when,
    )
    # Spacing looks further back than the count window (48 h < 7 d, so the
    # 7-day slice is enough for any spacing <= 168 h).
    count = len(done) + len(planned_quality)
    violations: list[str] = []
    if count > max_7d:
        violations.append(
            f"{count} quality runs in the rolling 7 days (max {max_7d}): "
            f"{len(done)} done + {len(planned_quality)} planned"
        )
    for p in planned_quality:
        tp = _when(p)
        for q in done + [x for x in planned_quality if x is not p]:
            gap_h = abs((tp - _when(q)).total_seconds()) / 3600.0
            if gap_h < min_spacing_h:
                violations.append(
                    f"only {gap_h:.0f} h to the quality run on {_date_of(q)} "
                    f"(min {min_spacing_h:.0f} h)"
                )
                break
    return {
        "count_7d": count,
        "violations": list(dict.fromkeys(violations)),
        "done": [_date_of(a) for a in done],
    }


# ───────────────────────── R035 / deloadDue: calendar deload ─────────────────────────

def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def weekly_run_minutes(activities: list[dict], week_start: date) -> float:
    lo, hi = week_start.isoformat(), (week_start + timedelta(days=7)).isoformat()
    return sum(
        _duration_minutes(a)
        for a in activities or []
        if _is_run(a) and lo <= _date_of(a) < hi
    )


def recovery_block_active(deload_state: dict | None, today: date) -> bool:
    """True when the recovery-week block is set and not past its planned end."""
    if not deload_state:
        return False
    raw = str(deload_state.get("aktiv") or deload_state.get("active") or "").strip().lower()
    if raw not in ("ja", "yes", "true"):
        return False
    end = parse_config_date(deload_state.get("ende_geplant") or deload_state.get("planned_end"))
    return end is None or end >= today


def compute_deload_due(
    activities: list[dict],
    today: date,
    *,
    every_n_weeks: int,
    reduction_pct: float = DELOAD_REDUCTION_DEFAULT_PCT,
    deload_state: dict | None = None,
    history_start: date | None = None,
) -> dict:
    """Is a deload week due in the calendar week containing ``today``?

    Weeks are Monday-Sunday. A completed week counts as a *reduction week*
    when its run volume (minutes — the one measure every run carries; belt
    distances are unreliable) is at most ``100 - reduction_pct`` % of the mean
    of the three weeks before it, whatever the reason (illness and travel
    weeks included). The counter walks back from the last completed week
    over consecutive non-reduction ("build") weeks; ``due`` once it reaches
    ``every_n_weeks``. A week with no running baseline behind it ends the
    walk. ``reduction_pct`` and the 3:1 rhythm are working assumptions.

    ``history_start`` (first day the activity list can be trusted to cover)
    stops the walk where the data ends; ``history_complete`` then reads False.
    """
    threshold = (100.0 - reduction_pct) / 100.0
    this_week = _monday(today)
    weeks_since = 0
    history_complete = True
    reason = "counter reached the configured rhythm"
    k = 1
    while weeks_since < every_n_weeks:
        wk = this_week - timedelta(weeks=k)
        oldest_needed = wk - timedelta(weeks=3)
        if history_start is not None and oldest_needed < history_start:
            history_complete = False
            reason = "history ends before the walk could finish"
            break
        prev = [weekly_run_minutes(activities, wk - timedelta(weeks=i)) for i in (1, 2, 3)]
        mean_prev = sum(prev) / 3.0
        if mean_prev <= 0:
            reason = "no running baseline before this week"
            break
        vol = weekly_run_minutes(activities, wk)
        if vol <= threshold * mean_prev:
            reason = f"week of {wk.isoformat()} was a reduction week"
            break
        weeks_since += 1
        k += 1
    due = weeks_since >= every_n_weeks
    return {
        "due": due,
        "weeks_since_last_reduction": weeks_since,
        "every_n_weeks": every_n_weeks,
        "reduction_threshold_pct": round(threshold * 100),
        "recovery_week_active": recovery_block_active(deload_state, today),
        "history_complete": history_complete,
        "week_start": this_week.isoformat(),
        "basis": f"run minutes per Mon-Sun week; {reason}",
    }
