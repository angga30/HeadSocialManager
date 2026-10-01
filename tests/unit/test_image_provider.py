"""Phase 2/M4: LiteLLM image provider (mocked network) + provider selection.

Both image paths are covered: providers with an images endpoint (OpenAI/Gemini Imagen)
and OpenRouter image models (chat completion with image modality, reference images).
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


def test_reference_support_flag(monkeypatch):
    assert MockMediaProvider.supports_reference_images is True
    monkeypatch.setattr(settings, "media_image_model", "gemini/imagen-3.0-generate-002")
    assert LiteLLMMediaProvider().supports_reference_images is False  # endpoint model (Imagen)
    monkeypatch.setattr(settings, "media_image_model", "openrouter/google/gemini-2.5-flash-image")
    assert LiteLLMMediaProvider().supports_reference_images is True  # multimodal path
    assert LiteLLMMediaProvider.supports_video is False


async def test_litellm_image_endpoint_writes_file(monkeypatch, tmp_path):
    """Non-OpenRouter model -> litellm.aimage_generation (images endpoint)."""
    monkeypatch.setattr(settings, "media_image_model", "openai/gpt-image-1")

    async def fake_aimage_generation(**kwargs):
        assert kwargs["n"] == 1
        assert kwargs["model"] == "openai/gpt-image-1"
        assert kwargs["size"] == "1080x1350"  # per-channel size passed through (M3)
        return SimpleNamespace(data=[SimpleNamespace(b64_json=_PNG, url=None)])

    import litellm

    monkeypatch.setattr(litellm, "aimage_generation", fake_aimage_generation)

    provider = LiteLLMMediaProvider()
    provider.out = tmp_path / "media"
    provider.out.mkdir(parents=True, exist_ok=True)

    path = await provider.generate_image("a coffee cup", size="1080x1350")
    assert isinstance(path, Path) and path.exists()
    assert path.read_bytes().startswith(b"\x89PNG")


async def test_litellm_image_openrouter_passes_references(monkeypatch, tmp_path):
    """openrouter/ model -> chat completion with image modality + reference images."""
    monkeypatch.setattr(settings, "media_image_model", "openrouter/google/gemini-2.5-flash-image")
    assert LiteLLMMediaProvider().supports_reference_images is True

    ref = tmp_path / "ref.png"
    ref.write_bytes(b"\x89PNG\r\n\x1a\n ref")

    async def fake_acompletion(**kwargs):
        assert kwargs["modalities"] == ["image", "text"]
        content = kwargs["messages"][0]["content"]
        assert any(part.get("type") == "image_url" for part in content)
        msg = SimpleNamespace(
            images=[{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{_PNG}"}}]
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    provider = LiteLLMMediaProvider()
    provider.out = tmp_path / "media"
    provider.out.mkdir(parents=True, exist_ok=True)

    path = await provider.generate_image("a coffee cup", reference_images=[ref])
    assert path.read_bytes().startswith(b"\x89PNG")


async def test_litellm_video_not_supported():
    with pytest.raises(MediaNotSupportedError):
        await LiteLLMMediaProvider().generate_video("clip")


async def test_mock_provider_still_works():
    path = await media_providers.MockMediaProvider().generate_image("x")
    assert isinstance(path, Path)
