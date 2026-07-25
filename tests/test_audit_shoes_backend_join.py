"""Regression + coverage tests for scripts.audit_consistency.check_shoes.

Prior regression (the bug this test exists for): the SHOES check crashed
with ``KeyError: 'strava_id'`` when equipment.md contained a profile
that declared only ``icu_gear_id:`` (no legacy ``strava_id:``) — the
set-comprehension ``{p["strava_id"] for p in profiles}`` blew up on the
first such profile and the whole check aborted, silently disabling the
``shoe_unprofiled`` / ``shoe_profile_orphan`` / ``shoe_threshold_reached``
findings class.

These tests lock in the backend-neutral join (``profile_gear_key``) and
the "no silent skip" property: a profile without a backend-side join key
must surface as its own ``shoe_profile_missing_gear_key`` finding.

All fixtures are synthetic (made-up gear ids / km / dates), never real
athlete data.
"""
from __future__ import annotations

from unittest.mock import patch

from scripts import audit_consistency


# ── Regression: profile with only icu_gear_id at backend='intervals' ────────


def test_intervals_backend_joins_icu_only_profile_without_keyerror() -> None:
    """The exact regression: no strava_id in the profile, backend=intervals.

    Before the fix this raised KeyError('strava_id') on the profile-set
    comprehension. The check must now run through, join the profile on
    its icu_gear_id, and — with a matching active shoe present — emit
    zero shoe findings.
    """
    profiles = [
        {
            "icu_gear_id": "iAAA111",
            "name": "Synthetic Trainer",
            "type": "easy",
            "role": "daily",
            "terrain": "asphalt",
            "threshold_km": 800,
        },
    ]
    shoes = [
        {
            "gear_key": "iAAA111",
            "strava_id": "iAAA111",  # gear_to_shoes mirrors id to strava_id
            "name": "Synthetic Trainer",
            "distance_km": 120.0,
            "retired": False,
        },
    ]
    with patch.object(
        audit_consistency, "load_shoe_profiles", create=True, new=lambda: profiles
    ), patch(
        "app.graphs.shoe_advisor.load_shoe_profiles", return_value=profiles
    ):
        findings = audit_consistency.check_shoes(shoes, backend="intervals")

    assert findings == [], (
        "backend=intervals + icu_gear_id-only profile must join cleanly and "
        f"produce no findings; got {findings!r}"
    )


# ── Backend symmetry: same logic works for backend='strava' ─────────────────


def test_strava_backend_joins_strava_only_profile() -> None:
    """Backend-symmetry: strava profile joins on strava_id at backend=strava.

    Guards against a fix that just flipped the hardcoded key from
    ``strava_id`` to ``icu_gear_id``; the join must be *backend-neutral*,
    not hardcoded to intervals.
    """
    profiles = [
        {
            "strava_id": "gBBB222",
            "name": "Synthetic Racer",
            "type": "race",
            "role": "race",
            "terrain": "asphalt",
            "threshold_km": 400,
        },
    ]
    shoes = [
        {
            "strava_id": "gBBB222",  # Strava-native shape carries no gear_key
            "name": "Synthetic Racer",
            "distance_km": 42.0,
            "retired": False,
        },
    ]
    with patch("app.graphs.shoe_advisor.load_shoe_profiles", return_value=profiles):
        findings = audit_consistency.check_shoes(shoes, backend="strava")

    assert findings == [], (
        "backend=strava + strava_id-only profile must join cleanly and "
        f"produce no findings; got {findings!r}"
    )


# ── No silent skip: profile without a backend-side join key surfaces ────────


def test_profile_without_backend_key_surfaces_missing_gear_key_finding() -> None:
    """The property the fix protects against future refactors.

    If a profile has *no* join key for the active backend (here: a
    strava-only profile while backend=intervals), the check must NOT
    silently drop it. It must emit a ``shoe_profile_missing_gear_key``
    finding so the misconfiguration stays visible in the audit report.
    """
    profiles = [
        {
            "strava_id": "gCCC333",  # no icu_gear_id, no neutral gear_id
            "name": "Synthetic Orphan",
            "type": "easy",
            "role": "daily",
        },
        # a well-formed profile in the same load, to prove the check
        # continues past the bad one instead of aborting.
        {
            "icu_gear_id": "iDDD444",
            "name": "Synthetic Good Trainer",
            "type": "easy",
            "role": "daily",
            "threshold_km": 800,
        },
    ]
    shoes = [
        {
            "gear_key": "iDDD444",
            "strava_id": "iDDD444",
            "name": "Synthetic Good Trainer",
            "distance_km": 50.0,
            "retired": False,
        },
    ]
    with patch("app.graphs.shoe_advisor.load_shoe_profiles", return_value=profiles):
        findings = audit_consistency.check_shoes(shoes, backend="intervals")

    missing = [f for f in findings if f["category"] == "shoe_profile_missing_gear_key"]
    assert len(missing) == 1, (
        "profile without an intervals-side join key must produce exactly one "
        f"shoe_profile_missing_gear_key finding; got {findings!r}"
    )
    assert missing[0]["severity"] == "MEDIUM"
    assert missing[0]["source_file"] == "config/equipment.md"
    # Evidence must name the offending profile so the report is actionable.
    assert "Synthetic Orphan" in missing[0]["evidence"]
    # And it must name the field the loader looked for on that backend.
    assert "icu_gear_id" in missing[0]["evidence"]

    # No stray unprofiled/orphan finding for the well-formed shoe — the good
    # profile still joined normally past the bad one.
    assert not [f for f in findings if f["category"] == "shoe_unprofiled"]
    assert not [f for f in findings if f["category"] == "shoe_profile_orphan"]


# ── CHECK_MAP registration ──────────────────────────────────────────────────


def test_shoes_check_is_registered_under_new_name() -> None:
    """After the rename check_strava_shoes → check_shoes, the CHECK_MAP
    entry for SHOES must point at the new function name.
    """
    assert "SHOES" in audit_consistency.CHECK_MAP
    name, online = audit_consistency.CHECK_MAP["SHOES"]
    assert name == "check_shoes"
    assert online is True, "SHOES check consumes online gear data"
    # The symbol itself must resolve — a stale CHECK_MAP string would slip
    # through the mere-string check above.
    assert callable(getattr(audit_consistency, "check_shoes"))
