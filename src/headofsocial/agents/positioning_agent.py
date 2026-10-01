"""Positioning Agent — interview/document-driven brand positioning recommendation."""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from headofsocial.agents.prompts import POSITIONING_INSTRUCTION
from headofsocial.domain.schemas import PositioningRecommendation
from headofsocial.llm.models import get_model
from headofsocial.tools import brand_tools, document_tools, research_tools


def create_positioning_agent() -> Agent:
    return Agent(
        name="positioning_agent",
        model=get_model("positioning"),
        instruction=POSITIONING_INSTRUCTION,
        description=(
            "Digunakan untuk rekomendasi positioning, strategi brand, target audience, "
            "differentiators, voice/tone, dan content pillars."
        ),
        tools=[
            brand_tools.create_brand,
            brand_tools.get_brand,
            brand_tools.list_brands,
            brand_tools.apply_positioning,
            brand_tools.upload_brand_asset,
            brand_tools.list_brand_assets,
            brand_tools.set_visual_style,
            document_tools.list_documents,
            document_tools.read_document,
            research_tools.research_competitors,
            # S1: validate the recommendation against the Pydantic schema before saving.
            AgentTool(agent=create_positioning_formatter()),
        ],
    )


# Structured-output formatter: separate agent, no tools, so output is schema-guaranteed.
def create_positioning_formatter() -> Agent:
    return Agent(
        name="positioning_formatter",
        model=get_model("positioning"),
        instruction=(
            "Susun hasil wawancara/penggalian brand menjadi rekomendasi positioning yang "
            "terstruktur. Isi semua field termasuk visual_style."
        ),
        description="Format hasil penggalian menjadi rekomendasi positioning terstruktur.",
        output_schema=PositioningRecommendation,
        output_key="positioning_recommendation",
    )