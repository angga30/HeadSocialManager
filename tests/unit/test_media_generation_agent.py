"""Media Generation Agent — factory wiring + fidelity protocols."""

from headofsocial.agents.content_agent import create_content_agent
from headofsocial.agents.media_generation_agent import create_media_generation_agent
from headofsocial.agents.prompts import MEDIA_GENERATION_INSTRUCTION


def _tool_names(agent) -> set[str]:
    names: set[str] = set()
    for tool in agent.tools:
        names.add(getattr(tool, "name", None) or getattr(tool, "__name__", None))
    return names


def test_media_agent_has_fidelity_tools():
    agent = create_media_generation_agent()
    names = _tool_names(agent)
    assert {"get_brand", "list_brand_assets", "analyze_reference_asset", "generate_media_item"} <= names


def test_instruction_enforces_fidelity_protocols():
    assert "FIDELITY KETAT" in MEDIA_GENERATION_INSTRUCTION
    assert "IMMUTABLE" in MEDIA_GENERATION_INSTRUCTION
    assert "fotorealistik" in MEDIA_GENERATION_INSTRUCTION
    assert "siluet" in MEDIA_GENERATION_INSTRUCTION


def test_content_agent_delegates_to_media_agent():
    agent = create_content_agent()
    assert "media_generation_agent" in _tool_names(agent)
    # The lead must NOT generate media directly anymore.
    assert "generate_media" not in _tool_names(agent)
    assert "generate_media_item" not in _tool_names(agent)
