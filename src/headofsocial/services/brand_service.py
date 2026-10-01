"""Brand (and channel) CRUD + positioning persistence."""

import shutil
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from headofsocial.config import settings
from headofsocial.domain.enums import BrandAssetKind, BrandType, Platform
from headofsocial.domain.models import Brand, BrandAsset, Channel
from headofsocial.domain.schemas import ChannelInput, PositioningRecommendation, VisualStyle
from headofsocial.storage import repos

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


async def create_brand(
    session: AsyncSession,
    name: str,
    type_: BrandType,
    description: str | None = None,
    industry: str | None = None,
    website: str | None = None,
    language: str = "id",
) -> Brand:
    brand = Brand(
        name=name,
        type=type_,
        description=description,
        industry=industry,
        website=website,
        language=language,
    )
    session.add(brand)
    await session.commit()
    await session.refresh(brand)
    return brand


async def create_channel(session: AsyncSession, brand_id: int, data: ChannelInput) -> Channel:
    channel = Channel(
        brand_id=brand_id,
        platform=data.platform,
        handle=data.handle,
        language=data.language,
        style_overrides=data.style_overrides,
    )
    session.add(channel)
    await session.commit()
    await session.refresh(channel)
    return channel


async def resolve_channel_language(brand: Brand, channel: Channel) -> str:
    """Channel language override falls back to the brand default."""
    return channel.language or brand.language


async def apply_recommendation(
    session: AsyncSession, brand_id: int, rec: PositioningRecommendation
) -> Brand:
    brand = await session.get(Brand, brand_id)
    if brand is None:
        raise ValueError(f"Brand {brand_id} not found")
    brand.positioning_statement = rec.positioning_statement
    brand.target_audience = rec.target_audience
    brand.differentiators = rec.differentiators
    brand.voice_tone = rec.voice_tone
    brand.content_pillars = rec.content_pillars
    if rec.visual_style is not None:
        brand.visual_style = rec.visual_style.model_dump()
    await session.commit()
    await session.refresh(brand)
    return brand


async def register_brand_asset(
    session: AsyncSession,
    brand_id: int,
    kind: str,
    source_path: str | Path,
    label: str | None = None,
    is_primary: bool = False,
) -> BrandAsset:
    """Copy a validated image into data/brand_assets and record it (M1)."""
    brand = await session.get(Brand, brand_id)
    if brand is None:
        raise ValueError(f"Brand {brand_id} not found")
    try:
        asset_kind = BrandAssetKind(kind)
    except ValueError as exc:
        raise ValueError(
            f"kind must be one of {[k.value for k in BrandAssetKind]}"
        ) from exc

    source = Path(source_path)
    if not source.is_file():
        raise ValueError(f"File not found: {source}")
    if source.suffix.lower() not in _IMAGE_SUFFIXES:
        raise ValueError(f"Unsupported file type {source.suffix!r}; use {sorted(_IMAGE_SUFFIXES)}")

    dest_dir = settings.resolved_brand_assets_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{brand_id}_{asset_kind.value}_{uuid.uuid4().hex[:8]}{source.suffix.lower()}"
    shutil.copyfile(source, dest)

    asset = BrandAsset(
        brand_id=brand_id,
        kind=asset_kind,
        file_path=str(dest),
        label=label,
        is_primary=is_primary,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return asset


async def list_brand_assets(session: AsyncSession, brand_id: int) -> list[BrandAsset]:
    return await repos.list_brand_assets(session, brand_id)


async def set_visual_style(
    session: AsyncSession, brand_id: int, visual_style: VisualStyle | dict
) -> Brand:
    """Validate and persist the locked visual style for a brand (M1)."""
    style = visual_style if isinstance(visual_style, VisualStyle) else VisualStyle(**visual_style)
    brand = await session.get(Brand, brand_id)
    if brand is None:
        raise ValueError(f"Brand {brand_id} not found")
    brand.visual_style = style.model_dump()
    await session.commit()
    await session.refresh(brand)
    return brand


async def list_brands(session: AsyncSession) -> list[Brand]:
    return await repos.list_brands(session)


async def list_channels(session: AsyncSession, brand_id: int | None = None) -> list[Channel]:
    return await repos.list_channels(session, brand_id)


async def count_channels_per_platform(session: AsyncSession, brand_id: int) -> dict[str, int]:
    channels = await repos.list_channels(session, brand_id)
    counts: dict[str, int] = {}
    for ch in channels:
        counts[Platform(ch.platform).value] = counts.get(Platform(ch.platform).value, 0) + 1
    return counts