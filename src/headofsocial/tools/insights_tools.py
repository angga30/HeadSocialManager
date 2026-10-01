"""Insight tools — aggregated performance for the Planning Agent to reason over."""

from headofsocial.services import analytics_service
from headofsocial.tools._deps import run


async def get_engagement_insights(brand_id: int, days: int = 90) -> dict:
    """Return aggregate engagement insights for a brand across recent days.

    Args:
        brand_id: Brand to analyze.
        days: Lookback window in days (default 90).
    """
    async def _fn(session):
        ins = await analytics_service.get_engagement_insights(session, brand_id, days)
        return {
            "ok": True,
            "days": days,
            "top_posts": [p.model_dump() for p in ins.top_posts],
            "bottom_posts": [p.model_dump() for p in ins.bottom_posts],
            "best_times": ins.best_times,
            "format_performance": ins.format_performance,
            "channel_notes": ins.channel_notes,
        }
    return await run(_fn)