"""Research tools — web search, trend + competitor research for agents (R1/R2).

All tools degrade gracefully: when research is disabled or unconfigured they return
`{ok: False, available: False, error: ...}` instead of raising, so a plan run still completes.
"""

from headofsocial.domain.enums import ResearchKind
from headofsocial.domain.models import Brand
from headofsocial.services import research_service
from headofsocial.tools._deps import run


async def search_web(query: str, max_results: int = 5, brand_id: int = 0) -> dict:
    """Search the web for current facts/statistics; use to fact-check claims in content.

    Args:
        query: The search query.
        max_results: How many results to return (default 5).
        brand_id: Optional brand id for caching/budget accounting.
    """
    async def _fn(session):
        try:
            results = await research_service.search_cached(
                session, brand_id, ResearchKind.WEB, query, max_results
            )
        except research_service.ResearchUnavailableError as exc:
            return {"ok": False, "available": False, "error": str(exc)}
        except research_service.ResearchBudgetExceededError as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "query": query,
            "count": len(results),
            "results": results,
            "sources": [r.get("url") for r in results if r.get("url")],
        }

    return await run(_fn)


async def research_trends(brand_id: int, focus: str = "") -> dict:
    """Research current trends/topics for the brand's niche (call before monthly planning).

    Starts a fresh research run (resets the query budget), then returns hot topics + sources.

    Args:
        brand_id: Brand whose industry/pillars anchor the trend query.
        focus: Optional extra focus (e.g. a campaign or product line).
    """
    async def _fn(session):
        brand = await session.get(Brand, brand_id)
        if brand is None:
            return {"ok": False, "error": f"Brand {brand_id} not found"}
        research_service.reset_run(brand_id)
        query = research_service.trend_query(brand, focus)
        try:
            results = await research_service.search_cached(
                session, brand_id, ResearchKind.TRENDS, query, 5
            )
        except research_service.ResearchUnavailableError as exc:
            return {"ok": False, "available": False, "error": str(exc)}
        except research_service.ResearchBudgetExceededError as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "query": query,
            "count": len(results),
            "results": results,
            "sources": [r.get("url") for r in results if r.get("url")],
            "guidance": (
                "Angkat minimal 1 hook topikal dari temuan ini di weekly_themes, dan sebut "
                "sumbernya di draft."
            ),
        }

    return await run(_fn)


async def research_competitors(brand_id: int, competitor_names: str = "") -> dict:
    """Research competitors' positioning/content to ground differentiators (call in positioning).

    Args:
        brand_id: Brand we are positioning.
        competitor_names: Optional comma-separated competitor names.
    """
    async def _fn(session):
        brand = await session.get(Brand, brand_id)
        if brand is None:
            return {"ok": False, "error": f"Brand {brand_id} not found"}
        query = research_service.competitor_query(brand, competitor_names)
        try:
            results = await research_service.search_cached(
                session, brand_id, ResearchKind.COMPETITORS, query, 5
            )
        except research_service.ResearchUnavailableError as exc:
            return {"ok": False, "available": False, "error": str(exc)}
        except research_service.ResearchBudgetExceededError as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "query": query,
            "count": len(results),
            "results": results,
            "sources": [r.get("url") for r in results if r.get("url")],
            "guidance": "Kutip temuan ini dengan sumber saat merumuskan differentiators.",
        }

    return await run(_fn)
