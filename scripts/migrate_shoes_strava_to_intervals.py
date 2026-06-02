"""One-time migration: mirror the Strava shoe fleet into intervals.icu gear.

The Strava API is moving behind a paid tier, so the coach is switching its
shoe-mileage tracking to intervals.icu's native gear (see
SHOE_TRACKING_BACKEND in app/config.py). This script copies every Strava
shoe — active and retired, with its current mileage — into intervals.icu
once, so the new backend starts with the real fleet and km counts.

After running it, intervals.icu accumulates each shoe's mileage itself from
every activity that carries the shoe's gear_id; no further Strava sync is
needed.

Idempotent: a shoe whose name already exists as an intervals.icu Shoes-gear
is skipped (or, with --update, has its mileage/retired status refreshed).

Usage:
    python3 scripts/migrate_shoes_strava_to_intervals.py            # dry-run (default)
    python3 scripts/migrate_shoes_strava_to_intervals.py --apply    # actually create gear
    python3 scripts/migrate_shoes_strava_to_intervals.py --apply --update   # also refresh existing

Requires the STRAVA_* credentials (read side) and the intervals.icu API key
(write side). On success it writes a strava_id → icu_gear_id mapping to
data/shoe_gear_map.json as a template for adding `icu_gear_id:` to your
config/equipment.md shoe profiles.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.intervals_client import IntervalsClient
from app.api.strava_client import StravaClient
from app.config import settings
from app.utils.paths import DATA_DIR

_MAP_PATH = DATA_DIR / "shoe_gear_map.json"


def shoe_to_gear_payload(shoe: dict) -> dict:
    """Map a Strava shoe dict to an intervals.icu gear-create payload.

    Strava `distance_km` → intervals.icu `distance` in metres (intervals.icu
    gear distance is metric metres, same unit as the Strava gear API).
    """
    return {
        "name": shoe.get("name") or "",
        "type": "Shoes",
        "retired": bool(shoe.get("retired", False)),
        "distance": int(round((shoe.get("distance_km") or 0) * 1000)),
    }


def _norm_name(name: str) -> str:
    return (name or "").strip().casefold()


def plan_migration(strava_shoes: list[dict], existing_gear: list[dict]) -> list[dict]:
    """Decide, per Strava shoe, what to do against the existing intervals.icu gear.

    Pure (no I/O) so it can be unit-tested. Matching is by case-insensitive
    name among existing `type == "Shoes"` gear.

    Returns a list of action dicts:
        {action: "create"|"update"|"skip", shoe, payload, existing_id}
    """
    by_name: dict[str, dict] = {}
    for g in existing_gear:
        if (g.get("type") or "") == "Shoes":
            by_name[_norm_name(g.get("name", ""))] = g

    actions: list[dict] = []
    for shoe in strava_shoes:
        payload = shoe_to_gear_payload(shoe)
        match = by_name.get(_norm_name(shoe.get("name", "")))
        if match is None:
            actions.append({"action": "create", "shoe": shoe, "payload": payload, "existing_id": None})
        else:
            actions.append({
                "action": "update",
                "shoe": shoe,
                "payload": payload,
                "existing_id": str(match.get("id") or ""),
            })
    return actions


def _print_plan(actions: list[dict]) -> None:
    print(f"\n{'─' * 78}")
    print(f"  {'Action':<8}  {'Name':<34}  {'km':>6}  {'Status':<8}  intervals.icu id")
    print(f"{'─' * 78}")
    for a in actions:
        shoe = a["shoe"]
        status = "retired" if shoe.get("retired") else "active"
        km = (shoe.get("distance_km") or 0)
        eid = a["existing_id"] or "—"
        print(f"  {a['action']:<8}  {(shoe.get('name') or '?'):<34}  {km:>6.0f}  {status:<8}  {eid}")
    print(f"{'─' * 78}")
    creates = sum(1 for a in actions if a["action"] == "create")
    updates = sum(1 for a in actions if a["action"] == "update")
    print(f"  {creates} to create · {updates} already present (matched by name)\n")


def _write_mapping(mapping: dict[str, dict]) -> None:
    try:
        _MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        _MAP_PATH.write_text(json.dumps(mapping, ensure_ascii=False, indent=2))
        print(f"Mapping geschrieben: {_MAP_PATH}")
    except Exception as e:  # noqa: BLE001
        print(f"⚠ Mapping konnte nicht geschrieben werden: {e}", file=sys.stderr)


async def _run(apply: bool, update: bool) -> None:
    if not settings.strava_client_id or not settings.strava_refresh_token:
        print("⚠ Strava ist nicht konfiguriert — kann die Quell-Schuhe nicht lesen.", file=sys.stderr)
        sys.exit(1)

    strava_shoes = await StravaClient().list_shoes()
    icu = IntervalsClient()
    existing_gear = await icu.list_gear()

    actions = plan_migration(strava_shoes, existing_gear)
    _print_plan(actions)

    if not apply:
        print("Dry-run (Default). Mit --apply ausführen.\n")
        return

    mapping: dict[str, dict] = {}
    for a in actions:
        shoe = a["shoe"]
        sid = str(shoe.get("strava_id") or "")
        try:
            if a["action"] == "create":
                created = await icu.create_gear(a["payload"])
                gid = str(created.get("id") or "")
                print(f"✓ angelegt: {shoe.get('name')} → {gid}")
            elif a["action"] == "update" and update:
                gid = a["existing_id"]
                await icu.update_gear(gid, a["payload"])
                print(f"↻ aktualisiert: {shoe.get('name')} → {gid}")
            else:  # update without --update flag → skip
                gid = a["existing_id"]
                print(f"– übersprungen (existiert): {shoe.get('name')} → {gid}")
            if sid and gid:
                mapping[sid] = {"icu_gear_id": gid, "name": shoe.get("name") or ""}
        except Exception as e:  # noqa: BLE001
            print(f"✗ Fehler bei {shoe.get('name')}: {e}", file=sys.stderr)

    if mapping:
        _write_mapping(mapping)
        print("\nNächster Schritt: `icu_gear_id:` aus dem Mapping in die")
        print("config/equipment.md-Schuhprofile übernehmen, dann")
        print("SHOE_TRACKING_BACKEND=intervals aktivieren.\n")


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Strava shoes to intervals.icu gear")
    parser.add_argument("--apply", action="store_true", help="Execute (default is dry-run)")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Also refresh mileage/retired on shoes that already exist (matched by name)",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.apply, args.update))


if __name__ == "__main__":
    main()
