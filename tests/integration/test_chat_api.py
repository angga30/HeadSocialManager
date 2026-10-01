"""Chat SSE route: HTTP framing of service events (fake service, real DB/route)."""

import httpx

from headofsocial.api import routes
from headofsocial.api.app import create_app
from headofsocial.services import conversation_service


class _FakeChat:
    async def stream(self, conversation_id, text, mentions=None, *, retry=False):
        yield {"type": "status", "state": "thinking"}
        yield {"type": "agent", "name": "root_agent"}
        yield {"type": "tool", "status": "start", "name": "get_brand", "summary": "id=1"}
        yield {"type": "token", "text": "Halo"}
        yield {"type": "tool", "status": "done", "name": "get_brand", "summary": "id=1"}
        yield {"type": "token", "text": " dunia"}
        yield {"type": "done", "message_id": 1, "stopped": False, "has_error": False}

    def stop(self, conversation_id):
        return False


async def test_stream_route_serializes_events(monkeypatch, session):
    conv = await conversation_service.create(session)
    monkeypatch.setattr(routes.chat, "get_chat_service", lambda: _FakeChat())

    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST",
            f"/api/chat/conversations/{conv.id}/stream",
            json={"message": "hi", "mentions": []},
        ) as res:
            assert res.status_code == 200
            assert res.headers["content-type"].startswith("text/event-stream")
            body = "".join([chunk async for chunk in res.aiter_text()])

    for frame in ("event: status", "event: agent", "event: tool", "event: token", "event: done"):
        assert frame in body
    assert '"text": "Halo"' in body
    assert body.count("event: token") == 2


async def test_retry_route_requires_a_user_message(monkeypatch, session):
    conv = await conversation_service.create(session)
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(f"/api/chat/conversations/{conv.id}/retry")
    assert res.status_code == 400
