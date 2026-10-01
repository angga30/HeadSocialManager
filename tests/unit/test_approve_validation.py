"""A2 — approve (schedule) requires both a schedule time and an attached asset."""

from datetime import datetime

import pytest

from headofsocial.domain.enums import ContentDepth, PostStatus
from headofsocial.domain.models import Asset, Post
from headofsocial.services import publishing_service


async def _make_post(session, brand, channel, *, scheduled: bool, with_asset: bool) -> Post:
    asset = None
    if with_asset:
        asset = Asset(brand_id=brand.id, type="text", depth=ContentDepth.TEXT, body="x")
        session.add(asset)
        await session.commit()
    post = Post(
        brand_id=brand.id,
        channel_id=channel.id,
        asset_id=asset.id if asset else None,
        status=PostStatus.DRAFT,
        scheduled_at=datetime(2026, 11, 1, 9, 0) if scheduled else None,
    )
    session.add(post)
    await session.commit()
    return post


async def test_approve_without_schedule_rejected(session, brand, channel):
    post = await _make_post(session, brand, channel, scheduled=False, with_asset=True)
    with pytest.raises(ValueError, match="scheduled_at"):
        await publishing_service.schedule_post(session, post)


async def test_approve_without_asset_rejected(session, brand, channel):
    post = await _make_post(session, brand, channel, scheduled=True, with_asset=False)
    with pytest.raises(ValueError, match="asset"):
        await publishing_service.schedule_post(session, post)


async def test_approve_valid(session, brand, channel):
    post = await _make_post(session, brand, channel, scheduled=True, with_asset=True)
    scheduled = await publishing_service.schedule_post(session, post)
    assert scheduled.status == PostStatus.SCHEDULED


async def test_scheduler_skips_unscheduled(session, brand, channel):
    await _make_post(session, brand, channel, scheduled=False, with_asset=True)
    published = await publishing_service.publish_due(session)
    assert published == []