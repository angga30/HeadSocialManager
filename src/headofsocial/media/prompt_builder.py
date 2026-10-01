"""Centralised, deterministic media prompt scaffold (M2).

Consistency rule: **the code owns style; the LLM only fills the creative slot.** Every
prompt for a brand therefore shares an identical STYLE prefix, produced from the brand's
locked `visual_style` — not re-invented by the model on each post.

Layers (docs/agent-architecture-plan.md §4):
  STYLE PREFIX  <- brand.visual_style, verbatim, identical on every post
  FORMAT        <- aspect ratio + composition for the target channel
  SCENE         <- the LLM's creative brief (the only free-form part)
  AVOID         <- negative constraints from the visual style
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from headofsocial.channels.styles import ChannelStyle
from headofsocial.domain.schemas import VisualStyle

if TYPE_CHECKING:
    from headofsocial.domain.models import Brand


def _as_style(visual_style: VisualStyle | dict | None) -> VisualStyle | None:
    if visual_style is None:
        return None
    if isinstance(visual_style, VisualStyle):
        return visual_style
    try:
        return VisualStyle(**visual_style)
    except Exception:
        # A malformed style must never break generation; fall back to the generic prefix.
        return None


def style_prefix(visual_style: VisualStyle | dict | None) -> str:
    """Locked, verbatim style header — identical for every post of a brand."""
    style = _as_style(visual_style)
    if style is None:
        return "BRAND VISUAL STYLE (locked): keep one consistent look across every post."
    lines = ["BRAND VISUAL STYLE (locked - follow exactly, identical on every post):"]
    if style.palette:
        lines.append(f"- Palette: {', '.join(style.palette)}")
    if style.style_keywords:
        lines.append(f"- Style keywords: {', '.join(style.style_keywords)}")
    if style.image_tone:
        lines.append(f"- Tone: {style.image_tone}")
    if style.render_style:
        lines.append(f"- Render style: {style.render_style}")
    if style.typography_hint:
        lines.append(f"- Typography: {style.typography_hint}")
    return "\n".join(lines)


def format_block(
    channel: ChannelStyle | None, part_index: int | None = None, part_total: int | None = None
) -> str:
    """Aspect ratio + composition for the channel, plus a carousel series marker."""
    lines = ["FORMAT:"]
    if channel is not None:
        lines.append(f"- Aspect ratio: {channel.image_aspect}")
        lines.append(f"- Composition: {channel.image_composition}")
    if part_total and part_total > 1:
        idx = (part_index or 0) + 1
        lines.append(
            f"- Series: part {idx} of {part_total} in ONE visual series - keep the same palette, "
            "lighting and framing so the set reads as a single carousel."
        )
    return "\n".join(lines)


def avoid_block(visual_style: VisualStyle | dict | None) -> str:
    style = _as_style(visual_style)
    if style is None or not style.avoid:
        return ""
    return "AVOID: " + ", ".join(style.avoid)


def _reference_block(reference_notes: list[str] | None) -> str:
    notes = [n for n in (reference_notes or []) if n]
    if not notes:
        return ""
    return "MATCH THESE REFERENCES: " + " | ".join(notes)


def _assemble(
    prefix: str,
    fmt: str,
    scene_label: str,
    creative_brief: str,
    avoid: str,
    references: str,
) -> str:
    parts = [prefix, fmt, f"{scene_label}: {creative_brief.strip()}"]
    if avoid:
        parts.append(avoid)
    if references:
        parts.append(references)
    return "\n\n".join(part for part in parts if part)


def build_image_prompt(
    brand: Brand,
    channel_style: ChannelStyle | None,
    creative_brief: str,
    *,
    part_index: int | None = None,
    part_total: int | None = None,
    reference_notes: list[str] | None = None,
) -> str:
    """Assemble the final image prompt from the locked style + channel format + LLM brief."""
    visual: Any = getattr(brand, "visual_style", None)
    return _assemble(
        style_prefix(visual),
        format_block(channel_style, part_index, part_total),
        "SCENE",
        creative_brief,
        avoid_block(visual),
        _reference_block(reference_notes),
    )


def build_video_prompt(
    brand: Brand,
    channel_style: ChannelStyle | None,
    creative_brief: str,
    *,
    part_index: int | None = None,
    part_total: int | None = None,
    reference_notes: list[str] | None = None,
) -> str:
    """Same scaffold as images, labelled for motion so the brief describes movement."""
    visual: Any = getattr(brand, "visual_style", None)
    return _assemble(
        style_prefix(visual),
        format_block(channel_style, part_index, part_total),
        "SCENE (video motion)",
        creative_brief,
        avoid_block(visual),
        _reference_block(reference_notes),
    )
