"""Publisher protocol and shared result type."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from headofsocial.domain.models import Asset, Post


@dataclass
class PublishResult:
    ok: bool
    external_id: str = ""
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "external_id": self.external_id,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class Publisher(Protocol):
    """Publish a post to a single platform. Implementations must be async."""

    async def publish(self, post: Post, asset: Asset | None) -> PublishResult: ...


class Registry:
    """Map platform names to Publisher instances (drop-in swapping)."""

    def __init__(self) -> None:
        self._publishers: dict[str, Publisher] = {}

    def register(self, platform: str, publisher: Publisher) -> None:
        self._publishers[platform] = publisher

    def get(self, platform: str) -> Publisher:
        return self._publishers[platform]

    def platforms(self) -> list[str]:
        return sorted(self._publishers)


_global: Registry | None = None


def get_registry() -> Registry:
    """Lazily-built global registry.

    Phase 1 routes every platform through MockPublisher so publishing (and the metrics
    it simulates) works end-to-end without real credentials. When a real adapter is
    ready, replace the mock entry for that platform — the service doesn't change.
    """
    global _global
    if _global is None:
        # Import real adapters so their docstrings/errors are discoverable, but in
        # phase 1 all platforms resolve to MockPublisher.
        from headofsocial.publishing.mock import MockPublisher

        _global = Registry()
        for platform in ("instagram", "threads", "linkedin", "mock"):
            _global.register(platform, MockPublisher())
    return _global