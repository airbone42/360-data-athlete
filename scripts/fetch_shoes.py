"""Fetch and display all Strava shoes with mileage, retired status and profile matching.

Usage:
    python3 scripts/fetch_shoes.py              # tabular output
    python3 scripts/fetch_shoes.py --json        # raw JSON
    python3 scripts/fetch_shoes.py --bust-cache  # re-fetch from Strava API

The script also shows which shoes are NOT yet profiled in config/equipment.md
so you can add them before the advisor goes live.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.strava_client import StravaClient, bust_shoes_cache
from app.graphs.shoe_advisor import load_shoe_profiles


async def _run(bust: bool, as_json: bool) -> None:
    if bust:
        bust_shoes_cache()
        print("Cache geleert.")

    client = StravaClient()
    shoes = await client.list_shoes()
    profiles = load_shoe_profiles()
    profiled_ids = {p["strava_id"] for p in profiles}

    if as_json:
        print(json.dumps(shoes, ensure_ascii=False, indent=2))
        return

    active = [s for s in shoes if not s["retired"]]
    retired = [s for s in shoes if s["retired"]]

    print(f"\n{'─' * 72}")
    print(f"  {'ID':<16}  {'Name':<30}  {'km':>6}  {'Prim':>4}  Profil")
    print(f"{'─' * 72}")

    for s in active:
        profiled = "✓" if s["strava_id"] in profiled_ids else "– fehlt"
        brand_model = f"{s['brand_name']} {s['model_name']}".strip()
        display = brand_model or s["name"]
        prim = "✓" if s["primary"] else ""
        print(f"  {s['strava_id']:<16}  {display:<30}  {s['distance_km']:>6.0f}  {prim:>4}  {profiled}")

    if retired:
        print(f"\n  Retired ({len(retired)}): " + ", ".join(s["name"] for s in retired))

    print(f"{'─' * 72}")
    missing = [s for s in active if s["strava_id"] not in profiled_ids]
    if missing:
        print(f"\n⚠  {len(missing)} Schuh/Schuhe ohne Profil in config/equipment.md:")
        for s in missing:
            print(f"   strava_id: {s['strava_id']}  →  {s['name']}")
        print("\n  Vorlage für equipment.md:")
        for s in missing:
            brand = s["brand_name"] or "?"
            model = s["model_name"] or s["name"]
            print(f"""
  - strava_id: {s['strava_id']}
    name: "{brand} {model}"
    type: easy          # tempo | easy | long | trail | recovery
    role: daily         # daily | race
    terrain: asphalt    # asphalt | trail | track | mixed
    pace_range_min_km: [4.5, 7.0]
    recommended_tags: [easy, long]
    threshold_km: 800
    cushion: medium     # low | medium | max
    race_prep_days: 7   # nur bei role: race""")
    else:
        print("\n✓  Alle aktiven Schuhe sind in config/equipment.md profiliert.")

    print()


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Strava shoes")
    parser.add_argument("--bust-cache", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    asyncio.run(_run(args.bust_cache, args.json))


if __name__ == "__main__":
    main()
