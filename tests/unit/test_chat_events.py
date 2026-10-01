"""Agent event stream: ADK events -> UI events (agent/tool/token) with partial dedupe."""

from google.adk.events import Event
from google.genai import types

from headofsocial.services.chat_service import ChatService, _error_message


class _FakeRunner:
    """Yields a canned list of ADK events from run_async."""

    def __init__(self, events):
        self._events = events

    async def run_async(self, **_kwargs):
        for event in self._events:
            yield event


def _text(author: str, text: str, partial: bool) -> Event:
    return Event(
        author=author,
        partial=partial,
        content=types.Content(role="model", parts=[types.Part.from_text(text=text)]),
    )


def _call(author: str, name: str, args: dict) -> Event:
    part = types.Part(function_call=types.FunctionCall(name=name, args=args))
    return Event(author=author, content=types.Content(role="model", parts=[part]))


def _response(author: str, name: str, response: dict) -> Event:
    part = types.Part(function_response=types.FunctionResponse(name=name, response=response))
    return Event(author=author, content=types.Content(role="user", parts=[part]))


def _service(events) -> ChatService:
    service = object.__new__(ChatService)
    service._user_id = "test"
    service._runner = _FakeRunner(events)
    return service


async def _collect(events) -> list[dict]:
    return [event async for event in _service(events)._agent_events("sess", "hi")]


async def test_author_change_emits_agent_event():
    events = [_text("root_agent", "Halo", True), _text("planning_agent", "Rencana", True)]
    out = await _collect(events)
    agents = [e["name"] for e in out if e["type"] == "agent"]
    assert agents == ["root_agent", "planning_agent"]


async def test_partial_then_final_does_not_duplicate_text():
    events = [
        _text("root_agent", "Halo", True),
        _text("root_agent", " dunia", True),
        _text("root_agent", "Halo dunia!", False),
    ]
    out = await _collect(events)
    tokens = [e["text"] for e in out if e["type"] == "token"]
    assert "".join(tokens) == "Halo dunia!"


async def test_final_only_yields_full_text_once():
    out = await _collect([_text("root_agent", "Sekali saja", False)])
    assert "".join(e["text"] for e in out if e["type"] == "token") == "Sekali saja"


async def test_function_call_and_response_become_tool_events():
    events = [
        _call("root_agent", "get_brand", {"brand_id": 1}),
        _response("root_agent", "get_brand", {"ok": True, "id": 1}),
    ]
    out = await _collect(events)
    tools = [(e["name"], e["status"]) for e in out if e["type"] == "tool"]
    assert tools == [("get_brand", "start"), ("get_brand", "done")]


async def test_transfer_call_emits_agent_not_tool():
    events = [_call("root_agent", "transfer_to_agent", {"agent_name": "content_agent"})]
    out = await _collect(events)
    assert [e["name"] for e in out if e["type"] == "agent"] == ["root_agent", "content_agent"]
    assert not [e for e in out if e["type"] == "tool"]


def test_error_message_classifies_db_and_auth():
    assert "Database" in _error_message(RuntimeError("attempt to write a readonly database"))
    assert "autentikasi" in _error_message(RuntimeError("invalid api key"))
    assert _error_message(RuntimeError("boom")).startswith("⚠️ Error: boom")
