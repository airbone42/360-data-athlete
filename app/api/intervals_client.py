import logging

import httpx

from app.config import settings
from app.utils.tracing import set_span_io, set_span_metadata, traced

logger = logging.getLogger(__name__)

BASE_URL = "https://intervals.icu/api/v1"


def _summarize_wellness(w: dict) -> str:
    if not w:
        return "(empty)"
    parts = []
    if (rhr := w.get("restingHR")) is not None:
        parts.append(f"RHR={rhr}")
    if (hrv := w.get("hrv")) is not None:
        parts.append(f"HRV={hrv}")
    if (sleep := w.get("sleepSecs")) is not None:
        parts.append(f"sleep={round(sleep / 3600, 1)}h")
    if (ctl := w.get("ctl")) is not None:
        parts.append(f"CTL={round(ctl, 1)}")
    if (atl := w.get("atl")) is not None:
        parts.append(f"ATL={round(atl, 1)}")
    return " ".join(parts) if parts else "(no metrics)"


def _summarize_activities(activities: list[dict]) -> str:
    if not activities:
        return "0 activities"
    types: dict[str, int] = {}
    for a in activities:
        t = a.get("type") or "Unknown"
        types[t] = types.get(t, 0) + 1
    breakdown = ", ".join(f"{n}× {t}" for t, n in sorted(types.items(), key=lambda x: -x[1]))
    return f"{len(activities)} activities ({breakdown})"


