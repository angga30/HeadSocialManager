"""R1/R3 — research tools: graceful degradation, caching, and the per-run query budget."""

import pytest

from headofsocial.config import settings
from headofsocial.domain.enums import ResearchKind
from headofsocial.services import research_service
from headofsocial.tools import research_tools


class _FakeResearch:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        self.queries.append(query)
        return [{"title": "T", "url": "https://example.com/a", "snippet": "S"}]


async def test_unavailable_is_graceful(session, brand, monkeypatch):
    monkeypatch.setattr(settings, "research_provider", "none")
    result = await research_tools.research_trends(brand.id)
    assert result["ok"] is False and result["available"] is False


async def test_trends_query_and_cache(session, brand, monkeypatch):
    fake = _FakeResearch()
    monkeypatch.setattr(research_service, "get_provider", lambda: fake)

    first = await research_tools.research_trends(brand.id, focus="kopi")
    assert first["ok"] and first["count"] == 1
    assert "kopi" in first["query"] and brand.industry in first["query"]

    second = await research_tools.research_trends(brand.id, focus="kopi")
    assert second["ok"] and second["count"] == 1
    assert len(fake.queries) == 1  # identical query served from cache


async def test_budget_enforced(session, brand, monkeypatch):
    monkeypatch.setattr(settings, "max_research_queries_per_run", 2)
    fake = _FakeResearch()
    monkeypatch.setattr(research_service, "get_provider", lambda: fake)
    research_service.reset_run(brand.id)

    await research_service.search_cached(session, brand.id, ResearchKind.WEB, "q1", use_cache=False)
    await research_service.search_cached(session, brand.id, ResearchKind.WEB, "q2", use_cache=False)
    with pytest.raises(research_service.ResearchBudgetExceededError):
        await research_service.search_cached(session, brand.id, ResearchKind.WEB, "q3", use_cache=False)
