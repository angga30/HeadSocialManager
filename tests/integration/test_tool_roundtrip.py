"""Integration: tools wired to services, publish_due scheduler path, media generation."""

from datetime import UTC, datetime, timedelta

from headofsocial.domain.enums import ContentDepth, PostStatus
from headofsocial.domain.models import Asset, Post
from headofsocial.services import publishing_service
from headofsocial.tools import brand_tools, media_tools


async def test_brand_tool_roundtrip():
    created = await brand_tools.create_brand("Tool Brand", "product", "widgets", language="id")
    assert created["name"] == "Tool Brand"
    fetched = await brand_tools.get_brand(created["id"])
    assert fetched["type"] == "product"


async def test_publish_due_publishes_scheduled(session, brand, channel):
    asset = Asset(brand_id=brand.id, type="text", depth=ContentDepth.TEXT, body="due")
    session.add(asset)
    await session.commit()
    post = Post(
        brand_id=brand.id, channel_id=channel.id, asset_id=asset.id,
        status=PostStatus.SCHEDULED,
        scheduled_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),
    )
    session.add(post)
    await session.commit()

    published = await publishing_service.publish_due(session)
    assert len(published) == 1
    assert published[0].status == PostStatus.PUBLISHED


async def test_media_spec_to_asset_and_generate(session, brand):
    asset = await media_tools.create_asset(
        brand.id, "caption body", depth="carousel",
        image_prompts=["coffee cup", "coffee bag"],
    )
    assert asset["depth"] == "carousel"
    generated = await media_tools.generate_media(asset["id"])
    assert generated["ok"] is True
    assert len(generated["media_files"]) == 2  # one per prompt
    assert len(asset["media_spec"]) == 2


async def test_agent_importability():
    from headofsocial.agents.root_agent import create_root_agent

    root = create_root_agent()
    assert root.name == "root_agent"
    names = {a.name for a in root.sub_agents}
    assert {"positioning_agent", "planning_agent", "content_agent", "publishing_agent"} <= names