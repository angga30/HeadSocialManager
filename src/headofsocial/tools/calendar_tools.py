"""Calendar tools — monthly plans and post slots the Planning/Publishing agents manage."""

from headofsocial.domain.models import Post
from headofsocial.domain.schemas import MonthlyPlan
from headofsocial.services import planning_service
from headofsocial.tools._deps import load_post, plan_to_dict, post_to_dict, run


async def create_monthly_plan(brand_id: int, plan: dict) -> dict:
    """Create a monthly editorial plan for a brand.

    Args:
        brand_id: Target brand.
        plan: dict with period (YYYY-MM), theme, weekly_themes [{week, focus, goal}],
            cadence {platform: posts_per_week}, content_mix {pillar %, format %},
            key_dates [{title, date}].
    """
    data = MonthlyPlan(**plan)
    async def _fn(session):
        row = await planning_service.create_plan(session, brand_id, data)
        return plan_to_dict(row)
    return await run(_fn)


async def get_existing_plan(brand_id: int, period: str) -> dict:
    """Fetch the plan for a brand in a given month (YYYY-MM), if one exists. Avoids duplicating a month."""
    async def _fn(session):
        plan = await planning_service.get_existing_plan(session, brand_id, period)
        return {"ok": True, "plan": plan_to_dict(plan) if plan else None}
    return await run(_fn)


async def fan_out_plan(plan_id: int) -> dict:
    """Materialize a plan into concrete draft post slots across its channels.

    Args:
        plan_id: The plan to fan out.
    """
    async def _fn(session):
        posts = await planning_service.fan_out_plan(session, plan_id)
        return {"ok": True, "created": len(posts), "posts": [post_to_dict(p) for p in posts]}
    return await run(_fn)


async def list_scheduled_posts(brand_id: int) -> dict:
    """List all posts for a brand (draft through published), newest first."""
    from headofsocial.storage import repos
    async def _fn(session):
        posts = await repos.list_posts(session, brand_id)
        return {"ok": True, "posts": [post_to_dict(p) for p in posts]}
    return await run(_fn)


async def get_post(post_id: int) -> dict:
    """Fetch one post slot's details (channel, pillar, status, schedule, attached asset).

    Call this before writing content so the copy matches the slot's channel, pillar, and time.
    """
    async def _fn(session):
        post = await load_post(session, post_id)
        if post is None:
            return {"ok": False, "error": f"Post {post_id} not found"}
        return {"ok": True, "post": post_to_dict(post)}
    return await run(_fn)


async def approve_post(post_id: int) -> dict:
    """Mark a draft post as scheduled. Requires a scheduled_at time AND an attached asset."""
    from headofsocial.services import publishing_service
    async def _fn(session):
        post = await load_post(session, post_id)
        if post is None:
            return {"ok": False, "error": f"Post {post_id} not found"}
        try:
            await publishing_service.schedule_post(session, post)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        post = await load_post(session, post_id)
        if post is None:
            return {"ok": False, "error": "post hilang setelah approve"}
        return {"ok": True, **post_to_dict(post)}
    return await run(_fn)


async def publish_now(post_id: int) -> dict:
    """Immediately publish a post via its channel publisher (mock in phase 1)."""
    from headofsocial.services import publishing_service
    async def _fn(session):
        post = await session.get(Post, post_id)
        if post is None:
            return {"ok": False, "error": f"Post {post_id} not found"}
        post = await publishing_service.publish_post(session, post)
        ok = bool(post.publish_result and post.publish_result.get("ok"))
        return {"ok": ok, **post_to_dict(post)}
    return await run(_fn)