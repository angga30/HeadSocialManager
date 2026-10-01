"""Media Generation Agent — single media item, vision-based fidelity.

Spawned by the Content Agent (via AgentTool) once per image/video item, run in parallel.
Each instance analyzes the relevant reference photo (face/logo/product) with a vision model,
then generates exactly one media item into the shared asset.
"""

from google.adk.agents import Agent

from headofsocial.agents.prompts import MEDIA_GENERATION_INSTRUCTION
from headofsocial.llm.models import get_model
from headofsocial.tools import brand_tools, media_tools


def create_media_generation_agent() -> Agent:
    return Agent(
        name="media_generation_agent",
        model=get_model("media"),
        instruction=MEDIA_GENERATION_INSTRUCTION,
        description=(
            "Generate SATU item media (image/video) dari caption + creative brief + foto "
            "referensi brand, dengan fidelity analisis (wajah/logo/produk)."
        ),
        tools=[
            brand_tools.get_brand,
            brand_tools.list_brand_assets,
            media_tools.analyze_reference_asset,
            media_tools.generate_media_item,
        ],
    )
