"""Dashboard REST API — wraps the services layer for the web UI."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from headofsocial.domain.enums import BrandType, Platform
from headofsocial.domain.schemas import ChannelInput, MonthlyPlan, WeeklyTheme
from headofsocial.services import (
    analytics_service,
    brand_service,
    media_service,
    planning_service,
    publishing_service,
)
from headofsocial.storage.db import SessionFactory
from headofsocial.tools._deps import (
    asset_to_dict,
    brand_to_dict,
    channel_to_dict,
    ensure_db,
    media_url,
    plan_to_dict,
    post_to_dict,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# --- Request bodies ---
class BrandCreate(BaseModel):
    name: str
    type_: str = Field("business")
    description: str = ""
    industry: str = ""
    website: str = ""
    language: str = "id"


class ChannelCreate(BaseModel):
    platform: Platform
    handle: str
    language: str | None = None
    style_overrides: dict | None = None


class PlanCreate(BaseModel):
    period: str
    theme: str = ""
    weekly_themes: list[WeeklyTheme] = []
    cadence: dict[str, int] = {}
    content_mix: dict = {}
    key_dates: list[dict] = []


class AssetCreate(BaseModel):
    brand_id: int
    body: str = ""
    depth: str = "text"
    media_spec: list[dict] = []


async def _brand_or_404(session, brand_id):
    from headofsocial.domain.models import Brand

    brand = await session.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail=f"Brand {brand_id} not found")
    return brand


# --- Brands ---
@router.get("/brands")
async def list_brands():
    await ensure_db()
    async with SessionFactory() as session:
        brands = await brand_service.list_brands(session)
        return [brand_to_dict(b) for b in brands]


@router.post("/brands")
async def create_brand(body: BrandCreate):
    await ensure_db()
    async with SessionFactory() as session:
        brand = await brand_service.create_brand(
            session,
            body.name,
            BrandType(body.type_),
            body.description or None,
            body.industry or None,
            body.website or None,
            body.language,
        )
        return brand_to_dict(brand)


@router.get("/brands/{brand_id}")
async def get_brand(brand_id: int):
    await ensure_db()
    async with SessionFactory() as session:
        await _brand_or_404(session, brand_id)
        from headofsocial.domain.models import Brand

        brand = await session.get(Brand, brand_id)
        return brand_to_dict(brand)


# --- Channels ---
@router.get("/brands/{brand_id}/channels")
async def list_channels(brand_id: int):
    await ensure_db()
    async with SessionFactory() as session:
        await _brand_or_404(session, brand_id)
        channels = await brand_service.list_channels(session, brand_id)
        return [channel_to_dict(c) for c in channels]


@router.post("/brands/{brand_id}/channels")
async def create_channel(brand_id: int, body: ChannelCreate):
    await ensure_db()
    async with SessionFactory() as session:
        await _brand_or_404(session, brand_id)
        channel = await brand_service.create_channel(session, brand_id, ChannelInput(
            platform=body.platform, handle=body.handle, language=body.language,
            style_overrides=body.style_overrides,
        ))
        return channel_to_dict(channel)


# --- Plans ---
@router.get("/brands/{brand_id}/plans")
async def list_plans(brand_id: int):
    await ensure_db()
    async with SessionFactory() as session:
        await _brand_or_404(session, brand_id)
        from headofsocial.storage import repos

        plans = await repos.list_plans(session, brand_id)
        return [plan_to_dict(p) for p in plans]


@router.post("/brands/{brand_id}/plans")
async def create_plan(brand_id: int, body: PlanCreate):
    await ensure_db()
    async with SessionFactory() as session:
        await _brand_or_404(session, brand_id)
        plan = MonthlyPlan(**body.model_dump())
        row = await planning_service.create_plan(session, brand_id, plan)
        return plan_to_dict(row)


@router.post("/plans/{plan_id}/fanout")
async def fan_out_plan(plan_id: int):
    await ensure_db()
    async with SessionFactory() as session:
        posts = await planning_service.fan_out_plan(session, plan_id)
        return [post_to_dict(p) for p in posts]


# --- Posts ---
@router.get("/brands/{brand_id}/posts")
async def list_posts(brand_id: int):
    await ensure_db()
    async with SessionFactory() as session:
        await _brand_or_404(session, brand_id)
        from headofsocial.storage import repos

        posts = await repos.list_posts(session, brand_id)
        return [post_to_dict(p) for p in posts]


@router.post("/posts/{post_id}/approve")
async def approve_post(post_id: int):
    await ensure_db()
    async with SessionFactory() as session:
        from headofsocial.domain.models import Post

        post = await session.get(Post, post_id)
        if post is None:
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
        post = await publishing_service.schedule_post(session, post)
        return post_to_dict(post)


@router.post("/posts/{post_id}/publish")
async def publish_post(post_id: int):
    await ensure_db()
    async with SessionFactory() as session:
        from headofsocial.domain.models import Post

        post = await session.get(Post, post_id)
        if post is None:
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
        post = await publishing_service.publish_post(session, post)
        return post_to_dict(post)


@router.post("/publish-due")
async def publish_due():
    await ensure_db()
    async with SessionFactory() as session:
        published = await publishing_service.publish_due(session)
        return {"published": len(published)}


# --- Insights ---
@router.get("/brands/{brand_id}/insights")
async def get_insights(brand_id: int, days: int = 90):
    await ensure_db()
    async with SessionFactory() as session:
        await _brand_or_404(session, brand_id)
        insights = await analytics_service.get_engagement_insights(session, brand_id, days)
        return insights.model_dump()


@router.get("/brands/{brand_id}/history")
async def get_history(brand_id: int, days: int = 90):
    await ensure_db()
    async with SessionFactory() as session:
        await _brand_or_404(session, brand_id)
        history = await analytics_service.get_content_history(session, brand_id, days)
        return {"history": history, "count": len(history)}


# --- Assets / media ---
@router.get("/brands/{brand_id}/assets")
async def list_assets(brand_id: int):
    await ensure_db()
    async with SessionFactory() as session:
        await _brand_or_404(session, brand_id)
        from headofsocial.storage import repos

        assets = await repos.list_assets(session, brand_id)
        out = []
        for a in assets:
            data = asset_to_dict(a)
            data["media"] = [media_url(p) for p in (a.media_files or [])]
            out.append(data)
        return out


@router.post("/assets")
async def create_asset(body: AssetCreate):
    await ensure_db()
    async with SessionFactory() as session:
        from headofsocial.domain.enums import ContentDepth
        from headofsocial.domain.models import Asset
        from headofsocial.domain.schemas import MediaSpecItem

        if body.depth not in ContentDepth._value2member_map_:
            raise HTTPException(status_code=400, detail="invalid depth")
        depth = ContentDepth(body.depth)
        try:
            media_spec = [MediaSpecItem(**s) for s in body.media_spec]
            media_service.check_media_budget(media_spec)
        except media_service.BudgetExceededError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        asset_type = media_service.content_type_for_depth(depth)
        asset = Asset(
            brand_id=body.brand_id,
            type=asset_type,
            depth=depth,
            body=body.body or None,
            media_spec=[i.model_dump() for i in media_spec] if media_spec else None,
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)
        return asset_to_dict(asset)


@router.post("/assets/{asset_id}/generate")
async def generate_asset_media(asset_id: int):
    await ensure_db()
    async with SessionFactory() as session:
        from headofsocial.domain.models import Asset

        asset = await session.get(Asset, asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
        if not (asset.media_spec or []):
            raise HTTPException(status_code=400, detail="Asset has no media_spec")
        try:
            paths = await media_service.generate_media(session, asset)
        except media_service.BudgetExceededError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ok": True, "asset_id": asset.id, "media": [media_url(p) for p in paths]}