"""MediaProvider protocol and implementations.

Phase 2 ships real image generation via LiteLLM (Gemini Imagen / OpenAI gpt-image).
Video (Replicate/Runway/Veo) is Phase 3. The mock provider stays the default so the app
runs without credentials; set MEDIA_PROVIDER=litellm to generate real images.
"""

import asyncio
import base64
import logging
import uuid
from pathlib import Path
from typing import Protocol

from headofsocial.config import settings
from headofsocial.domain.enums import MediaProviderKind, MediaType

logger = logging.getLogger(__name__)


class MediaNotSupportedError(RuntimeError):
    """Raised when the active provider cannot produce a requested media type."""


class MediaProvider(Protocol):
    supports_video: bool

    async def generate_image(self, prompt: str, n: int = 1) -> list[Path]: ...
    async def generate_video(self, prompt: str, n: int = 1) -> list[Path]: ...


# 1x1 dark-gray PNG used as a visible placeholder by the mock provider.
_PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


class MockMediaProvider:
    """Writes small placeholder media files (no network) so the UI has something to show."""

    supports_video = True

    def __init__(self) -> None:
        self.out = settings.resolved_data_dir / "media"
        self.out.mkdir(parents=True, exist_ok=True)

    async def generate_image(self, prompt: str, n: int = 1) -> list[Path]:
        await asyncio.sleep(0.02 * n)
        paths: list[Path] = []
        for _ in range(n):
            path = self.out / f"mock_img_{uuid.uuid4().hex}.png"
            path.write_bytes(_PLACEHOLDER_PNG)
            paths.append(path)
        return paths

    async def generate_video(self, prompt: str, n: int = 1) -> list[Path]:
        await asyncio.sleep(0.03 * n)
        paths: list[Path] = []
        for _ in range(n):
            path = self.out / f"mock_video_{uuid.uuid4().hex}.mp4"
            path.write_bytes(b"")  # placeholder file
            paths.append(path)
        return paths


class LiteLLMMediaProvider:
    """Real image generation via LiteLLM (multi-provider). Video is Phase 3."""

    supports_video = False

    def __init__(self) -> None:
        self.out = settings.resolved_data_dir / "media"
        self.out.mkdir(parents=True, exist_ok=True)

    async def generate_image(self, prompt: str, n: int = 1) -> list[Path]:
        # OpenRouter exposes image models through chat completions (image modality), not
        # the /images/generations endpoint, so route it separately.
        if settings.media_image_model.startswith("openrouter/"):
            paths = await self._generate_image_openrouter(prompt, n)
        else:
            paths = await self._generate_image_endpoint(prompt, n)
        logger.info("Generated %d image(s) via %s", len(paths), settings.media_image_model)
        return paths

    async def _generate_image_endpoint(self, prompt: str, n: int) -> list[Path]:
        """Providers with an images endpoint (OpenAI, Gemini Imagen, ...)."""
        import litellm

        kwargs: dict = {"model": settings.media_image_model, "prompt": prompt, "n": n}
        if settings.media_image_size:
            kwargs["size"] = settings.media_image_size

        response = await litellm.aimage_generation(**kwargs)
        paths: list[Path] = []
        for item in response.data:
            data = self._item_bytes(item)
            if data is not None:
                paths.append(self._write(data))
        if not paths:
            raise RuntimeError("Image provider returned no usable images (b64_json/url).")
        return paths

    async def _generate_image_openrouter(self, prompt: str, n: int) -> list[Path]:
        """OpenRouter image models: chat completion with modalities=["image","text"]."""
        import litellm

        paths: list[Path] = []
        for _ in range(max(1, n)):
            response = await litellm.acompletion(
                model=settings.media_image_model,
                messages=[{"role": "user", "content": prompt}],
                modalities=["image", "text"],
            )
            message = response.choices[0].message
            for url in self._extract_image_urls(message):
                data = self._bytes_from_url(url)
                if data is not None:
                    paths.append(self._write(data))
        if not paths:
            raise RuntimeError(
                "OpenRouter returned no images. Pastikan model mendukung output image "
                "(mis. openrouter/google/gemini-2.5-flash-image) dan key valid."
            )
        return paths

    def _write(self, data: bytes) -> Path:
        path = self.out / f"img_{uuid.uuid4().hex}.png"
        path.write_bytes(data)
        return path

    @staticmethod
    def _extract_image_urls(message) -> list[str]:
        urls: list[str] = []
        for item in getattr(message, "images", None) or []:
            if isinstance(item, dict):
                ref = item.get("image_url", item)
                url = ref.get("url") if isinstance(ref, dict) else str(ref)
            else:
                ref = getattr(item, "image_url", None)
                url = getattr(ref, "url", None) if ref else None
            if url:
                urls.append(url)
        return urls

    @staticmethod
    def _bytes_from_url(url: str) -> bytes | None:
        if url.startswith("data:"):
            _, _, b64 = url.partition(",")
            return base64.b64decode(b64)
        if url.startswith("http"):
            import httpx

            return httpx.get(url, timeout=60).content
        return None

    async def generate_video(self, prompt: str, n: int = 1) -> list[Path]:
        raise MediaNotSupportedError(
            "Provider ini belum mendukung video (fase 3). Gunakan depth text/visual/carousel, "
            "atau set HEADSOF_MEDIA_PROVIDER=mock untuk placeholder video."
        )

    @staticmethod
    def _item_bytes(item) -> bytes | None:
        b64 = getattr(item, "b64_json", None)
        if b64:
            return base64.b64decode(b64)
        url = getattr(item, "url", None)
        if url:
            import httpx

            return httpx.get(url, timeout=60).content
        return None


def get_media_provider(kind: str = "") -> MediaProvider:
    kind = (kind or settings.media_provider).lower()
    if kind == MediaProviderKind.MOCK.value:
        return MockMediaProvider()
    if kind == MediaProviderKind.LITELLM.value:
        return LiteLLMMediaProvider()
    raise ValueError(f"Unknown media provider: {kind}")


def provider_supports_video(kind: str = "") -> bool:
    """Whether the active media provider can generate video (mock yes; litellm no, fase 3)."""
    return bool(getattr(get_media_provider(kind), "supports_video", False))


def budget() -> dict[str, int]:
    return {
        "max_images": settings.max_images_per_asset,
        "max_videos": settings.max_videos_per_asset,
    }


def validate_media_spec(media_type: MediaType, count: int) -> list[str]:
    """Return a list of budget violations (empty means OK)."""
    b = budget()
    if media_type == MediaType.IMAGE and count > b["max_images"]:
        return [f"image count {count} exceeds max {b['max_images']}"]
    if media_type == MediaType.VIDEO and count > b["max_videos"]:
        return [f"video count {count} exceeds max {b['max_videos']}"]
    return []