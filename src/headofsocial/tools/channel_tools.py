"""Tools for channel CRUD and channel style lookup."""

from headofsocial.channels.styles import get_style, style_instruction_block
from headofsocial.domain.models import Brand
from headofsocial.domain.schemas import ChannelInput
from headofsocial.services import brand_service
from headofsocial.tools._deps import channel_to_dict, run

_PLATFORMS = ("instagram", "threads", "linkedin")


async def create_channel(brand_id: int, platform: str, handle: str, language: str = "") -> dict:
    """Connect a social channel to a brand.

    Args:
        brand_id: Target brand id.
        platform: instagram | threads | linkedin.
        handle: The account handle/name on that platform.
        language: Optional content language override for this channel.
    """
    if platform not in _PLATFORMS:
        return {"ok": False, "error": f"platform must be one of {_PLATFORMS}"}
    data = ChannelInput(platform=platform, handle=handle, language=language or None)
    async def _fn(session):
        channel = await brand_service.create_channel(session, brand_id, data)
        return channel_to_dict(channel)
    return await run(_fn)


async def list_channels(brand_id: int) -> dict:
    """List all social channels connected to a brand."""
    async def _fn(session):
        channels = await brand_service.list_channels(session, brand_id)
        return {"ok": True, "channels": [channel_to_dict(c) for c in channels]}
    return await run(_fn)


async def get_channel_style(brand_id: int, platform: str) -> dict:
    """Return the writing-style profile for a channel, for content creation.

    Args:
        brand_id: Brand owning the channel.
        platform: instagram | threads | linkedin.
    """
    if platform not in _PLATFORMS:
        return {"ok": False, "error": f"platform must be one of {_PLATFORMS}"}
    async def _fn(session):
        brand = await session.get(Brand, brand_id)
        if brand is None:
            return {"ok": False, "error": f"Brand {brand_id} not found"}
        overrides = None
        for c in await brand_service.list_channels(session, brand_id):
            if str(c.platform) == platform:
                overrides = c.style_overrides
                break
        style = get_style(platform, overrides)
        return {
            "ok": True,
            "platform": platform,
            "label": style.label,
            "caption_limit_chars": style.caption_limit_chars,
            "hashtag_range": list(style.hashtag_range),
            "emoji_level": style.emoji_level,
            "image_aspect": style.image_aspect,
            "image_size": style.image_size,
            "suggested_depths": [d.value for d in style.suggested_depths],
            "style_instruction": style_instruction_block(style, brand.language),
        }
    return await run(_fn)