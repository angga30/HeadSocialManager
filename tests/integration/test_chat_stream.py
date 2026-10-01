"""Chat stream lifecycle: events, persistence, and server-side stop (fake runner, real DB)."""

import asyncio

from google.adk.events import Event
from google.genai import types

from headofsocial.services import conversation_service
from headofsocial.services.chat_service import ChatService


class _Runner:
    def __init__(self, events, delay: float = 0.0) -> None:
        self._events = events
        self._delay = delay

    async def run_async(self, **_kwargs):
        for event in self._events:
            if self._delay:
                await asyncio.sleep(self._delay)
            yield event


def _text(author: str, text: str, partial: bool = False) -> Event:
    return Event(
        author=author,
        partial=partial,
        content=types.Content(role="model", parts=[types.Part.from_text(text=text)]),
    )


def _service(events, delay: float = 0.0) -> ChatService:
    service = object.__new__(ChatService)
    service._user_id = "test"
    service._runner = _Runner(events, delay)
    service._tasks = {}

    async def _noop(_session_id: str) -> None:
        return None

    service._ensure_adk_session = _noop
    return service


async def test_stream_emits_events_and_persists(session):
    conv = await conversation_service.create(session)
    events = [_text("root_agent", "Hi", True), _text("root_agent", "Hi there", False)]
    service = _service(events)

    out = [event async for event in service.stream(conv.id, "halo")]

    kinds = [event["type"] for event in out]
    assert kinds[0] == "status"
    assert "agent" in kinds and "token" in kinds
    assert kinds[-1] == "done" and out[-1]["stopped"] is False

    msgs = await conversation_service.list_messages(session, conv.id)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["text"] == "halo"
    assert msgs[1]["text"] == "Hi there"
    assert (await conversation_service.list_conversations(session))[0]["status"] == "idle"


async def test_stop_cancels_run_and_marks_partial(session):
    conv = await conversation_service.create(session)
    service = _service([_text("root_agent", "sebagian", True)], delay=2.0)

    out = []
    async for event in service.stream(conv.id, "halo"):
        out.append(event)
        if event["type"] == "status":
            assert service.stop(conv.id) is True

    assert out[-1]["type"] == "done"
    assert out[-1]["stopped"] is True
    msgs = await conversation_service.list_messages(session, conv.id)
    assert msgs[-1]["role"] == "assistant"
    assert "(dihentikan)" in msgs[-1]["text"]
    assert (await conversation_service.list_conversations(session))[0]["status"] == "idle"


async def test_stop_with_no_running_task_is_noop(session):
    conv = await conversation_service.create(session)
    service = _service([])
    assert service.stop(conv.id) is False
