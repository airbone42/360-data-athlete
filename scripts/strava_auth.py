"""One-time Strava OAuth2 authorization flow.

Two-step usage (kein lokaler Server nötig):

  Schritt 1 — Auth-URL ausgeben:
      python3 scripts/strava_auth.py

  Schritt 2 — Code eintauschen (nach Browser-Autorisierung):
      python3 scripts/strava_auth.py --code DEIN_CODE

Der Code steht in der Redirect-URL nach der Autorisierung:
    http://localhost/exchange_token?state=&code=HIER_DER_CODE&scope=...

Scopes: profile:read_all,activity:read_all,activity:write
(activity:* wird für den strava-publisher Agent / strava_apply.py
benötigt.)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from app.config import settings

_TOKEN_URL = "https://www.strava.com/oauth/token"
_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
_SCOPE = "profile:read_all,activity:read_all,activity:write"
_ENV_FILE = Path(__file__).parent.parent / ".env"
# Strava redirects to this URI — must match "Authorization Callback Domain" in app settings.
# localhost is always accepted by Strava regardless of port.
_REDIRECT_URI = "http://localhost/exchange_token"


async def _exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.post(
            _TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        r.raise_for_status()
        return r.json()


def _write_env_key(key: str, value: str) -> None:
    if _ENV_FILE.exists():
        lines = _ENV_FILE.read_text().splitlines()
    else:
        lines = []
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}")
    _ENV_FILE.write_text("\n".join(lines) + "\n")
    print(f"✓  {key} gespeichert in {_ENV_FILE}")


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", help="Authorization code from Strava redirect URL")
    args = parser.parse_args()

    client_id = settings.strava_client_id
    client_secret = settings.strava_client_secret

    if not client_id or not client_secret:
        print("FEHLER: STRAVA_CLIENT_ID und STRAVA_CLIENT_SECRET fehlen in .env")
        sys.exit(1)

    if not args.code:
        # Step 1: print auth URL
        auth_url = (
            f"{_AUTHORIZE_URL}?"
            + urllib.parse.urlencode({
                "client_id": client_id,
                "redirect_uri": _REDIRECT_URI,
                "response_type": "code",
                "approval_prompt": "auto",
                "scope": _SCOPE,
            })
        )
        print("\nSchritt 1 — Diese URL im Browser öffnen:")
        print(f"\n  {auth_url}\n")
        print("Nach der Autorisierung leitet Strava auf eine localhost-URL um.")
        print("Den Wert des 'code'-Parameters aus der URL kopieren, dann:")
        print("\n  python3 scripts/strava_auth.py --code DEIN_CODE\n")
        return

    # Step 2: exchange code for tokens
    print(f"Tausche Code gegen Token ...")
    tokens = asyncio.run(_exchange_code(client_id, client_secret, args.code))

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print(f"FEHLER: Kein refresh_token in Antwort: {tokens}")
        sys.exit(1)

    athlete = tokens.get("athlete", {})
    name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()

    _write_env_key("STRAVA_REFRESH_TOKEN", refresh_token)
    print(f"Athlete: {name} (id={athlete.get('id')})")
    print("\nFertig. Jetzt testen mit:\n  python3 scripts/fetch_shoes.py\n")


if __name__ == "__main__":
    main()
