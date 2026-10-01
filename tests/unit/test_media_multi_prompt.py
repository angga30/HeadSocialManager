"""A5 — generate_media uses each spec item's own prompt (distinct carousel images)."""

from pathlib import Path

from headofsocial.domain.enums import ContentDepth
from headofsocial.domain.models import Asset
from headofsocial.services import media_service


class _FakeProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    async def generate_image(self, prompt: str, n: int = 1) -> list[Path]:
        self.calls.append(("image", prompt, n))
        return [Path(f"/tmp/img_{len(self.calls)}.png")]

    async def generate_video(self, prompt: str, n: int = 1) -> list[Path]:
        self.calls.append(("video", prompt, n))
        return [Path(f"/tmp/vid_{len(self.calls)}.mp4")]


async def test_each_spec_item_uses_its_own_prompt(session, brand, monkeypatch):
    fake = _FakeProvider()
    monkeypatch.setattr(media_service, "get_media_provider", lambda: fake)

    asset = Asset(
        brand_id=brand.id,
        type="image",
        depth=ContentDepth.CAROUSEL,
        body="carousel",
        media_spec=[
            {"media_type": "image", "prompt": "shot A", "position": 0},
            {"media_type": "image", "prompt": "shot B", "position": 1},
            {"media_type": "image", "prompt": "shot C", "position": 2},
        ],
    )
    session.add(asset)
    await session.commit()

    paths = await media_service.generate_media(session, asset)

    assert len(paths) == 3
    prompts = [c[1] for c in fake.calls]
    assert prompts == ["shot A", "shot B", "shot C"]
    assert all(c[2] == 1 for c in fake.calls)  # one call per prompt
    assert asset.media_files == paths