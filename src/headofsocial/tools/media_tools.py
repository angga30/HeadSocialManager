"""Media tools — generate image/video with enforced budget (max 5 images, 2 videos per asset)."""

from headofsocial.domain.enums import ContentDepth, MediaType
from headofsocial.domain.models import Asset, Post
from headofsocial.domain.schemas import MediaSpecItem
from headofsocial.services import media_service
from headofsocial.tools._deps import asset_to_dict, load_post, post_to_dict, run


def _as_list(value: list | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


async def create_asset(
    brand_id: int,
    body: str,
    depth: str = "text",
    image_prompts: list[str] | None = None,
    video_prompts: list[str] | None = None,
) -> dict:
    """Create a content asset: channel copy plus prompts for the media to generate.

    Simple string lists keep model-generated tool arguments valid JSON.

    Args:
        brand_id: Target brand.
        body: Channel-native copy text (the caption/post body).
        depth: text | visual | carousel | motion | series | rich.
        image_prompts: One prompt per image (max 5). Empty for text-only.
        video_prompts: One prompt per video (max 2). Usually empty (video is fase 3).
    """
    if depth not in ContentDepth._value2member_map_:
        return {"ok": False, "error": f"depth must be one of {[d.value for d in ContentDepth]}"}
    images, videos = _as_list(image_prompts), _as_list(video_prompts)
    try:
        depth_enum = ContentDepth(depth)
        items = [
            MediaSpecItem(media_type=MediaType.IMAGE, prompt=p, position=i)
            for i, p in enumerate(images)
        ] + [
            MediaSpecItem(media_type=MediaType.VIDEO, prompt=p, position=len(images) + i)
            for i, p in enumerate(videos)
        ]
        media_service.check_media_budget(items)  # raises BudgetExceededError
    except media_service.BudgetExceededError as exc:
        return {"ok": False, "error": str(exc)}
    except (TypeError, ValueError) as exc:
        return {"ok": False, "error": f"Invalid media prompts: {exc}"}

    asset_type = media_service.content_type_for_depth(depth_enum)
    async def _fn(session):
        asset = Asset(
            brand_id=brand_id,
            type=asset_type,
            depth=depth_enum,
            body=body or None,
            media_spec=[i.model_dump() for i in items] if items else None,
        )
        session.add(asset)
        await session.flush()  # run() commits; avoid a double commit
        return asset_to_dict(asset)
    return await run(_fn)


async def attach_asset(post_id: int, asset_id: int) -> dict:
    """Attach a content asset to a post slot (the missing link that makes publishing work).

    Args:
        post_id: The post slot to fill.
        asset_id: The asset (copy/media) to attach.
    """
    async def _fn(session):
        post = await session.get(Post, post_id)
        if post is None:
            return {"ok": False, "error": f"Post {post_id} not found"}
        asset = await session.get(Asset, asset_id)
        if asset is None:
            return {"ok": False, "error": f"Asset {asset_id} not found"}
        if post.brand_id != asset.brand_id:
            return {
                "ok": False,
                "error": f"Brand mismatch: post belongs to brand {post.brand_id}, asset to {asset.brand_id}",
            }
        post.asset_id = asset.id
        await session.flush()
        loaded = await load_post(session, post_id)
        return {"ok": True, "post": post_to_dict(loaded) if loaded else {"id": post_id}}
    return await run(_fn)


async def generate_media(asset_id: int) -> dict:
    """Generate the media planned in an asset's media_spec. Enforces the media budget.

    Args:
        asset_id: The asset whose media_spec should be generated.
    """
    async def _fn(session):
        asset = await session.get(Asset, asset_id)
        if asset is None:
            return {"ok": False, "error": f"Asset {asset_id} not found"}
        if not (asset.media_spec or []):
            return {"ok": False, "error": "Asset has no media_spec to generate."}
        try:
            paths = await media_service.generate_media(session, asset)
        except media_service.BudgetExceededError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "asset_id": asset.id, "media_files": paths}
    return await run(_fn)


async def check_media_budget(media_spec: list) -> dict:
    """Validate a media_spec against hard caps before generating. Returns violations or ok.

    Args:
        media_spec: List of {media_type: image|video, prompt, position}.
    """
    try:
        items = [MediaSpecItem(**s) for s in media_spec]
        media_service.check_media_budget(items)
        return {"ok": True, "message": "Within budget."}
    except media_service.BudgetExceededError as exc:
        return {"ok": False, "error": str(exc)}