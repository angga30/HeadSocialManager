"""Web research (Tavily) for trend + competitor grounding (R1/R3).

Design goals:
- **Graceful degradation**: no provider / no API key => tools report "tidak tersedia" and
  the agent keeps going without research (never a hard failure).
- **Cache**: results are stored in `research_notes` (TTL 7 days) so monthly planning does
  not re-query the same thing.
- **Budget**: a hard cap of `max_research_queries_per_run` real queries per research run
  (mirrors the media budget pattern). A run starts when `research_trends` resets the counter.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from headofsocial.config import settings
from headofsocial.domain.enums import ResearchKind
from headofsocial.domain.models import Brand, ResearchNote
from headofsocial.storage import repos

logger = logging.getLogger(__name__)


class ResearchUnavailableError(RuntimeError):
    """Raised when research is disabled or misconfigured (no provider / no API key)."""


class ResearchBudgetExceededError(RuntimeError):
    """Raised when a research run exceeds its hard query cap."""


# brand_id -> queries issued in the current run (reset by research_trends).
_run_counts: dict[int, int] = {}


def reset_run(brand_id: int) -> None:
    """Start a fresh research run for a brand (called when planning kicks off)."""
    _run_counts[brand_id] = 0


def _tick(brand_id: int) -> None:
    count = _run_counts.get(brand_id, 0) + 1
    if count > settings.max_research_queries_per_run:
        raise ResearchBudgetExceededError(
            f"Riset melebihi batas {settings.max_research_queries_per_run} query per plan-run."
        )
    _run_counts[brand_id] = count


class TavilyResearch:
    """Thin wrapper over the official Tavily async client."""

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        response = await client.search(query, max_results=max_results)
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
            }
            for item in response.get("results", [])
        ]


def get_provider() -> TavilyResearch | None:
    """Return the configured research provider, or None when research is unavailable."""
    provider = (settings.research_provider or "none").lower()
    if provider == "none":
        return None
    if provider == "tavily":
        if not settings.tavily_api_key:
            logger.info("Research provider=tavily but no HEADSOF_TAVILY_API_KEY; disabled.")
            return None
        return TavilyResearch()
    logger.warning("Unknown research provider %r; research disabled.", provider)
    return None


async def search_cached(
    session: AsyncSession,
    brand_id: int,
    kind: ResearchKind | str,
    query: str,
    max_results: int = 5,
    *,
    use_cache: bool = True,
) -> list[dict]:
    """Run a web query, caching the result; raises for unavailability / budget."""
    provider = get_provider()
    if provider is None:
        raise ResearchUnavailableError(
            "Riset web tidak tersedia (provider=none atau HEADSOF_TAVILY_API_KEY kosong)."
        )
    kind_value = str(kind)

    if use_cache:
        since = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            days=settings.research_cache_ttl_days
        )
        cached = await repos.find_research_note(session, brand_id, kind_value, query, since)
        if cached is not None:
            return cached.results or []

    _tick(brand_id)
    results = await provider.search(query, max_results)
    session.add(
        ResearchNote(brand_id=brand_id, kind=kind_value, query=query, results=results)
    )
    await session.flush()
    return results


def _pillar_names(brand: Brand) -> str:
    names = [
        (p.get("name") if isinstance(p, dict) else str(p))
        for p in (brand.content_pillars or [])
    ]
    return ", ".join(name for name in names if name)


def trend_query(brand: Brand, focus: str = "") -> str:
    parts = [f"tren terbaru industri {brand.industry or brand.name}"]
    if focus:
        parts.append(focus)
    pillars = _pillar_names(brand)
    if pillars:
        parts.append(f"topik: {pillars}")
    return " ".join(parts)


def competitor_query(brand: Brand, competitor_names: str = "") -> str:
    target = competitor_names or f"kompetitor {brand.industry or brand.name}"
    return f"positioning dan strategi konten {target}"
