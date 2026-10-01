"""Thin repository helpers over AsyncSession for common read/upsert patterns.

Relationships are eager-loaded (selectinload) by default so consumers never trigger a
lazy load inside an async session, which raises SQLAlchemy's MissingGreenlet.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from headofsocial.domain.models import (
    Asset,
    Brand,
    Channel,
    Plan,
    Post,
    PostMetrics,
)

_POST_OPTIONS = (selectinload(Post.channel), selectinload(Post.asset), selectinload(Post.plan))


async def list_brands(session: AsyncSession) -> list[Brand]:
    result = await session.execute(select(Brand).order_by(Brand.name))
    return list(result.scalars().all())


async def get_brand(session: AsyncSession, brand_id: int) -> Brand | None:
    return await session.get(Brand, brand_id)


async def list_channels(session: AsyncSession, brand_id: int | None = None) -> list[Channel]:
    stmt = select(Channel).order_by(Channel.created_at)
    if brand_id is not None:
        stmt = stmt.where(Channel.brand_id == brand_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_plans(session: AsyncSession, brand_id: int | None = None) -> list[Plan]:
    stmt = select(Plan).order_by(Plan.period.desc())
    if brand_id is not None:
        stmt = stmt.where(Plan.brand_id == brand_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_posts_by_status(session: AsyncSession, brand_id: int | None = None) -> dict[str, int]:
    stmt = select(Post.status, func.count(Post.id)).group_by(Post.status)
    if brand_id is not None:
        stmt = stmt.where(Post.brand_id == brand_id)
    result = await session.execute(stmt)
    return {status: count for status, count in result.all()}


async def list_posts(session: AsyncSession, brand_id: int | None = None) -> list[Post]:
    stmt = select(Post).options(*_POST_OPTIONS).order_by(Post.scheduled_at.desc())
    if brand_id is not None:
        stmt = stmt.where(Post.brand_id == brand_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_metrics_for_posts(session: AsyncSession, post_ids: list[int]) -> list[PostMetrics]:
    if not post_ids:
        return []
    result = await session.execute(select(PostMetrics).where(PostMetrics.post_id.in_(post_ids)))
    return list(result.scalars().all())


async def list_assets(session: AsyncSession, brand_id: int | None = None) -> list[Asset]:
    stmt = select(Asset).order_by(Asset.created_at.desc())
    if brand_id is not None:
        stmt = stmt.where(Asset.brand_id == brand_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())