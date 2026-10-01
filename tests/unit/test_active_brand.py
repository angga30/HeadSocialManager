"""S3 — the active brand is stored in ADK session state so sub-agents can read it."""

from types import SimpleNamespace

import pytest
from google.adk.utils import instructions_utils

from headofsocial.agents.prompts import _ACTIVE_BRAND_LINE
from headofsocial.tools import brand_tools


class _Ctx:
    """Minimal stand-in for ADK's ReadonlyContext (only the bits templating reads)."""

    def __init__(self, state: dict) -> None:
        self.agent_name = "test_agent"
        self._invocation_context = SimpleNamespace(
            session=SimpleNamespace(state=state, app_name="a", user_id="u", id="s")
        )


def test_set_active_brand_writes_state():
    ctx = SimpleNamespace(state={})
    result = brand_tools.set_active_brand(7, ctx)
    assert ctx.state["active_brand_id"] == 7
    assert result["ok"] is True and result["active_brand_id"] == 7


async def test_active_brand_placeholder_is_optional():
    # Rendering must not raise when the state key is absent (e.g. pre-existing sessions).
    assert "(" in await instructions_utils.inject_session_state(_ACTIVE_BRAND_LINE, _Ctx({}))
    rendered = await instructions_utils.inject_session_state(
        _ACTIVE_BRAND_LINE, _Ctx({"active_brand_id": 5})
    )
    assert "5" in rendered


async def test_required_placeholder_would_raise():
    with pytest.raises(KeyError):
        await instructions_utils.inject_session_state("brand: {active_brand_id}", _Ctx({}))
