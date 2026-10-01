"""A1 — the pipeline end-to-end: plan → fan-out → attach asset → approve → publish."""

from datetime import datetime

from headofsocial.domain.enums import Platform, PostStatus
from headofsocial.domain.models import Asset, Post
from headofsocial.domain.schemas import ChannelInput, MonthlyPlan, WeeklyTheme
from headofsocial.services import brand_service, planning_service, publishing_service
from headofsocial.tools import calendar_tools, media_tools


async def test_fan_out_attach_and_publish(session, brand):
    await brand_service.create_channel(
        session, brand.id, ChannelInput(platform=Platform.THREADS, handle="kopi.th")
    )
    plan = await planning_service.create_plan(
        session,
        brand.id,
        MonthlyPlan(
            period="2026-12",
            theme="Year end",
            weekly_themes=[WeeklyTheme(week=1, focus="Recap")],
            cadence={"threads": 1},
        ),
    )
    posts = await planning_service.fan_out_plan(session, plan.id)
    assert posts, "fan-out produced no slots"
    post = posts[0]
    assert post.asset_id is None  # created without content

    # Content step: create an asset and attach it (the missing link before the fix).
    asset = await media_tools.create_asset(brand.id, "Caption tahunan", depth="text")
    attached = await media_tools.attach_asset(post.id, asset["id"])
    assert attached["ok"] is True

    # Slot now reports its asset via get_post.
    fetched = await calendar_tools.get_post(post.id)
    assert fetched["ok"] and fetched["post"]["asset_id"] == asset["id"]

    # Approve (needs schedule + asset) then publish.
    approved = await calendar_tools.approve_post(post.id)
    assert approved["ok"] is True, approved
    assert approved["status"] == PostStatus.SCHEDULED

    published = await calendar_tools.publish_now(post.id)
    assert published["status"] == PostStatus.PUBLISHED
    assert published["publish_result"]["ok"] is True


async def test_attach_asset_brand_mismatch_rejected(session, brand):
    other = await brand_service.create_brand(session, "Brand lain", "product", language="id")
    channel = await brand_service.create_channel(
        session, brand.id, ChannelInput(platform=Platform.LINKEDIN, handle="li")
    )
    asset = Asset(brand_id=other.id, type="text", body="x")
    post = Post(brand_id=brand.id, channel_id=channel.id, status=PostStatus.DRAFT)
    session.add_all([asset, post])
    await session.commit()

    result = await media_tools.attach_asset(post.id, asset.id)
    assert result["ok"] is False and "mismatch" in result["error"].lower()


async def test_service_level_flow_publishes_due(session, brand, channel):
    asset = Asset(brand_id=brand.id, type="text", body="hi")
    session.add(asset)
    await session.commit()
    post = Post(
        brand_id=brand.id,
        channel_id=channel.id,
        asset_id=asset.id,
        status=PostStatus.DRAFT,
        scheduled_at=datetime(2020, 1, 1, 9, 0),
    )
    session.add(post)
    await session.commit()

    await publishing_service.schedule_post(session, post)
    published = await publishing_service.publish_due(session)
    assert len(published) == 1
    assert published[0].status == PostStatus.PUBLISHED