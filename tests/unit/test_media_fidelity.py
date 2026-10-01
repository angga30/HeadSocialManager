"""M4 fidelity — vision-derived identity directive + per-item generation into the asset."""

from pathlib import Path

from headofsocial.domain.enums import ContentDepth
from headofsocial.domain.models import Asset
from headofsocial.media.prompt_builder import fidelity_block
from headofsocial.services import media_service


def test_fidelity_block_directives():
    assert "PRESERVE EXACT FACIAL IDENTITY" in fidelity_block("person", "almond eyes")
    assert "LOGO IMMUTABLE" in fidelity_block("logo", "red circle")
    assert "PRESERVE PRODUCT IDENTITY" in fidelity_block("product", "matte bottle")
    assert fidelity_block("style", "") == ""
    assert fidelity_block("unknown", "note").startswith("MATCH THIS REFERENCE STYLE")


class _FakeProvider:
    supports_video = True
    supports_reference_images = False

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def generate_image(self, prompt, *, size="", reference_images=None):
        self.calls.append({"prompt": prompt, "size": size, "refs": reference_images})
        return Path(f"/tmp/fake_{len(self.calls)}.png")

    async def generate_video(self, prompt, *, size="", reference_images=None):
        self.calls.append({"prompt": prompt, "size": size, "refs": reference_images})
        return Path(f"/tmp/fakev_{len(self.calls)}.mp4")


async def test_generate_media_item_injects_fidelity_and_records_position(session, brand, monkeypatch):
    provider = _FakeProvider()
    monkeypatch.setattr(media_service, "get_media_provider", lambda: provider)
    asset = Asset(
        brand_id=brand.id,
        type="image",
        depth=ContentDepth.CAROUSEL,
        media_spec=[
            {"media_type": "image", "creative_brief": "shot A", "position": 0},
            {"media_type": "image", "creative_brief": "shot B", "position": 1},
        ],
    )
    session.add(asset)
    await session.commit()

    p1 = await media_service.generate_media_item(
        session, asset, 1, fidelity_notes="almond eyes, sharp jaw", fidelity_subject="person"
    )
    p0 = await media_service.generate_media_item(session, asset, 0)

    assert asset.media_files == [p0, p1]
    assert "PRESERVE EXACT FACIAL IDENTITY" in provider.calls[0]["prompt"]
    assert "almond eyes, sharp jaw" in provider.calls[0]["prompt"]
    # The second (no fidelity) call carries no fidelity directive.
    assert "PRESERVE EXACT FACIAL IDENTITY" not in provider.calls[1]["prompt"]


class _RefRecordingProvider:
    supports_video = True
    supports_reference_images = True

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def generate_image(self, prompt, *, size="", reference_images=None):
        self.calls.append({"prompt": prompt, "refs": reference_images})
        return Path(f"/tmp/ref_{len(self.calls)}.png")

    async def generate_video(self, prompt, *, size="", reference_images=None):
        self.calls.append({"prompt": prompt, "refs": reference_images})
        return Path(f"/tmp/refv_{len(self.calls)}.mp4")


async def test_all_reference_photos_are_sent(session, monkeypatch, tmp_path):
    from PIL import Image

    from headofsocial.config import settings
    from headofsocial.domain.enums import BrandAssetKind, BrandType
    from headofsocial.services import brand_service

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    provider = _RefRecordingProvider()
    monkeypatch.setattr(media_service, "get_media_provider", lambda: provider)

    brand = await brand_service.create_brand(session, "Personal", BrandType.PERSONAL, language="id")
    for i, color in enumerate([(1, 2, 3), (4, 5, 6), (7, 8, 9)]):
        png = tmp_path / f"face{i}.png"
        Image.new("RGB", (8, 8), color).save(png)
        await brand_service.register_brand_asset(
            session, brand.id, BrandAssetKind.FACE_PHOTO, png, label=f"face{i}"
        )

    asset = Asset(
        brand_id=brand.id,
        type="image",
        depth=ContentDepth.VISUAL,
        media_spec=[{"media_type": "image", "creative_brief": "portrait", "position": 0}],
    )
    session.add(asset)
    await session.commit()

    await media_service.generate_media_item(session, asset, 0)

    refs = provider.calls[0]["refs"]
    assert refs is not None and len(refs) == 3
