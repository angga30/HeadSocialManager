"""Content Agent — channel-native copy + creative briefs, delegating media to a sub-agent."""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from headofsocial.agents.media_generation_agent import create_media_generation_agent
from headofsocial.agents.prompts import content_instruction
from headofsocial.llm.models import get_model
from headofsocial.tools import (
    brand_tools,
    calendar_tools,
    channel_tools,
    media_tools,
    research_tools,
)


def create_content_agent() -> Agent:
    return Agent(
        name="content_agent",
        model=get_model("content"),
        instruction=content_instruction(),
        description=(
            "Digunakan untuk membuat konten (copy native per channel), memilih kedalaman "
            "konten (text/visual/carousel/motion/series/rich), lalu mendelegasikan generate "
            "media ke media_generation_agent."
        ),
        tools=[
            brand_tools.get_brand,
            channel_tools.get_channel_style,
            calendar_tools.list_scheduled_posts,
            calendar_tools.get_post,
            media_tools.create_asset,
            media_tools.attach_asset,
            research_tools.search_web,
            AgentTool(agent=create_media_generation_agent()),
        ],
    )
