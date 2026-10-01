"""Planning Agent — evidence-driven monthly editorial planning."""

from google.adk.agents import Agent

from headofsocial.agents.prompts import planning_instruction
from headofsocial.llm.models import get_model
from headofsocial.tools import (
    brand_tools,
    calendar_tools,
    channel_tools,
    history_tools,
    insights_tools,
)


def create_planning_agent(history_note: str = "") -> Agent:
    return Agent(
        name="planning_agent",
        model=get_model("planning"),
        instruction=planning_instruction(history_note or "Tidak ada catatan khusus."),
        description=(
            "Digunakan untuk rencana editorial bulanan, kalender konten, cadence per channel, "
            "content mix, dan fan-out jadwal posting."
        ),
        tools=[
            brand_tools.get_brand,
            channel_tools.list_channels,
            channel_tools.get_channel_style,
            insights_tools.get_engagement_insights,
            history_tools.get_content_history,
            calendar_tools.get_existing_plan,
            calendar_tools.create_monthly_plan,
            calendar_tools.fan_out_plan,
            calendar_tools.list_scheduled_posts,
        ],
    )