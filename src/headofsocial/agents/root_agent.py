"""Root orchestrator agent — routes user intent to specialist sub-agents."""

from google.adk.agents import Agent

from headofsocial.agents.content_agent import create_content_agent
from headofsocial.agents.planning_agent import create_planning_agent
from headofsocial.agents.positioning_agent import create_positioning_agent
from headofsocial.agents.prompts import ROOT_INSTRUCTION
from headofsocial.agents.publishing_agent import create_publishing_agent
from headofsocial.llm.models import get_model
from headofsocial.tools import brand_tools, channel_tools


def create_root_agent(history_note: str = "") -> Agent:
    """Build the root agent with its specialist sub-agents (factory pattern: always call)."""
    return Agent(
        name="root_agent",
        model=get_model("orchestrator"),
        instruction=ROOT_INSTRUCTION,
        description="Entry point untuk seluruh sistem Head of Social Media. Router intent.",
        tools=[
            brand_tools.list_brands,
            brand_tools.get_brand,
            channel_tools.list_channels,
        ],
        sub_agents=[
            create_positioning_agent(),
            create_planning_agent(history_note),
            create_content_agent(),
            create_publishing_agent(),
        ],
    )