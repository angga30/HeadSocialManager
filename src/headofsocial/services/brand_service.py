"""Brand (and channel) CRUD + positioning persistence."""

from sqlalchemy.ext.asyncio import AsyncSession

from headofsocial.domain.enums import BrandType, Platform
from headofsocial.domain.models import Brand, Channel
from headofsocial.domain.schemas import ChannelInput, PositioningRecommendation
from headofsocial.storage import repos


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