"""Shared helpers for ADK tools: DB bootstrap, session wrapper, model serializers."""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from headofsocial.domain.models import Asset, Brand, BrandAsset, Channel, Plan, Post
from headofsocial.storage.db import SessionFactory, create_all, verify_writable

logger = logging.getLogger(__name__)
_db_ready = False
_boot_lock = asyncio.Lock()


async def ensure_db() -> None:
    """Create tables once (idempotent, guarded) so tools/screens work without an init step."""
    global _db_ready
    if _db_ready:
        return
    async with _boot_lock:
        if not _db_ready:
            verify_writable()  # clear error now beats "readonly database" on every later write
            await create_all()
            _db_ready = True


def brand_to_dict(brand: Brand) -> dict:
    return {
        "id": brand.id,
        "name": brand.name,
        "type": str(brand.type),
        "description": brand.description,
        "industry": brand.industry,
        "website": brand.website,
        "language": brand.language,
        "positioning_statement": brand.positioning_statement,
        "target_audience": brand.target_audience or [],
        "differentiators": brand.differentiators or [],
        "voice_tone": brand.voice_tone,
        "content_pillars": brand.content_pillars or [],
        "visual_style": brand.visual_style,
    }


def brand_asset_to_dict(asset: BrandAsset) -> dict:
    return {
        "id": asset.id,
        "brand_id": asset.brand_id,
        "kind": str(asset.kind),
        "file_path": asset.file_path,
        "label": asset.label,
        "is_primary": bool(asset.is_primary),
        "url": brand_asset_url(asset.file_path),
    }


def brand_asset_url(path: str) -> str:
    """Map a stored brand-asset path to a served URL (FastAPI mounts it at /brand-assets)."""
    from pathlib import Path

    return f"/brand-assets/{Path(path).name}"


def channel_to_dict(channel: Channel) -> dict:
    return {
        "id": channel.id,
        "brand_id": channel.brand_id,
        "platform": str(channel.platform),
        "handle": channel.handle,
        "language": channel.language,
        "style_overrides": channel.style_overrides or {},
    }


def asset_to_dict(asset: Asset) -> dict:
    return {
        "id": asset.id,
        "brand_id": asset.brand_id,
        "type": str(asset.type),
        "status": str(asset.status),
        "depth": str(asset.depth) if asset.depth else None,
        "body": asset.body,
        "media_spec": asset.media_spec or [],
        "media_files": asset.media_files or [],
    }


def plan_to_dict(plan: Plan) -> dict:
    return {
        "id": plan.id,
        "brand_id": plan.brand_id,
        "period": plan.period,
        "status": str(plan.status),
        "theme": plan.theme,
        "weekly_themes": plan.weekly_themes or [],
        "cadence": plan.cadence or {},
        "content_mix": plan.content_mix or {},
        "key_dates": plan.key_dates or [],
    }


def media_url(path: str) -> dict:
    """Map a stored media path to a served URL (FastAPI mounts data/media at /media)."""
    from pathlib import Path

    name = Path(path).name
    return {"filename": name, "url": f"/media/{name}"}


def post_to_dict(post: Post) -> dict:
    media_files = (post.asset.media_files or []) if post.asset else []
    return {
        "id": post.id,
        "brand_id": post.brand_id,
        "channel_id": post.channel_id,
        "channel": post.channel.platform if post.channel else None,
        "handle": post.channel.handle if post.channel else None,
        "asset_id": post.asset_id,
        "plan_id": post.plan_id,
        "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
        "status": str(post.status),
        "pillar": post.pillar,
        "depth_hint": post.depth_hint,
        "body": post.asset.body if post.asset and post.asset.body else None,
        "headline": (post.asset.body or "")[:80] if post.asset and post.asset.body else "",
        "media": [media_url(p) for p in media_files],
        "publish_result": post.publish_result,
        "published_at": post.published_at.isoformat() if post.published_at else None,
    }


async def load_post(session: AsyncSession, post_id: int) -> Post | None:
    """Load a post with channel/asset/plan eager-loaded (safe to serialize in async)."""
    result = await session.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(selectinload(Post.channel), selectinload(Post.asset), selectinload(Post.plan))
    )
    return result.scalars().one_or_none()


async def run(fn):
    """Run an async tool body against a fresh session; commits on success.

    Any exception is rolled back and returned as {ok: False, error} instead of propagating —
    a tool error must not abort the whole agent run (ADK treats a raised tool as fatal).
    """
    try:
        await ensure_db()
    except Exception as exc:
        logger.exception("Tool failed during DB init")
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    async with SessionFactory() as session:
        try:
            result = await fn(session)
            await session.commit()
            return result
        except Exception as exc:
            await session.rollback()
            logger.exception("Tool failed")
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


async def session_ctx() -> AsyncSession:
    await ensure_db()
    return SessionFactory()