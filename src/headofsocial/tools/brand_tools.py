"""Tools for brand CRUD + applying positioning recommendations."""

from headofsocial.domain.enums import BrandType
from headofsocial.domain.models import Brand
from headofsocial.domain.schemas import PositioningRecommendation
from headofsocial.services import brand_service
from headofsocial.tools._deps import brand_to_dict, run


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
            (list of {name, angle, example_angles}).
    """
    rec = PositioningRecommendation(**positioning)
    async def _fn(session):
        brand = await brand_service.apply_recommendation(session, brand_id, rec)
        return brand_to_dict(brand)

    return await run(_fn)