class IntervalsClient:
    def __init__(self, athlete_id: str | None = None) -> None:
        self.athlete_id = athlete_id or settings.intervals_icu_athlete_id
        self._auth = httpx.BasicAuth("API_KEY", settings.intervals_icu_api_key)

    def _url(self, path: str) -> str:
        return f"{BASE_URL}/athlete/{self.athlete_id}{path}"

    @traced("intervals.icu · fetch wellness", kind="tool")
    async def get_wellness(self, date: str) -> dict:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(self._url(f"/wellness/{date}"))
            r.raise_for_status()
            data = r.json()
        set_span_io(input={"date": date}, output=_summarize_wellness(data))
        return data

    @traced("intervals.icu · fetch activities", kind="tool")
    async def get_activities(self, oldest: str, newest: str) -> list[dict]:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(self._url("/activities"), params={"oldest": oldest, "newest": newest})
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"oldest": oldest, "newest": newest},
            output=_summarize_activities(data),
        )
        return data

    @traced("intervals.icu · fetch events (calendar)", kind="tool")
    async def get_events(self, oldest: str, newest: str) -> list[dict]:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(self._url("/events"), params={"oldest": oldest, "newest": newest})
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"oldest": oldest, "newest": newest},
            output=f"{len(data)} events",
        )
        return data

    @traced("intervals.icu · fetch wellness history", kind="tool")
    async def get_wellness_history(self, oldest: str, newest: str) -> list[dict]:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(self._url("/wellness"), params={"oldest": oldest, "newest": newest})
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"oldest": oldest, "newest": newest},
            output=f"{len(data)} daily entries",
        )
        return data

    @traced("intervals.icu · fetch weather forecast", kind="tool")
    async def get_weather_forecast(self) -> dict:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(self._url("/weather-forecast"))
            r.raise_for_status()
            data = r.json()
        days = data.get("daily", []) if isinstance(data, dict) else []
        set_span_io(input="(none)", output=f"{len(days)} forecast days")
        return data

    @traced("intervals.icu · fetch notes", kind="tool")
    async def get_notes(self, oldest: str, newest: str) -> list[dict]:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(
                self._url("/events"),
                params={"oldest": oldest, "newest": newest, "category": "NOTE"},
            )
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"oldest": oldest, "newest": newest},
            output=f"{len(data)} notes",
        )
        return data

    @traced("intervals.icu · create events (bulk)", kind="tool")
    async def post_events_bulk(self, events: list[dict]) -> list[dict]:
        names = [e.get("name", "?") for e in events]
        for e in events:
            logger.info(
                "intervals POST event: name=%r desc_len=%d moving_time=%s",
                e.get("name"),
                len(e.get("description") or ""),
                e.get("moving_time"),
            )
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.post(
                self._url("/events/bulk"),
                params={"upsert": "true"},
                json=events,
                headers={"Content-Type": "application/json"},
            )
            logger.info("intervals POST /events/bulk → status=%d", r.status_code)
            r.raise_for_status()
            data = r.json()
        ids = [e.get("id") for e in data]
        set_span_io(
            input={"count": len(events), "names": names},
            output={"created": len(data), "ids": ids},
        )
        set_span_metadata(event_count=len(events))
        return data

    @traced("intervals.icu · fetch today's workouts", kind="tool")
    async def get_today_workouts(self, date: str) -> list[dict]:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(
                self._url("/events"),
                params={"oldest": date, "newest": date, "category": "WORKOUT"},
            )
            r.raise_for_status()
            data = r.json()
        set_span_io(input={"date": date}, output=f"{len(data)} workouts")
        return data

    @traced("intervals.icu · delete event", kind="tool")
    async def delete_event(self, event_id: int) -> None:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.delete(self._url(f"/events/{event_id}"))
            r.raise_for_status()
        set_span_io(input={"event_id": event_id}, output="OK")

    @traced("intervals.icu · update event", kind="tool")
    async def update_event(self, event_id: int, payload: dict) -> dict:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.put(self._url(f"/events/{event_id}"), json=payload)
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"event_id": event_id, "fields": list(payload.keys())},
            output="OK",
        )
        return data

    @traced("intervals.icu · fetch activity detail", kind="tool")
    async def get_activity(self, activity_id: str) -> dict:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(f"{BASE_URL}/activity/{activity_id}")
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"activity_id": activity_id},
            output=f"{data.get('type', '?')} · {data.get('name', '?')}",
        )
        return data

    @traced("intervals.icu · update activity name", kind="tool")
    async def update_activity_name(self, activity_id: str, name: str) -> dict:
        """Rename an existing activity. Used e.g. by `strava_pending` when an
        Indoor-Activity carries an outdoor surface term in the title — keeps
        the source-of-truth name coherent with the actual setting
        (Forstweg ≠ Laufband)."""
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.put(f"{BASE_URL}/activity/{activity_id}", json={"name": name})
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"activity_id": activity_id, "name": name},
            output=f"renamed to '{data.get('name', '?')}'",
        )
        return data

    @traced("intervals.icu · fetch activity messages", kind="tool")
    async def get_activity_messages(self, activity_id: str) -> list[dict]:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(f"{BASE_URL}/activity/{activity_id}/messages")
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"activity_id": activity_id},
            output=f"{len(data)} messages",
        )
        return data

    @traced("intervals.icu · delete activity message", kind="tool")
    async def delete_activity_message(self, chat_id: int, message_id: int) -> None:
        """Delete an activity message via /chats/{chat_id}/messages/{message_id}.

        chat_id is returned by post_activity_message in response['new_chat']['id'].
        """
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.delete(f"{BASE_URL}/chats/{chat_id}/messages/{message_id}")
            r.raise_for_status()
        set_span_io(
            input={"chat_id": chat_id, "message_id": message_id},
            output="OK",
        )

    @traced("intervals.icu · post activity message", kind="tool")
    async def post_activity_message(self, activity_id: str, content: str) -> dict:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.post(
                f"{BASE_URL}/activity/{activity_id}/messages",
                json={"content": content},
                headers={"Content-Type": "application/json"},
                auth=self._auth,
            )
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"activity_id": activity_id, "content": content},
            output="OK",
        )
        return data

    @traced("intervals.icu · fetch event detail", kind="tool")
    async def get_event(self, event_id: str) -> dict:
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(self._url(f"/events/{event_id}"))
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"event_id": event_id},
            output=f"{data.get('type', '?')} · {data.get('name', '?')}",
        )
        return data

    @traced("intervals.icu · fetch athlete settings", kind="tool")
    async def get_athlete_settings(self) -> dict:
        """Fetch athlete profile including sport-specific HR zone boundaries."""
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(self._url(""))
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input="(none)",
            output=f"sportSettings={len(data.get('sportSettings', []))}",
        )
        return data

    # ── Gear (shoes) ──────────────────────────────────────────────────

    @traced("intervals.icu · list gear", kind="tool")
    async def list_gear(self) -> list[dict]:
        """GET /gear — athlete gear list (shoes + bikes + components).

        Each entry carries at least: id, name, type ("Shoes"/"Bike"/…),
        retired (bool), distance (metres), time (seconds). The shoe advisor
        filters on `type == "Shoes"`.
        """
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(self._url("/gear"))
            r.raise_for_status()
            data = r.json()
        shoes = sum(1 for g in data if (g.get("type") or "") == "Shoes")
        set_span_io(input="(none)", output=f"{len(data)} gear ({shoes} shoes)")
        return data

    @traced("intervals.icu · create gear", kind="tool")
    async def create_gear(self, payload: dict) -> dict:
        """POST /gear — create a new gear item (e.g. a shoe).

        payload keys: name, type ("Shoes"), retired (bool), distance (metres),
        time (seconds). Returns the created Gear object incl. its `id`.
        """
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.post(self._url("/gear"), json=payload)
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"name": payload.get("name"), "type": payload.get("type")},
            output=f"id={data.get('id', '?')}",
        )
        return data

    @traced("intervals.icu · update gear", kind="tool")
    async def update_gear(self, gear_id: str, payload: dict) -> dict:
        """PUT /gear/{gearId} — update gear fields (name, retired, distance…)."""
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.put(self._url(f"/gear/{gear_id}"), json=payload)
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"gear_id": gear_id, "fields": list(payload.keys())},
            output="OK",
        )
        return data

    @traced("intervals.icu · set activity gear", kind="tool")
    async def set_activity_gear(self, activity_id: str, gear_id: str | None) -> dict:
        """Assign a gear (shoe) to a completed activity.

        intervals.icu accumulates a shoe's mileage from every activity that
        carries it, so setting the gear here is what drives the native km
        tracking. Pass `gear_id=None` to clear the assignment.
        Uses PUT /activity/{id} with the `gear` field — intervals.icu
        rejects `gear_id` as an unknown custom field (422), and reads the
        assignment back as a nested `gear` object, not a flat `gear_id`.
        """
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.put(
                f"{BASE_URL}/activity/{activity_id}", json={"gear": gear_id}
            )
            r.raise_for_status()
            data = r.json()
        set_span_io(
            input={"activity_id": activity_id, "gear_id": gear_id},
            output=f"gear={(data.get('gear') or {}).get('id', '?')}",
        )
        return data

    @traced("intervals.icu · fetch activity streams", kind="tool")
    async def get_streams(
        self,
        activity_id: str,
        types: str = "time,heartrate,latlng,velocity_smooth,cadence,altitude,distance",
    ) -> dict[str, list]:
        """Fetch activity streams from intervals.icu.

        API returns [{"type": "time", "data": [...]}, ...] – converted to {type: data}.
        """
        async with httpx.AsyncClient(auth=self._auth) as c:
            r = await c.get(
                f"{BASE_URL}/activity/{activity_id}/streams",
                params={"types": types},
            )
            r.raise_for_status()
            raw: list[dict] = r.json()
        result = {item["type"]: item["data"] for item in raw if "type" in item and "data" in item}
        set_span_io(
            input={"activity_id": activity_id, "types": types.split(",")},
            output=f"{len(result)} streams: {list(result.keys())}",
        )
        return result
