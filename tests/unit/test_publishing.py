"""Publishing flow — publish a post, record metrics, flip status."""

from datetime import UTC, datetime, timedelta

from headofsocial.domain.enums import ContentDepth, PostStatus
from headofsocial.domain.models import Asset
from headofsocial.services import publishing_service
from headofsocial.services.publishing_service import simulate_metrics


async def test_simulate_metrics_shape():
    data = {"post_id": 1, "platform": "instagram"}
    m = simulate_metrics(**data)
    assert m["post_id"] == 1
    assert m["platform"] == "instagram"
    for key in ("impressions", "reach", "likes", "comments", "shares", "saves"):
        assert key in m


async def test_publish_post_flips_status_and_metrics(session, brand, channel):
    asset = Asset(brand_id=brand.id, type="text", depth=ContentDepth.TEXT, body="hello")
    session.add(asset)
    await session.commit()

    async def _mk_post():
        from headofsocial.domain.models import Post

        post = Post(
            brand_id=brand.id,
            channel_id=channel.id,
            asset_id=asset.id,
            status=PostStatus.SCHEDULED,
            scheduled_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),
        )
        session.add(post)
        await session.commit()
        return post

    post = await _mk_post()
    result = await publishing_service.publish_post(session, post)

    assert result.status == PostStatus.PUBLISHED
    assert result.publish_result["ok"] is True
    assert result.publish_result["external_id"]
    assert result.published_at is not None
    # metrics were recorded and are visible on the returned object
    assert len(result.metrics) == 1
    assert result.metrics[0].likes > 0