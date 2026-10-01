"""Publishing Agent — post lifecycle: schedule, approve, publish."""

from google.adk.agents import Agent

from headofsocial.agents.prompts import PUBLISHING_INSTRUCTION
from headofsocial.llm.models import get_model
from headofsocial.tools import calendar_tools


def create_publishing_agent() -> Agent:
    return Agent(
        name="publishing_agent",
        model=get_model("publishing"),
        instruction=PUBLISHING_INSTRUCTION,
        description=(
            "Digunakan untuk menjadwalkan, meng-approve, dan mempublish posting ke "
            "social media (IG, Threads, LinkedIn)."
        ),
        tools=[
            calendar_tools.list_scheduled_posts,
            calendar_tools.approve_post,
            calendar_tools.publish_now,
        ],
    )