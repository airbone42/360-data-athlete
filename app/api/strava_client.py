"""Strava API v3 client — shoes/gear (read) + activity title sync (write).

Required .env variables:
    STRAVA_CLIENT_ID
    STRAVA_CLIENT_SECRET
    STRAVA_REFRESH_TOKEN   ← written by scripts/strava_auth.py

Scopes needed: profile:read_all,activity:read_all,activity:write
(Re-Auth via scripts/strava_auth.py wenn der Scope erweitert wird.)
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import httpx

from app.config import settings
from app.utils.tracing import set_span_io, traced

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://www.strava.com/oauth/token"
_BASE = "https://www.strava.com/api/v3"
_CACHE_TTL_S = 23 * 3600  # 23 h — refreshed once per day at /training

from app.utils.paths import CACHE_DIR as _APP_CACHE_DIR
_CACHE_DIR = _APP_CACHE_DIR / "strava"


class StravaClient:
    """Minimal Strava client with in-memory token refresh and file cache for shoe data."""

    def __init__(self) -> None:
        self._access_token: str = ""
        self._expires_at: float = 0.0

    # ── Token management ──────────────────────────────────────────────

    @traced("Strava · refresh access token", kind="tool")
    async def _ensure_token(self) -> None:
        if self._access_token and time.time() < self._expires_at - 60:
            set_span_io(input="(cached token)", output="OK · still valid")
            return
        if not settings.strava_client_id or not settings.strava_refresh_token:
            raise RuntimeError(
                "Strava not configured. Please run 'python3 scripts/strava_auth.py'."
            )
        async with httpx.AsyncClient() as c:
            r = await c.post(
                _TOKEN_URL,
                data={
                    "client_id": settings.strava_client_id,
                    "client_secret": settings.strava_client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": settings.strava_refresh_token,
                },
            )
            r.raise_for_status()
            data = r.json()
        self._access_token = data["access_token"]
        self._expires_at = float(data["expires_at"])
        logger.debug("strava: token refreshed, expires_at=%s", self._expires_at)
        set_span_io(input="(refresh)", output=f"OK · expires_at={self._expires_at}")

    def _auth_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    # ── API calls ────────────────────────────────────────────────────

    @traced("Strava · fetch athlete", kind="tool")
    async def get_athlete(self) -> dict:
        """GET /athlete — returns shoes[] with id, name, primary, distance (m)."""
        await self._ensure_token()
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{_BASE}/athlete", headers=self._auth_header())
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input="(none)",
            output=f"shoes={len(data.get('shoes') or [])} · bikes={len(data.get('bikes') or [])}",
        )
        return data

    @traced("Strava · fetch gear detail", kind="tool")
    async def get_gear(self, gear_id: str) -> dict:
        """GET /gear/{id} — returns brand_name, model_name, distance, retired."""
        await self._ensure_token()
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{_BASE}/gear/{gear_id}", headers=self._auth_header())
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"gear_id": gear_id},
            output=f"{data.get('brand_name', '?')} {data.get('model_name', '?')} · {round((data.get('distance') or 0) / 1000, 1)}km",
        )
        return data

    @traced("Strava · list activities", kind="tool")
    async def list_activities(self, after_epoch: int, per_page: int = 30) -> list[dict]:
        """GET /athlete/activities?after=… — Activities since UTC epoch seconds."""
        await self._ensure_token()
        async with httpx.AsyncClient() as c:
            r = await c.get(
                f"{_BASE}/athlete/activities",
                headers=self._auth_header(),
                params={"after": after_epoch, "per_page": per_page},
            )
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"after_epoch": after_epoch, "per_page": per_page},
            output=f"{len(data)} activities",
        )
        return data

    @traced("Strava · activity detail", kind="tool")
    async def get_activity_detail(self, activity_id: int) -> dict:
        """GET /activities/{id} — detail representation incl. description."""
        await self._ensure_token()
        async with httpx.AsyncClient() as c:
            r = await c.get(
                f"{_BASE}/activities/{activity_id}",
                headers=self._auth_header(),
            )
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"activity_id": activity_id},
            output=f"{data.get('type', '?')} · {data.get('name', '?')}",
        )
        return data

    @traced("Strava · update activity title", kind="tool")
    async def update_activity(
        self,
        activity_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> dict:
        """PUT /activities/{id} — partial update of name/description."""
        await self._ensure_token()
        payload: dict[str, str] = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if not payload:
            raise ValueError("update_activity: kein Feld zu aktualisieren")
        async with httpx.AsyncClient() as c:
            r = await c.put(
                f"{_BASE}/activities/{activity_id}",
                headers=self._auth_header(),
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"activity_id": activity_id, "fields": list(payload.keys()), "new_name": name},
            output="OK",
        )
        return data

    @traced("Strava · list shoes (enriched)", kind="tool")
    async def list_shoes(self) -> list[dict]:
        """Return enriched shoe list from Strava.

        Each entry:
            strava_id, name, brand_name, model_name, distance_km, retired, primary
        """
        cached = _read_cache("shoes")
        if cached is not None:
            logger.debug("strava: shoes served from cache")
            set_span_io(input="(none)", output=f"{len(cached)} shoes (from cache)")
            return cached

        athlete = await self.get_athlete()
        raw_shoes = [s for s in (athlete.get("shoes") or []) if not s.get("retired")]
        # Also include retired ones — caller filters; we cache all
        all_shoes_raw = athlete.get("shoes") or []

        enriched: list[dict] = []
        for shoe in all_shoes_raw:
            sid = shoe.get("id", "")
            if not sid:
                continue
            try:
                detail = await self.get_gear(sid)
            except Exception as e:
                logger.warning("strava: could not fetch gear %s: %s", sid, e)
                detail = {}
            enriched.append({
                "strava_id": sid,
                "name": detail.get("name") or shoe.get("name", ""),
                "brand_name": detail.get("brand_name", ""),
                "model_name": detail.get("model_name", ""),
                "distance_km": round((detail.get("distance") or shoe.get("distance") or 0) / 1000, 1),
                "retired": bool(detail.get("retired", shoe.get("retired", False))),
                "primary": bool(shoe.get("primary", False)),
            })

        _write_cache("shoes", enriched)
        active = sum(1 for s in enriched if not s.get("retired"))
        set_span_io(
            input="(none)",
            output=f"{len(enriched)} shoes ({active} active) · refreshed",
        )
        return enriched


# ── File-cache helpers ────────────────────────────────────────────────────────

def _cache_path(key: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{key}.json"


def _read_cache(key: str) -> list | None:
    p = _cache_path(key)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        if time.time() - data.get("_ts", 0) < _CACHE_TTL_S:
            return data["payload"]
    except Exception:
        p.unlink(missing_ok=True)
    return None


def _write_cache(key: str, payload: list) -> None:
    try:
        _cache_path(key).write_text(
            json.dumps({"_ts": time.time(), "payload": payload}, ensure_ascii=False)
        )
    except Exception as e:
        logger.warning("strava cache write failed: %s", e)


def bust_shoes_cache() -> None:
    """Call after manually editing equipment.md shoe profiles."""
    _cache_path("shoes").unlink(missing_ok=True)
