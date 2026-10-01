"""M2 — the central prompt scaffold: locked style prefix + channel format + brief + avoid."""

from headofsocial.channels.styles import get_style
from headofsocial.domain.enums import Platform
from headofsocial.media.prompt_builder import build_image_prompt, style_prefix

_STYLE = {
    "palette": ["#1A1A2E", "#E94560"],
    "style_keywords": ["minimalist", "warm natural light"],
    "image_tone": "bright",
    "render_style": "photography",
    "avoid": ["neon", "stock-photo look"],
}


class _Brand:
    visual_style = _STYLE


def test_prefix_identical_across_different_briefs():
    style = get_style(Platform.INSTAGRAM)
    p1 = build_image_prompt(_Brand(), style, "brief one")
    p2 = build_image_prompt(_Brand(), style, "brief two")
    prefix = style_prefix(_STYLE)
    assert p1.startswith(prefix)
    assert p2.startswith(prefix)


def test_format_and_avoid_rendered():
    style = get_style(Platform.LINKEDIN)
    prompt = build_image_prompt(_Brand(), style, "brief")
    assert "1.91:1" in prompt
    assert "AVOID: neon, stock-photo look" in prompt


def test_carousel_series_marker():
    style = get_style(Platform.INSTAGRAM)
    prompt = build_image_prompt(_Brand(), style, "x", part_index=1, part_total=3)
    assert "part 2 of 3" in prompt


def test_no_visual_style_falls_back_to_generic_prefix():
    class _Plain:
        visual_style = None

    prompt = build_image_prompt(_Plain(), None, "x")
    assert "BRAND VISUAL STYLE" in prompt
