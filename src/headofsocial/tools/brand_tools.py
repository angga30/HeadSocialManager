"""Tools for brand CRUD + applying positioning recommendations."""

from google.adk.tools.tool_context import ToolContext

from headofsocial.domain.enums import BrandType
from headofsocial.domain.models import Brand
from headofsocial.domain.schemas import PositioningRecommendation
from headofsocial.services import brand_service
from headofsocial.tools._deps import brand_asset_to_dict, brand_to_dict, run


async def create_brand(
    name: str,
    type_: str,
    business_description: str = "",
    industry: str = "",
    website: str = "",
    language: str = "id",
) -> dict:
    """Create a new brand to manage. type_ is personal, business, or product.

    Args:
        name: Brand name.
        type_: personal | business | product.
        business_description: What the brand does, sells, or stands for.
        industry: Sector, e.g. F&B, SaaS, personal coaching.
        website: Optional website URL.
        language: Default content language code, e.g. id or en.
    """
    async def _fn(session):
        brand = await brand_service.create_brand(
            session, name, BrandType(type_), business_description or None, industry or None,
            website or None, language,
        )
        return brand_to_dict(brand)

    return await run(_fn)


async def get_brand(brand_id: int) -> dict:
    """Fetch a brand's full profile, including positioning, pillars, voice, and audience."""
    async def _fn(session):
        brand = await session.get(Brand, brand_id)
        if brand is None:
            return {"ok": False, "error": f"Brand {brand_id} not found"}
        return brand_to_dict(brand)

    return await run(_fn)


async def list_brands() -> dict:
    """List all brands managed by the system with a compact summary."""
    async def _fn(session):
        brands = await brand_service.list_brands(session)
        return {
            "ok": True,
            "brands": [
                {"id": b.id, "name": b.name, "type": str(b.type), "language": b.language,
                 "has_positioning": bool(b.positioning_statement)}
                for b in brands
            ],
        }

    return await run(_fn)


async def apply_positioning(brand_id: int, positioning: dict) -> dict:
    """Save a full positioning recommendation to a brand.

    Args:
        brand_id: Target brand.
        positioning: dict with positioning_statement, target_audience (list),
            differentiators (list), voice_tone (str), content_pillars
            (list of {name, angle, example_angles}), and optional visual_style
            {palette, style_keywords, image_tone, typography_hint, avoid, render_style,
            logo_overlay}.
    """
    rec = PositioningRecommendation(**positioning)
    async def _fn(session):
        brand = await brand_service.apply_recommendation(session, brand_id, rec)
        return brand_to_dict(brand)

    return await run(_fn)


async def upload_brand_asset(
    brand_id: int,
    kind: str,
    file_path: str,
    label: str = "",
    is_primary: bool = False,
) -> dict:
    """Register a real brand asset (photo/logo/product) so media stays on-brand (M1).

    Args:
        brand_id: Target brand.
        kind: face_photo | logo | logo_dark | product_photo | reference_style.
        file_path: Path to an existing image file (png/jpg/jpeg/webp) on disk.
        label: Short description (used as textual reference for providers without
            reference-image support, e.g. "wanita 30-an, rambut pendek, senyum ramah").
        is_primary: Mark as the primary asset of its kind.
    """
    async def _fn(session):
        asset = await brand_service.register_brand_asset(
            session, brand_id, kind, file_path, label or None, is_primary
        )
        return {"ok": True, "asset": brand_asset_to_dict(asset)}

    return await run(_fn)


async def list_brand_assets(brand_id: int) -> dict:
    """List a brand's uploaded visual assets (photos, logo, product shots, reference style)."""
    async def _fn(session):
        assets = await brand_service.list_brand_assets(session, brand_id)
        return {"ok": True, "assets": [brand_asset_to_dict(a) for a in assets]}

    return await run(_fn)


async def set_visual_style(brand_id: int, visual_style: dict) -> dict:
    """Persist the brand's locked visual identity, grounding every media prompt (M1).

    Args:
        brand_id: Target brand.
        visual_style: dict with palette (2-4 hex), style_keywords (list), image_tone,
            typography_hint, avoid (list), render_style, and optional logo_overlay
            {position, opacity, margin}.
    """
    async def _fn(session):
        brand = await brand_service.set_visual_style(session, brand_id, visual_style)
        return brand_to_dict(brand)

    return await run(_fn)


def set_active_brand(brand_id: int, tool_context: ToolContext) -> dict:
    """Remember the brand the user is currently working on for the rest of the session (S3).

    Call this whenever the user picks or switches the active brand, so sub-agents can read
    it from session state instead of re-asking.

    Args:
        brand_id: The brand id to mark as active.
    """
    tool_context.state["active_brand_id"] = brand_id
    return {"ok": True, "active_brand_id": brand_id}