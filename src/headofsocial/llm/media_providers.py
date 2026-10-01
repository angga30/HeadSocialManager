"""MediaProvider protocol and implementations.

Phase 2 ships real image generation via LiteLLM (Gemini Imagen / OpenAI gpt-image).
Video (Replicate/Runway/Veo) is Phase 3. The mock provider stays the default so the app
runs without credentials; set MEDIA_PROVIDER=litellm to generate real images.

M4 extends the protocol with **capability flags** (`supports_video`,
`supports_reference_images`) and a keyword-only `size` + `reference_images`, so
`media_service` can stay provider-agnostic: it either passes reference images straight
through, or falls back to describing them textually in the prompt.
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
    supports_reference_images: bool

    async def generate_image(
        self,
        prompt: str,
        *,
        size: str = "",
        reference_images: list[Path] | None = None,
    ) -> Path: ...
    async def generate_video(
        self,
        prompt: str,
        *,
        size: str = "",
        reference_images: list[Path] | None = None,
    ) -> Path: ...


# 1x1 dark-gray PNG used as a visible placeholder by the mock provider.
_PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


class MockMediaProvider:
    """Writes small placeholder media files (no network) so the UI has something to show."""

    supports_video = True
    supports_reference_images = True  # accepts and ignores (logged) — M4

    def __init__(self) -> None:
        self.out = settings.resolved_data_dir / "media"
        self.out.mkdir(parents=True, exist_ok=True)

    async def generate_image(
        self, prompt: str, *, size: str = "", reference_images: list[Path] | None = None
    ) -> Path:
        await asyncio.sleep(0.02)
        if reference_images:
            logger.debug("Mock provider ignoring %d reference image(s)", len(reference_images))
        path = self.out / f"mock_img_{uuid.uuid4().hex}.png"
        path.write_bytes(_PLACEHOLDER_PNG)
        return path

    async def generate_video(
        self, prompt: str, *, size: str = "", reference_images: list[Path] | None = None
    ) -> Path:
        await asyncio.sleep(0.03)
        path = self.out / f"mock_video_{uuid.uuid4().hex}.mp4"
        path.write_bytes(b"")  # placeholder file
        return path


class LiteLLMMediaProvider:
    """Real image generation via LiteLLM (multi-provider). Video is Phase 3."""

    supports_video = False

    def __init__(self) -> None:
        self.out = settings.resolved_data_dir / "media"
        self.out.mkdir(parents=True, exist_ok=True)

    @property
    def supports_reference_images(self) -> bool:
        """Only the multimodal (chat-completion) path can take reference images (M4)."""
        return settings.media_image_model.startswith("openrouter/")

    async def generate_image(
        self, prompt: str, *, size: str = "", reference_images: list[Path] | None = None
    ) -> Path:
        # OpenRouter exposes image models through chat completions (image modality), not
        # the /images/generations endpoint, so route it separately.
        if settings.media_image_model.startswith("openrouter/"):
            path = await self._generate_image_openrouter(prompt, reference_images)
        else:
            path = await self._generate_image_endpoint(prompt, size)
        logger.info("Generated 1 image via %s", settings.media_image_model)
        return path

    async def _generate_image_endpoint(self, prompt: str, size: str) -> Path:
        """Providers with an images endpoint (OpenAI, Gemini Imagen, ...)."""
        import litellm

        kwargs: dict = {"model": settings.media_image_model, "prompt": prompt, "n": 1}
        chosen_size = size or settings.media_image_size
        if chosen_size:
            kwargs["size"] = chosen_size

        response = await litellm.aimage_generation(**kwargs)
        for item in response.data:
            data = self._item_bytes(item)
            if data is not None:
                return self._write(data)
        raise RuntimeError("Image provider returned no usable image (b64_json/url).")

    async def _generate_image_openrouter(
        self, prompt: str, reference_images: list[Path] | None
    ) -> Path:
        """OpenRouter image models: chat completion with modalities=["image","text"]."""
        import litellm

        content: list[dict] = [{"type": "text", "text": prompt}]
        for ref in reference_images or []:
            data_url = self._file_to_data_url(ref)
            if data_url:
                content.append({"type": "image_url", "image_url": {"url": data_url}})

        response = await litellm.acompletion(
            model=settings.media_image_model,
            messages=[{"role": "user", "content": content}],
            modalities=["image", "text"],
        )
        message = response.choices[0].message
        for url in self._extract_image_urls(message):
            data = self._bytes_from_url(url)
            if data is not None:
                return self._write(data)
        raise RuntimeError(
            "OpenRouter returned no images. Pastikan model mendukung output image "
            "(mis. openrouter/google/gemini-2.5-flash-image) dan key valid."
        )

    def _write(self, data: bytes) -> Path:
        path = self.out / f"img_{uuid.uuid4().hex}.png"
        path.write_bytes(data)
        return path

    @staticmethod
    def _file_to_data_url(path: Path) -> str | None:
        try:
            raw = Path(path).read_bytes()
        except OSError:
            return None
        suffix = Path(path).suffix.lower().lstrip(".") or "png"
        mime = "image/jpeg" if suffix in ("jpg", "jpeg") else f"image/{suffix}"
        return f"data:{mime};base64,{base64.b64encode(raw).decode()}"

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

    async def generate_video(
        self, prompt: str, *, size: str = "", reference_images: list[Path] | None = None
    ) -> Path:
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
