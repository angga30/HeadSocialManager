"""Video capability guard: tool returns an error instead of crashing the agent run."""

import pytest

from headofsocial.config import settings
from headofsocial.domain.enums import ContentDepth
from headofsocial.domain.models import Asset
from headofsocial.llm.media_providers import (
    LiteLLMMediaProvider,
    MediaNotSupportedError,
    MockMediaProvider,
    provider_supports_video,
)
from headofsocial.services import media_service
from headofsocial.tools import media_tools


def test_provider_video_capability():
    assert provider_supports_video("mock") is True
    assert provider_supports_video("litellm") is False
    assert MockMediaProvider.supports_video is True
    assert LiteLLMMediaProvider.supports_video is False


async def test_generate_media_service_rejects_video(session, brand, monkeypatch):
    monkeypatch.setattr(settings, "media_provider", "litellm")
    asset = Asset(
        brand_id=brand.id,
        type="mixed",
        depth=ContentDepth.RICH,
        media_spec=[
            {"media_type": "image", "creative_brief": "cover", "position": 0},
            {"media_type": "video", "creative_brief": "reel", "position": 1},
        ],
    )
    session.add(asset)
    await session.commit()
    with pytest.raises(MediaNotSupportedError):
        await media_service.generate_media(session, asset)


async def test_generate_media_tool_returns_error_not_raise(session, brand, monkeypatch):
    """The tool must not raise (that would abort the ADK run)."""
    monkeypatch.setattr(settings, "media_provider", "litellm")
    asset = Asset(
        brand_id=brand.id,
        type="video",
        depth=ContentDepth.MOTION,
        media_spec=[{"media_type": "video", "creative_brief": "reel", "position": 0}],
    )
    session.add(asset)
    await session.commit()

    result = await media_tools.generate_media(asset.id)
    assert result["ok"] is False
    assert "video" in result["error"].lower()