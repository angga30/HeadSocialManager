"""Deterministic post-processing for generated images (M3 crop/pad, M5 logo overlay).

These run after the provider returns an image, so the result is guaranteed regardless of
what the provider does with `size`: providers that ignore it get a deterministic cover-crop
to the channel's target size, and brands with a logo get a composited overlay (logos are
never AI-generated — they always break).
"""

from __future__ import annotations

import logging
from pathlib import Path

from headofsocial.domain.schemas import LogoOverlay

logger = logging.getLogger(__name__)

# Logo width as a fraction of the image width when compositing (kept simple/consistent).
_LOGO_WIDTH_RATIO = 0.18


def parse_size(size: str) -> tuple[int, int] | None:
    """Parse "1080x1350" -> (1080, 1350); None for empty/malformed input."""
    if not size or "x" not in size:
        return None
    try:
        w, h = (int(part) for part in size.lower().split("x", 1))
    except ValueError:
        return None
    return (w, h) if w > 0 and h > 0 else None


def fit_to_size(path: Path, size: str) -> Path:
    """Deterministically cover-crop an image to `size` (no distortion). No-op if it matches."""
    target = parse_size(size)
    if target is None:
        return path
    from PIL import Image

    with Image.open(path) as raw:
        image = raw.convert("RGBA")
    if image.size == target:
        return path

    tw, th = target
    iw, ih = image.size
    scale = max(tw / iw, th / ih)
    new_w, new_h = max(tw, round(iw * scale)), max(th, round(ih * scale))
    resized = image.resize((new_w, new_h), Image.LANCZOS)
    left, top = (new_w - tw) // 2, (new_h - th) // 2
    cropped = resized.crop((left, top, left + tw, top + th))
    cropped.save(path)
    return path


def overlay_logo(path: Path, logo_path: Path, overlay: LogoOverlay | dict | None) -> Path:
    """Composite a brand logo onto an image at the configured corner (M5). No-op without a logo."""
    if overlay is None:
        return path
    config = overlay if isinstance(overlay, LogoOverlay) else LogoOverlay(**overlay)
    logo_file = Path(logo_path)
    if not logo_file.is_file():
        logger.warning("Logo file missing, skipping overlay: %s", logo_file)
        return path

    from PIL import Image

    with Image.open(path) as raw:
        base = raw.convert("RGBA")
    with Image.open(logo_file) as raw_logo:
        logo = raw_logo.convert("RGBA")

    target_w = max(1, int(base.width * _LOGO_WIDTH_RATIO))
    ratio = target_w / logo.width
    logo = logo.resize((target_w, max(1, round(logo.height * ratio))), Image.LANCZOS)
    if config.opacity < 1.0:
        alpha = logo.getchannel("A").point(lambda value: int(value * config.opacity))
        logo.putalpha(alpha)

    margin = config.margin
    positions = {
        "top-left": (margin, margin),
        "top-right": (base.width - logo.width - margin, margin),
        "bottom-left": (margin, base.height - logo.height - margin),
        "bottom-right": (
            base.width - logo.width - margin,
            base.height - logo.height - margin,
        ),
    }
    x, y = positions[config.position]
    base.paste(logo, (x, y), logo)
    base.convert("RGB").save(path)
    return path
