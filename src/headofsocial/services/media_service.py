"""Media generation with hard budget enforcement (max 5 images / 2 videos per asset)."""

from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession

from headofsocial.domain.enums import AssetType, ContentDepth, MediaType
from headofsocial.domain.models import Asset
from headofsocial.domain.schemas import MediaSpecItem
from headofsocial.llm.media_providers import (
    MediaNotSupportedError,
    budget,
    get_media_provider,
    validate_media_spec,
)


class BudgetExceededError(ValueError):
    """Raised when a media_spec exceeds the hard caps."""


def content_type_for_depth(depth: ContentDepth) -> AssetType:
    mapping = {
        ContentDepth.TEXT: AssetType.TEXT,
        ContentDepth.VISUAL: AssetType.IMAGE,
        ContentDepth.CAROUSEL: AssetType.IMAGE,
        ContentDepth.MOTION: AssetType.VIDEO,
        ContentDepth.SERIES: AssetType.VIDEO,
        ContentDepth.RICH: AssetType.MIXED,
    }
    return mapping[depth]


def counts_for_depth(depth: ContentDepth) -> tuple[int, int]:
    """Expected (images, videos) for a depth — used to validate specs."""
    if depth == ContentDepth.TEXT:
        return (0, 0)
    if depth == ContentDepth.VISUAL:
        return (1, 0)
    if depth == ContentDepth.CAROUSEL:
        return (5, 0)  # 2-5 acceptable; enforce ceiling
    if depth == ContentDepth.MOTION:
        return (0, 1)
    if depth == ContentDepth.SERIES:
        return (0, 2)
    return (5, 2)  # RICH


def check_media_budget(media_spec: list[MediaSpecItem]) -> None:
    """Validate a full media spec against hard caps; raise BudgetExceededError."""
    counts: Counter = Counter()
    for item in media_spec:
        counts[item.media_type] += 1
    for media_type in (MediaType.IMAGE, MediaType.VIDEO):
        violations = validate_media_spec(media_type, counts[media_type])
        if violations:
            raise BudgetExceededError("; ".join(violations))


async def generate_media(session: AsyncSession, asset: Asset) -> list[str]:
    """Generate the media in an asset's media_spec, enforcing the budget. Returns paths.

    Each spec item carries its own prompt, so a carousel produces distinct images
    (not the first prompt repeated n times).
    """
    spec = asset.media_spec or []
    items = [MediaSpecItem(**s) if isinstance(s, dict) else s for s in spec]
    check_media_budget(items)

    provider = get_media_provider()
    # Validate capabilities up-front so we don't generate half the media then fail.
    videos = [i for i in items if i.media_type == MediaType.VIDEO]
    if videos and not getattr(provider, "supports_video", False):
        raise MediaNotSupportedError(
            "Provider media aktif tidak mendukung video (fase 3). Pakai depth "
            "text/visual/carousel, atau set HEADSOF_MEDIA_PROVIDER=mock untuk placeholder video."
        )

    ordered = sorted(items, key=lambda i: i.position)
    paths: list[str] = []
    for item in ordered:
        if item.media_type == MediaType.IMAGE:
            paths.extend(str(p) for p in await provider.generate_image(item.prompt, 1))
        elif item.media_type == MediaType.VIDEO:
            paths.extend(str(p) for p in await provider.generate_video(item.prompt, 1))

    asset.media_files = paths
    await session.commit()
    return paths


def budget_summary() -> str:
    b = budget()
    return f"Media budget: max {b['max_images']} images and {b['max_videos']} videos per asset."