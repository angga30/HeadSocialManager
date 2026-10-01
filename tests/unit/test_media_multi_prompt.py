"""A5/M2 — generate_media uses each spec item's own creative brief (distinct carousel images)
and applies the central scaffold (series marker) to every prompt."""

from pathlib import Path

from headofsocial.domain.enums import ContentDepth
from headofsocial.domain.models import Asset
from headofsocial.services import media_service


class _FakeProvider:
    supports_video = True
    supports_reference_images = False

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def generate_image(
        self, prompt: str, *, size: str = "", reference_images: list[Path] | None = None
    ) -> Path:
        self.calls.append({"prompt": prompt, "size": size, "refs": reference_images})
        return Path(f"/tmp/img_{len(self.calls)}.png")

    async def generate_video(
        self, prompt: str, *, size: str = "", reference_images: list[Path] | None = None
    ) -> Path:
        self.calls.append({"prompt": prompt, "size": size, "refs": reference_images})
        return Path(f"/tmp/vid_{len(self.calls)}.mp4")


async def test_each_spec_item_uses_its_own_brief(session, brand, monkeypatch):
    fake = _FakeProvider()
    monkeypatch.setattr(media_service, "get_media_provider", lambda: fake)

    asset = Asset(
        brand_id=brand.id,
        type="image",
        depth=ContentDepth.CAROUSEL,
        body="carousel",
        media_spec=[
            {"media_type": "image", "creative_brief": "shot A", "position": 0},
            {"media_type": "image", "creative_brief": "shot B", "position": 1},
            {"media_type": "image", "creative_brief": "shot C", "position": 2},
        ],
    )
    session.add(asset)
    await session.commit()

    paths = await media_service.generate_media(session, asset)

    assert len(paths) == 3
    prompts = [call["prompt"] for call in fake.calls]
    # Each brief lands in its own call...
    for brief, prompt in zip(["shot A", "shot B", "shot C"], prompts, strict=True):
        assert f"SCENE: {brief}" in prompt
    # ...and the scaffold adds a carousel series marker.
    assert "part 1 of 3" in prompts[0]
    assert "part 3 of 3" in prompts[2]
    assert asset.media_files == paths
