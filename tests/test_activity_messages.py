"""delete_activity_message / get_activity_messages contract.

Message objects carry no chat id and post_activity_message returns
`new_chat` only on chat creation — delete therefore resolves the chat via
/athlete/{id}/chats (ACTIVITY entries carry `activity_id`). Deletes are
soft (a `deleted` timestamp); the list call hides those by default.
Verified live 2026-08-06.
"""
from __future__ import annotations

import asyncio

import pytest

from app.api.intervals_client import IntervalsClient


def _client() -> IntervalsClient:
    c = IntervalsClient.__new__(IntervalsClient)
    c.athlete_id = "i0"
    c._auth = None
    return c


def test_delete_raises_when_activity_has_no_chat(monkeypatch):
    c = _client()

    async def no_chat(activity_id):
        return None

    monkeypatch.setattr(c, "get_activity_chat_id", no_chat)
    with pytest.raises(ValueError, match="no activity chat"):
        asyncio.run(c.delete_activity_message("i123", 42))


def test_delete_uses_resolved_chat_id(monkeypatch):
    c = _client()
    seen: dict = {}

    async def chat(activity_id):
        seen["resolved_for"] = activity_id
        return 777

    class _Resp:
        def raise_for_status(self):
            pass

    class _Http:
        def __init__(self, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def delete(self, url):
            seen["url"] = url
            return _Resp()

    monkeypatch.setattr(c, "get_activity_chat_id", chat)
    monkeypatch.setattr("app.api.intervals_client.httpx.AsyncClient", _Http)
    asyncio.run(c.delete_activity_message("i123", 42))
    assert seen["resolved_for"] == "i123"
    assert seen["url"].endswith("/chats/777/messages/42")


def test_get_activity_messages_hides_soft_deleted(monkeypatch):
    c = _client()
    raw = [
        {"id": 1, "content": "keep", "deleted": None},
        {"id": 2, "content": "gone", "deleted": "2026-08-06T16:39:40+00:00"},
    ]

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return raw

    class _Http:
        def __init__(self, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            return _Resp()

    monkeypatch.setattr("app.api.intervals_client.httpx.AsyncClient", _Http)
    visible = asyncio.run(c.get_activity_messages("i123"))
    assert [m["id"] for m in visible] == [1]
    everything = asyncio.run(c.get_activity_messages("i123", include_deleted=True))
    assert [m["id"] for m in everything] == [1, 2]
