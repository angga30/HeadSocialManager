"""M3/M4/M5 — channel sizing, reference-image handling, and deterministic logo compositing."""

from pathlib import Path

import pytest
from PIL import Image

from headofsocial.config import settings
from headofsocial.domain.enums import BrandAssetKind, BrandType, ContentDepth, Platform
from headofsocial.domain.models import Asset, Post
from headofsocial.domain.schemas import ChannelInput
from headofsocial.services import brand_service, media_service


class _RecordingProvider:
    """Writes a real PNG (so post-processing runs) and records the call kwargs."""

    supports_video = True

    def __init__(self, out: Path, *, supports_refs: bool = False, color=(10, 20, 30)) -> None:
        self.out = out
        self.out.mkdir(parents=True, exist_ok=True)
        self.supports_reference_images = supports_refs
        self.color = color
        self.calls: list[dict] = []

    async def generate_image(
        self, prompt: str, *, size: str = "", reference_images: list[Path] | None = None
    ) -> Path:
        path = self.out / f"gen_{len(self.calls)}.png"
        Image.new("RGB", (240, 240), self.color).save(path)
        self.calls.append({"prompt": prompt, "size": size, "refs": reference_images, "path": path})
        return path

    async def generate_video(
        self, prompt: str, *, size: str = "", reference_images: list[Path] | None = None
    ) -> Path:
        path = self.out / f"vid_{len(self.calls)}.mp4"
        path.write_bytes(b"")
        self.calls.append({"prompt": prompt, "size": size, "refs": reference_images, "path": path})
        return path


def _write_png(path: Path, color) -> Path:
    Image.new("RGB", (8, 8), color).save(path)
    return path


async def _asset_with_post(session, brand, platform: Platform, brief: str = "subject"):
    channel = await brand_service.create_channel(
        session, brand.id, ChannelInput(platform=platform, handle="h")
    )
    asset = Asset(
        brand_id=brand.id,
        type="image",
        depth=ContentDepth.VISUAL,
        media_spec=[{"media_type": "image", "creative_brief": brief, "position": 0}],
    )
    session.add(asset)
    await session.commit()
    session.add(Post(brand_id=brand.id, channel_id=channel.id, asset_id=asset.id))
    await session.commit()
    return asset


@pytest.mark.parametrize(
    "platform,expected",
    [
        (Platform.INSTAGRAM, "1080x1350"),
        (Platform.THREADS, "1080x1080"),
        (Platform.LINKEDIN, "1200x627"),
    ],
)
async def test_channel_size_requested(session, brand, monkeypatch, tmp_path, platform, expected):
    asset = await _asset_with_post(session, brand, platform)
    provider = _RecordingProvider(tmp_path / "media")
    monkeypatch.setattr(media_service, "get_media_provider", lambda: provider)

    await media_service.generate_media(session, asset)

    assert provider.calls[0]["size"] == expected
    with Image.open(asset.media_files[0]) as image:
        w, h = (int(x) for x in expected.split("x"))
        assert image.size == (w, h)


async def test_reference_described_when_provider_unsupported(session, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    brand = await brand_service.create_brand(session, "Personal", BrandType.PERSONAL, language="id")
    await brand_service.register_brand_asset(
        session, brand.id, BrandAssetKind.FACE_PHOTO, _write_png(tmp_path / "face.png", (1, 2, 3)),
        label="wanita 30-an, rambut pendek",
    )
    asset = Asset(
        brand_id=brand.id,
        type="image",
        depth=ContentDepth.VISUAL,
        media_spec=[{"media_type": "image", "creative_brief": "portrait", "position": 0}],
    )
    session.add(asset)
    await session.commit()

    provider = _RecordingProvider(tmp_path / "media", supports_refs=False)
    monkeypatch.setattr(media_service, "get_media_provider", lambda: provider)
    await media_service.generate_media(session, asset)

    call = provider.calls[0]
    assert call["refs"] is None
    assert "MATCH THESE REFERENCES: wanita 30-an, rambut pendek" in call["prompt"]


async def test_references_passed_when_provider_supports(session, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    brand = await brand_service.create_brand(session, "Personal", BrandType.PERSONAL, language="id")
    await brand_service.register_brand_asset(
        session, brand.id, BrandAssetKind.FACE_PHOTO, _write_png(tmp_path / "face.png", (1, 2, 3)),
        label="wanita 30-an",
    )
    asset = Asset(
        brand_id=brand.id,
        type="image",
        depth=ContentDepth.VISUAL,
        media_spec=[{"media_type": "image", "creative_brief": "portrait", "position": 0}],
    )
    session.add(asset)
    await session.commit()

    provider = _RecordingProvider(tmp_path / "media", supports_refs=True)
    monkeypatch.setattr(media_service, "get_media_provider", lambda: provider)
    await media_service.generate_media(session, asset)

    call = provider.calls[0]
    assert call["refs"] and Path(call["refs"][0]).exists()
    assert "MATCH THESE REFERENCES" not in call["prompt"]


async def test_logo_overlay_is_applied(session, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    brand = await brand_service.create_brand(session, "Biz", BrandType.BUSINESS, language="id")
    await brand_service.register_brand_asset(
        session, brand.id, BrandAssetKind.LOGO, _write_png(tmp_path / "logo.png", (255, 0, 0)),
        is_primary=True,
    )
    await brand_service.set_visual_style(
        session,
        brand.id,
        {
            "palette": ["#111111", "#222222"],
            "logo_overlay": {"position": "bottom-right", "opacity": 1.0, "margin": 10},
        },
    )
    asset = Asset(
        brand_id=brand.id,
        type="image",
        depth=ContentDepth.VISUAL,
        media_spec=[{"media_type": "image", "creative_brief": "x", "position": 0}],
    )
    session.add(asset)
    await session.commit()

    provider = _RecordingProvider(tmp_path / "media", color=(10, 20, 30))
    monkeypatch.setattr(media_service, "get_media_provider", lambda: provider)
    await media_service.generate_media(session, asset)

    with Image.open(asset.media_files[0]) as image:
        # Logo width = 18% of 240 = 43px, margin 10 -> spans x/y 187..230.
        assert image.getpixel((200, 200)) == (255, 0, 0)
        assert image.getpixel((5, 5)) == (10, 20, 30)


async def test_logo_overlay_noop_without_logo(session, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    brand = await brand_service.create_brand(session, "Plain", BrandType.BUSINESS, language="id")
    asset = Asset(
        brand_id=brand.id,
        type="image",
        depth=ContentDepth.VISUAL,
        media_spec=[{"media_type": "image", "creative_brief": "x", "position": 0}],
    )
    session.add(asset)
    await session.commit()

    provider = _RecordingProvider(tmp_path / "media", color=(10, 20, 30))
    monkeypatch.setattr(media_service, "get_media_provider", lambda: provider)
    await media_service.generate_media(session, asset)

    with Image.open(asset.media_files[0]) as image:
        assert image.getpixel((200, 200)) == (10, 20, 30)
