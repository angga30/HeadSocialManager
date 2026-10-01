"""Insights + content history aggregation."""

from datetime import UTC, datetime

from headofsocial.domain.enums import ContentDepth, PostStatus
from headofsocial.domain.models import Asset, Post, PostMetrics
from headofsocial.services import analytics_service


async def _publish_ok(session, brand, channel, body):
    asset = Asset(brand_id=brand.id, type="text", depth=ContentDepth.TEXT, body=body)
    session.add(asset)
    await session.commit()
    post = Post(
        brand_id=brand.id,
        channel_id=channel.id,
        asset_id=asset.id,
        status=PostStatus.PUBLISHED,
        pillar="education",
        depth_hint="text",
        published_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(post)
    await session.commit()
    session.add(
        PostMetrics(
            post_id=post.id, platform=str(channel.platform),
            impressions=10000, reach=2000, likes=300, comments=20, shares=10, saves=5,
        )
    )
    await session.commit()
    return post


async def test_insights_ranks_posts(session, brand, channel):
    await _publish_ok(session, brand, channel, "low performer")
    await _publish_ok(session, brand, channel, "low")
    # second, higher engagement
    high_asset = Asset(brand_id=brand.id, type="image", depth=ContentDepth.VISUAL, body="high performer")
    session.add(high_asset)
    await session.commit()
    high_post = Post(
        brand_id=brand.id, channel_id=channel.id, asset_id=high_asset.id,
        status=PostStatus.PUBLISHED, pillar="education", depth_hint="visual",
        published_at=datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(high_post)
    await session.commit()
    session.add(PostMetrics(post_id=high_post.id, platform="instagram",
                            impressions=10000, reach=1000, likes=900, comments=10, shares=0, saves=0))
    await session.commit()

    insights = await analytics_service.get_engagement_insights(session, brand.id)
    assert len(insights.top_posts) >= 1
    assert insights.top_posts[0].post_id == high_post.id  # higher engagement rate first
    # format performance includes both depth values
    depths = {f["depth"] for f in insights.format_performance}
    assert "text" in depths and "visual" in depths


async def test_content_history_returns_entries(session, brand, channel):
    await _publish_ok(session, brand, channel, "a post about beans")
    history = await analytics_service.get_content_history(session, brand.id)
    assert len(history) == 1
    assert history[0]["pillar"] == "education"
    assert history[0]["engagement_rate"] > 0
    assert "beans" in history[0]["headline"] or "beans" in history[0]["headline"]