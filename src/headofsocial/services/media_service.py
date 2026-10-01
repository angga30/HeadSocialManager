"""Media generation with hard budget enforcement (max 5 images / 2 videos per asset).

The pipeline (M2-M5):
  1. build the final prompt in code from the brand's locked style + channel format + the
     LLM's creative brief (never let the model invent style);
  2. resolve reference images from real brand assets (passed to the provider, or described
     textually when the provider can't take images);
  3. generate, then deterministically cover-crop to the channel's aspect/size;
  4. composite the brand logo (M5) so it always appears correctly.
"""

import asyncio
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from headofsocial.channels.styles import ChannelStyle, get_style
from headofsocial.domain.enums import AssetType, BrandAssetKind, BrandType, ContentDepth, MediaType
from headofsocial.domain.models import Asset, Brand, BrandAsset, Post
from headofsocial.domain.schemas import LogoOverlay, MediaSpecItem
from headofsocial.llm.media_providers import (
    MediaNotSupportedError,
    budget,
    get_media_provider,
    validate_media_spec,
)
from headofsocial.media import vision
from headofsocial.media.postprocess import fit_to_size, overlay_logo
from headofsocial.media.prompt_builder import build_image_prompt, build_video_prompt
from headofsocial.storage import repos

_LOGO_KINDS = (BrandAssetKind.LOGO, BrandAssetKind.LOGO_DARK)


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


async def _channel_for_asset(session: AsyncSession, asset: Asset) -> ChannelStyle | None:
    """Find the channel a post using this asset belongs to (drives format + size, M3)."""
    result = await session.execute(
        select(Post).where(Post.asset_id == asset.id).options(selectinload(Post.channel)).limit(1)
    )
    post = result.scalars().first()
    if post is None or post.channel is None:
        return None
    return get_style(str(post.channel.platform), post.channel.style_overrides)


def _target_size(channel: ChannelStyle | None) -> str:
    if channel is not None and channel.image_size:
        return channel.image_size
    return ""  # provider default; fit_to_size is a no-op without a size


def _references_for(
    brand: Brand, brand_assets: list[BrandAsset], creative_brief: str
) -> list[BrandAsset]:
    """Collect ALL the brand's reference assets relevant to its type (primary first) (M4).

    Every matching reference photo is sent to the provider so the generated image has the
    fullest possible grounding (multiple face angles, product shots, style refs). Logo is
    excluded here — it is composited deterministically, never AI-generated.
    """
    brand_type = str(brand.type)
    if brand_type == BrandType.PERSONAL:
        faces = [a for a in brand_assets if str(a.kind) == BrandAssetKind.FACE_PHOTO]
        return sorted(faces, key=lambda a: not a.is_primary)
    if brand_type == BrandType.BUSINESS:
        refs = [a for a in brand_assets if str(a.kind) == BrandAssetKind.REFERENCE_STYLE]
        return sorted(refs, key=lambda a: not a.is_primary)
    if brand_type == BrandType.PRODUCT:
        products = [a for a in brand_assets if str(a.kind) == BrandAssetKind.PRODUCT_PHOTO]
        return sorted(products, key=lambda a: not a.is_primary)
    return []


def _logo_asset(brand_assets: list[BrandAsset]) -> BrandAsset | None:
    logos = [a for a in brand_assets if str(a.kind) in {k.value for k in _LOGO_KINDS}]
    if not logos:
        return None
    primary = [a for a in logos if a.is_primary]
    return (primary or logos)[0]


def _logo_config(brand: Brand | None) -> LogoOverlay | None:
    if brand is None or not isinstance(brand.visual_style, dict):
        return None
    raw = brand.visual_style.get("logo_overlay")
    if not raw:
        return None
    if isinstance(raw, LogoOverlay):
        return raw
    try:
        return LogoOverlay(**raw)
    except Exception:
        return None


def _resolve_refs(
    brand: Brand | None,
    brand_assets: list[BrandAsset],
    creative_brief: str,
    supports_refs: bool,
) -> tuple[list[str] | None, list[Path] | None]:
    """Return (textual notes, reference paths) — which one is used depends on the provider (M4)."""
    if brand is None:
        return None, None
    selected = _references_for(brand, brand_assets, creative_brief)
    if not selected:
        return None, None
    if supports_refs:
        return None, [Path(a.file_path) for a in selected]
    notes = [a.label for a in selected if a.label]
    return (notes or None), None


@dataclass
class _GenContext:
    provider: object
    brand: Brand | None
    channel_style: ChannelStyle | None
    brand_assets: list[BrandAsset]
    logo: BrandAsset | None
    logo_config: LogoOverlay | None
    size: str
    supports_refs: bool


async def _load_context(session: AsyncSession, asset: Asset, provider: object) -> _GenContext:
    brand = await session.get(Brand, asset.brand_id)
    channel_style = await _channel_for_asset(session, asset)
    brand_assets = await repos.list_brand_assets(session, asset.brand_id)
    return _GenContext(
        provider=provider,
        brand=brand,
        channel_style=channel_style,
        brand_assets=brand_assets,
        logo=_logo_asset(brand_assets),
        logo_config=_logo_config(brand),
        size=_target_size(channel_style),
        supports_refs=bool(getattr(provider, "supports_reference_images", False)),
    )


