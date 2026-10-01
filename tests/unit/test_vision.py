"""Vision-based reference analysis (M4) — structured fidelity output + graceful failure."""

import litellm

from headofsocial.media import vision


class _Msg:
    content = '{"identity": {"eyes": "almond"}, "fidelity_note": "almond eyes, sharp jaw"}'


class _Choice:
    message = _Msg()


class _Resp:
    choices = [_Choice()]


async def _fake_acompletion(**kwargs):
    return _Resp()


async def test_analyze_face_returns_structured(monkeypatch, tmp_path):
    monkeypatch.setattr(litellm, "acompletion", _fake_acompletion)
    image = tmp_path / "face.png"
    image.write_bytes(b"\x89PNG fake")

    result = await vision.analyze_reference_image(image, "face_photo")

    assert result["ok"] is True
    assert result["subject"] == "person"
    assert result["identity"] == {"eyes": "almond"}
    assert "almond eyes" in result["fidelity_note"]


async def test_analyze_logo_subject(monkeypatch, tmp_path):
    monkeypatch.setattr(litellm, "acompletion", _fake_acompletion)
    image = tmp_path / "logo.png"
    image.write_bytes(b"x")

    result = await vision.analyze_reference_image(image, "logo")

    assert result["subject"] == "logo"


async def test_analyze_failure_is_graceful(monkeypatch, tmp_path):
    async def _raise(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(litellm, "acompletion", _raise)
    image = tmp_path / "x.png"
    image.write_bytes(b"x")

    result = await vision.analyze_reference_image(image, "face_photo")

    assert result["ok"] is False
    assert "boom" in result["error"]


def test_subject_for_kind():
    assert vision.subject_for_kind("face_photo") == "person"
    assert vision.subject_for_kind("logo") == "logo"
    assert vision.subject_for_kind("logo_dark") == "logo"
    assert vision.subject_for_kind("product_photo") == "product"
    assert vision.subject_for_kind("reference_style") == "style"
