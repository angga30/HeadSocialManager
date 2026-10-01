"""Publishing: resolve a publisher adapter, publish a post, record result + simulate metrics."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from headofsocial.domain.enums import PostStatus
from headofsocial.domain.models import Post, PostMetrics
from headofsocial.publishing.base import get_registry
from headofsocial.publishing.mock import simulate_metrics


@dataclass
class PublishAsset:
    """Transient, publish-ready view of an asset (research sources already stripped, R3)."""

    id: int
    body: str | None


def strip_research_sources(body: str | None) -> str | None:
    """Drop draft-only source lines ("Sumber: <url>") before the final publish (R3).

    Sources stay in the stored draft for human review; they are not part of the published copy.
    """
    if not body:
        return body
    kept = [line for line in body.splitlines() if not line.strip().lower().startswith("sumber:")]
    return "\n".join(kept).strip()


def _publish_view(post: Post) -> PublishAsset | None:
    """A publish-ready view whose body has research sources stripped (stored draft untouched)."""
    if post.asset is None:
        return None
    return PublishAsset(id=post.asset.id, body=strip_research_sources(post.asset.body))


async def publish_post(session: AsyncSession, post: Post) -> Post:
    """Publish a single post via its channel's publisher adapter. Handles rollback on failure.

    Relationships are eagerly re-loaded because lazy-loading them in an async session
    raises MissingGreenlet (SQLAlchemy asyncio limitation).
    """
    post = await _loaded(session, post.id)
    platform = str(post.channel.platform)
    publisher = get_registry().get(platform)

    try:
        result = await publisher.publish(post, _publish_view(post))
        post.status = PostStatus.PUBLISHED
        post.publish_result = result.to_dict()
        post.published_at = datetime.now(UTC).replace(tzinfo=None)
        if result.ok:
            _record_metrics(session, post, platform)
    except Exception as exc:  # real adapters may raise; mark failed and re-raise details
        post.status = PostStatus.FAILED
        post.publish_result = {"ok": False, "message": str(exc)}
        await session.commit()
        raise

    await session.commit()
    # Re-load eager relationships (channel/asset/metrics) so nothing lazy-loads in the
    # async session (which raises MissingGreenlet).
    return await _loaded(session, post.id)


def _record_metrics(session: AsyncSession, post: Post, platform: str) -> None:
    data = simulate_metrics(post.id, platform)
    metric = PostMetrics(**data)
    session.add(metric)
    # Keep the in-memory collection consistent (backref) so callers see the metrics
    # without a lazy reload after commit.
    post.metrics.append(metric)


async def _loaded(session: AsyncSession, post_id: int) -> Post:
    """Reload a single post with channel/asset/metadata eager-loaded (async-safe)."""
    from sqlalchemy import select

    result = await session.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(selectinload(Post.channel), selectinload(Post.asset), selectinload(Post.metrics))
    )
    return result.scalars().one()


async def publish_due(session: AsyncSession) -> list[Post]:
    """Publish all scheduled posts whose scheduled_at has passed. Used by the scheduler."""
    from datetime import datetime

    from sqlalchemy import select

    now = datetime.now(UTC).replace(tzinfo=None)
    result = await session.execute(
        select(Post)
        .where(Post.status == PostStatus.SCHEDULED)
        .where(Post.scheduled_at <= now)
        .options(selectinload(Post.channel), selectinload(Post.asset))
    )
    due = list(result.scalars().all())
    published: list[Post] = []
    for post in due:
        try:
            published.append(await publish_post(session, post))
        except Exception:
            continue  # failed posts were marked by publish_post; keep going
    return published


async def schedule_post(session: AsyncSession, post: Post) -> Post:
    """Move a draft post to scheduled.

    Validates that the post has a publish time AND an attached asset, otherwise the
    scheduler would silently skip it forever.
    """
    if post.scheduled_at is None:
        raise ValueError(
            f"Post {post.id} belum punya scheduled_at; set waktu jadwal dulu sebelum approve."
        )
    if post.asset_id is None:
        raise ValueError(
            f"Post {post.id} belum punya konten (asset). Buat konten lalu attach_asset dulu."
        )
    post.status = PostStatus.SCHEDULED
    await session.commit()
    await session.refresh(post)
    return post