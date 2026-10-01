"""MockPublisher — no network; returns a realistic result and simulates metrics."""

import asyncio
import random

from headofsocial.domain.models import Asset, Post
from headofsocial.publishing.base import Publisher, PublishResult


class MockPublisher(Publisher):
    """Simulates publishing for any platform, plus plausible engagement numbers."""

    async def publish(self, post: Post, asset: Asset | None) -> PublishResult:
        await asyncio.sleep(random.uniform(0.05, 0.2))  # simulate latency
        external_id = f"{post.channel.platform}-{post.id}-{random.randint(100000, 999999)}"
        return PublishResult(
            ok=True,
            external_id=external_id,
            message=f"Mock publish to {post.channel.platform} succeeded (asset "
            f"{asset.id if asset else 'none'}). Simulated metrics recorded.",
        )


def simulate_metrics(post_id: int, platform: str) -> dict:
    """Generate plausible engagement figures drive the insights/history tools in mock mode."""
    base = random.randint(800, 5000)
    return {
        "post_id": post_id,
        "platform": platform,
        "impressions": base * random.randint(2, 5),
        "reach": base,
        "likes": int(base * random.uniform(0.05, 0.18)),
        "comments": int(base * random.uniform(0.005, 0.03)),
        "shares": int(base * random.uniform(0.003, 0.02)),
        "saves": int(base * random.uniform(0.004, 0.02)),
        "clicks": int(base * random.uniform(0.002, 0.015)),
        "follows": int(base * random.uniform(0.001, 0.01)),
    }