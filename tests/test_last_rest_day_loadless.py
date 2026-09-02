"""lastRestDay must distinguish a full rest day from a load-less day.

Regression source: a recovery day was argued from "no rest day in the last
7 days" while the day in question held only a 14-minute bodyweight block and
a short grip block. The framework already carried that rule in prose; the
field said otherwise, and the field won.
"""

from datetime import date

from app.graphs.sub_athlete_context.context_builder import _find_last_rest_day

TODAY = date(2026, 9, 2)


def _a(d, typ, name, minutes, load=None):
    return {
        "start_date_local": f"{d}T09:00:00",
        "type": typ,
        "name": name,
        "moving_time": minutes * 60,
        "icu_training_load": load,
    }


def _full_week(exclude=None):
    """One real run per day for the last 7 days, minus the excluded date."""
    from datetime import timedelta

    out = []
    for day in range(1, 8):
        d = (TODAY - timedelta(days=day)).isoformat()
        if d == exclude:
            continue
        out.append(_a(d, "Run", "Easy", 50, 40))
    return out


def test_empty_day_is_a_full_rest_day():
    out = _find_last_rest_day(_full_week(exclude="2026-08-30"), TODAY)
    assert out == "3 days ago"


def test_loadless_day_is_reported_not_masked():
    acts = _full_week(exclude="2026-08-31")
    acts += [
        _a("2026-08-31", "WeightTraining", "Glute-Reaktivierung", 14),
        _a("2026-08-31", "WeightTraining", "Griffkraft-Kurzblock", 17),
    ]
    out = _find_last_rest_day(acts, TODAY)
    assert "LOAD-LESS" in out
    assert "Glute-Reaktivierung" in out and "Griffkraft-Kurzblock" in out
    assert "31 min" in out
    assert "rest is overdue" in out


def test_an_endurance_session_is_never_loadless():
    acts = _full_week(exclude="2026-08-31")
    acts.append(_a("2026-08-31", "Ride", "Rollen-Cruise", 30, None))
    assert _find_last_rest_day(acts, TODAY) == "no rest day in the last 7 days"


def test_a_scored_strength_session_is_never_loadless():
    acts = _full_week(exclude="2026-08-31")
    acts.append(_a("2026-08-31", "WeightTraining", "Bein-Block", 40, 35))
    assert _find_last_rest_day(acts, TODAY) == "no rest day in the last 7 days"


def test_long_accessory_day_is_not_loadless():
    """A 70-minute block is a session, not an activation snack."""
    acts = _full_week(exclude="2026-08-31")
    acts.append(_a("2026-08-31", "WeightTraining", "Langer Block", 70))
    assert _find_last_rest_day(acts, TODAY) == "no rest day in the last 7 days"


def test_full_rest_wins_over_a_more_distant_loadless_day():
    """Yesterday empty, two days ago load-less — the empty day is reported."""
    acts = [a for a in _full_week(exclude="2026-09-01")
            if not a["start_date_local"].startswith("2026-08-31")]
    acts.append(_a("2026-08-31", "WeightTraining", "Mobility", 15))
    assert _find_last_rest_day(acts, TODAY) == "yesterday"
