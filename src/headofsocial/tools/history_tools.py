"""History tools — past content with performance, so planning avoids dupes and lifts winners."""

from headofsocial.services import analytics_service
from headofsocial.tools._deps import run


async def get_content_history(brand_id: int, days: int = 90) -> dict:
    """Return a summarized feed of past posts with engagement rates.

    Args:
        brand_id: Brand to analyze.
        days: Lookback window in days (default 90).
    """
    async def _fn(session):
        history = await analytics_service.get_content_history(session, brand_id, days)
        return {
            "ok": True,
            "days": days,
            "count": len(history),
            "history": history,
            "guidance": (
                "Use this to avoid repeating recent angles/topics and to double down "
                "on pillars/formats/channels with the highest engagement_rate."
            ),
        }
    return await run(_fn)