async def _generate_item(
    ctx: _GenContext,
    item: MediaSpecItem,
    *,
    part_index: int,
    part_total: int,
    fidelity_notes: str = "",
    fidelity_subject: str = "style",
) -> Path:
    """Generate one spec item (image or video) and return its path."""
    notes, refs = _resolve_refs(ctx.brand, ctx.brand_assets, item.creative_brief, ctx.supports_refs)
    if item.media_type == MediaType.IMAGE:
        prompt = build_image_prompt(
            ctx.brand,
            ctx.channel_style,
            item.creative_brief,
            part_index=part_index,
            part_total=part_total,
            reference_notes=notes,
            fidelity_notes=fidelity_notes,
            fidelity_subject=fidelity_subject,
        )
        produced = await ctx.provider.generate_image(prompt, size=ctx.size, reference_images=refs)
        produced = fit_to_size(produced, ctx.size)
        if ctx.logo is not None and ctx.logo_config is not None:
            produced = overlay_logo(produced, Path(ctx.logo.file_path), ctx.logo_config)
        return produced
    prompt = build_video_prompt(
        ctx.brand,
        ctx.channel_style,
        item.creative_brief,
        part_index=part_index,
        part_total=part_total,
        reference_notes=notes,
        fidelity_notes=fidelity_notes,
        fidelity_subject=fidelity_subject,
    )
    return await ctx.provider.generate_video(prompt, reference_images=refs)


async def generate_media(session: AsyncSession, asset: Asset) -> list[str]:
    """Generate the media in an asset's media_spec, enforcing the budget. Returns paths.

    Each spec item carries its own creative brief, so a carousel produces distinct images;
    the visual style is applied centrally, so every image shares the brand's look.
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

    ctx = await _load_context(session, asset, provider)
    ordered = sorted(items, key=lambda i: i.position)
    image_items = [i for i in ordered if i.media_type == MediaType.IMAGE]
    video_items = [i for i in ordered if i.media_type == MediaType.VIDEO]
    paths: list[str] = []

    for index, item in enumerate(image_items):
        paths.append(str(await _generate_item(ctx, item, part_index=index, part_total=len(image_items))))
    for index, item in enumerate(video_items):
        paths.append(str(await _generate_item(ctx, item, part_index=index, part_total=len(video_items))))

    asset.media_files = paths
    await session.commit()
    return paths


_media_files_lock = asyncio.Lock()


async def record_media_file(session: AsyncSession, asset_id: int, position: int, path: str) -> None:
    """Race-free per-position write: parallel sub-agents each fill one slot in media_files."""
    async with _media_files_lock:
        asset = await session.get(Asset, asset_id, populate_existing=True)
        files = list(asset.media_files or [])
        while len(files) <= position:
            files.append(None)
        files[position] = path
        asset.media_files = files
        await session.commit()


async def generate_media_item(
    session: AsyncSession,
    asset: Asset,
    position: int,
    *,
    fidelity_notes: str = "",
    fidelity_subject: str = "style",
) -> str:
    """Generate a single media item at `position` and record its path on the asset.

    Used by the Media Generation Agent: one call per media item, run in parallel. The
    fidelity notes come from a prior vision analysis of the reference photo.
    """
    spec = asset.media_spec or []
    items = [MediaSpecItem(**s) if isinstance(s, dict) else s for s in spec]
    check_media_budget(items)
    ordered = sorted(items, key=lambda i: i.position)
    item = next((i for i in ordered if i.position == position), None)
    if item is None:
        raise ValueError(f"Asset {asset.id} tidak punya media item di posisi {position}")

    provider = get_media_provider()
    if item.media_type == MediaType.VIDEO and not getattr(provider, "supports_video", False):
        raise MediaNotSupportedError(
            "Provider media aktif tidak mendukung video (fase 3). Pakai depth "
            "text/visual/carousel, atau set HEADSOF_MEDIA_PROVIDER=mock untuk placeholder video."
        )

    ctx = await _load_context(session, asset, provider)
    same_type = [i for i in ordered if i.media_type == item.media_type]
    part_index = [i.position for i in same_type].index(position)
    part_total = len(same_type)
    path = await _generate_item(
        ctx,
        item,
        part_index=part_index,
        part_total=part_total,
        fidelity_notes=fidelity_notes,
        fidelity_subject=fidelity_subject,
    )
    await record_media_file(session, asset.id, position, str(path))
    return str(path)


async def analyze_reference(session: AsyncSession, asset_id: int) -> dict:
    """Vision-analyze a brand reference asset and return a structured fidelity dict."""
    asset = await session.get(BrandAsset, asset_id)
    if asset is None:
        return {"ok": False, "error": f"BrandAsset {asset_id} not found"}
    return await vision.analyze_reference_image(Path(asset.file_path), str(asset.kind))


def budget_summary() -> str:
    b = budget()
    return f"Media budget: max {b['max_images']} images and {b['max_videos']} videos per asset."
