"""Phase 2: LiteLLM image provider (mocked network) + provider selection.

Both image paths are covered: providers with an images endpoint (OpenAI/Gemini Imagen)
and OpenRouter image models (chat completion with image modality).
"""

import base64
from pathlib import Path
from types import SimpleNamespace

import pytest

from headofsocial.config import settings
from headofsocial.llm import media_providers
from headofsocial.llm.media_providers import (
    LiteLLMMediaProvider,
    MediaNotSupportedError,
    MockMediaProvider,
    get_media_provider,
)

_PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n fake").decode()


def test_provider_selection():
    assert isinstance(get_media_provider("mock"), MockMediaProvider)
    assert isinstance(get_media_provider("litellm"), LiteLLMMediaProvider)
    with pytest.raises(ValueError):
        get_media_provider("nope")


async def test_litellm_image_endpoint_writes_files(monkeypatch, tmp_path):
    """Non-OpenRouter model -> litellm.aimage_generation (images endpoint)."""
    monkeypatch.setattr(settings, "media_image_model", "openai/gpt-image-1")

    async def fake_aimage_generation(**kwargs):
        assert kwargs["n"] == 2
        assert kwargs["model"] == "openai/gpt-image-1"
        return SimpleNamespace(
            data=[SimpleNamespace(b64_json=_PNG, url=None), SimpleNamespace(b64_json=_PNG, url=None)]
        )

    import litellm

    monkeypatch.setattr(litellm, "aimage_generation", fake_aimage_generation)

    provider = LiteLLMMediaProvider()
    provider.out = tmp_path / "media"
    provider.out.mkdir(parents=True, exist_ok=True)

    paths = await provider.generate_image("a coffee cup", n=2)
    assert len(paths) == 2
    for p in paths:
        assert isinstance(p, Path) and p.exists()
        assert p.read_bytes().startswith(b"\x89PNG")


async def test_litellm_image_openrouter_writes_files(monkeypatch, tmp_path):
    """openrouter/ model -> chat completion with image modality."""
    monkeypatch.setattr(settings, "media_image_model", "openrouter/google/gemini-2.5-flash-image")

    async def fake_acompletion(**kwargs):
        assert kwargs["modalities"] == ["image", "text"]
        msg = SimpleNamespace(
            images=[{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{_PNG}"}}]
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    provider = LiteLLMMediaProvider()
    provider.out = tmp_path / "media"
    provider.out.mkdir(parents=True, exist_ok=True)

    paths = await provider.generate_image("a coffee cup", n=1)
    assert len(paths) == 1
    assert paths[0].read_bytes().startswith(b"\x89PNG")


async def test_litellm_video_not_supported():
    with pytest.raises(MediaNotSupportedError):
        await LiteLLMMediaProvider().generate_video("clip", n=1)


async def test_mock_provider_still_works():
    paths = await media_providers.MockMediaProvider().generate_image("x", n=3)
    assert len(paths) == 3