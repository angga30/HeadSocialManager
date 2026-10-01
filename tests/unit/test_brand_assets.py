"""M1 — brand visual identity: asset upload/list/validation + visual_style persistence."""

from pathlib import Path

import pytest
from PIL import Image

from headofsocial.config import settings
from headofsocial.services import brand_service
from headofsocial.tools import brand_tools


def _png(path: Path, color=(0, 0, 0)) -> Path:
    Image.new("RGB", (4, 4), color).save(path)
    return path


async def test_register_list_and_validate(session, brand, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    source = _png(tmp_path / "face.png")
    asset = await brand_service.register_brand_asset(
        session, brand.id, "face_photo", source, label="me", is_primary=True
    )
    assert str(asset.kind) == "face_photo"
    assert Path(asset.file_path).is_file()
    assert asset.file_path != str(source)  # copied into data/brand_assets

    listed = await brand_service.list_brand_assets(session, brand.id)
    assert [a.id for a in listed] == [asset.id]


async def test_register_rejects_bad_kind_and_type(session, brand, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    good = _png(tmp_path / "x.png")
    with pytest.raises(ValueError):
        await brand_service.register_brand_asset(session, brand.id, "poster", good)
    bad = tmp_path / "x.txt"
    bad.write_text("nope")
    with pytest.raises(ValueError):
        await brand_service.register_brand_asset(session, brand.id, "logo", bad)


async def test_brand_tools_upload_and_list(session, brand, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    source = _png(tmp_path / "logo.png")
    uploaded = await brand_tools.upload_brand_asset(
        brand.id, "logo", str(source), label="logo utama", is_primary=True
    )
    assert uploaded["ok"] and uploaded["asset"]["kind"] == "logo"

    listing = await brand_tools.list_brand_assets(brand.id)
    assert len(listing["assets"]) == 1
    assert listing["assets"][0]["url"].startswith("/brand-assets/")


async def test_apply_positioning_saves_visual_style(session, brand):
    result = await brand_tools.apply_positioning(
        brand.id,
        {
            "positioning_statement": "x",
            "target_audience": ["a"],
            "differentiators": ["b"],
            "voice_tone": "c",
            "content_pillars": [{"name": "p"}],
            "visual_style": {
                "palette": ["#112233", "#abcdef"],
                "style_keywords": ["minimal"],
                "render_style": "photography",
            },
        },
    )
    assert result["visual_style"]["palette"] == ["#112233", "#abcdef"]
    fetched = await brand_tools.get_brand(brand.id)
    assert fetched["visual_style"]["render_style"] == "photography"


async def test_set_visual_style_rejects_bad_palette(session, brand):
    result = await brand_tools.set_visual_style(brand.id, {"palette": ["not-a-color"]})
    assert result["ok"] is False
