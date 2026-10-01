"""Aggregate performance analytics (insights + content history) for the Planning Agent."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from headofsocial.domain.models import Post, PostMetrics
from headofsocial.domain.schemas import EngagementInsights, PostInsight
from headofsocial.storage import repos


def _engagement_rate(m: PostMetrics) -> float:
    reach = m.reach or 1
    return (m.likes + m.comments + m.shares + m.saves + m.clicks) / reach


def _join_post(post: Post, metric: PostMetrics | None) -> PostInsight:
    ctx = {
        "post_id": post.id,
        "channel": str(post.channel.platform) if post.channel else "?",
        "depth": post.depth_hint or "",
        "pillar": post.pillar or "",
        "headline": (post.asset.body or "")[:80] if post.asset and post.asset.body else "",
    }
    if metric is not None:
        ctx["engagement_rate"] = round(_engagement_rate(metric), 4)
    return PostInsight(**ctx)


def _metric_for(post: Post, metrics: list[PostMetrics]) -> PostMetrics | None:
    return next((m for m in metrics if m.post_id == post.id), None)


async def get_engagement_insights(
    session: AsyncSession, brand_id: int, days: int = 90
) -> EngagementInsights:
    posts = await repos.list_posts(session, brand_id)
    published = [p for p in posts if p.status == "published"]
    metrics = await repos.list_metrics_for_posts(session, [p.id for p in published])

    insights = [_join_post(p, _metric_for(p, metrics)) for p in published]
    insights = [i for i in insights if i.engagement_rate > 0]

    top = sorted(insights, key=lambda i: i.engagement_rate, reverse=True)[:5]
    bottom = sorted(insights, key=lambda i: i.engagement_rate)[:3]

    # Format performance by depth.
    depth_map: dict[str, list[float]] = {}
    for i in insights:
        depth_map.setdefault(i.depth or "unknown", []).append(i.engagement_rate)
    format_perf = [
        {"depth": d, "avg_engagement_rate": round(sum(v) / len(v), 4)} for d, v in depth_map.items()
    ]

    # Channel comparison.
    chan_map: dict[str, list[float]] = {}
    for i in insights:
        chan_map.setdefault(i.channel, []).append(i.engagement_rate)
    channel_notes = [
        {"channel": c, "avg_engagement_rate": round(sum(v) / len(v), 4)} for c, v in chan_map.items()
    ]

    # Best times (day-of-week aggregate).
    best_times = _aggregate_best_times(published, metrics)

    return EngagementInsights(
        top_posts=top,
        bottom_posts=bottom,
        best_times=best_times,
        format_performance=format_perf,
        channel_notes=channel_notes,
    )


async def get_content_history(
    session: AsyncSession, brand_id: int, days: int = 90
) -> list[dict]:
    """Summarized, windowed feed of past posts for planning context (avoid dupes, lift winners)."""
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    posts = await repos.list_posts(session, brand_id)
    published = [p for p in posts if p.published_at and p.published_at >= cutoff]
    metrics = await repos.list_metrics_for_posts(session, [p.id for p in published])

    history = []
    for p in sorted(published, key=lambda x: x.published_at or x.created_at):
        m = _metric_for(p, metrics)
        history.append(
            {
                "period": p.published_at.date().isoformat() if p.published_at else "",
                "channel": str(p.channel.platform) if p.channel else "?",
                "pillar": p.pillar or "",
                "depth": p.depth_hint or "",
                "headline": (p.asset.body or "")[:60] if p.asset and p.asset.body else "",
                "engagement_rate": round(_engagement_rate(m), 4) if m else 0.0,
            }
        )
    return history


def _aggregate_best_times(posts: list[Post], metrics: list[PostMetrics]) -> list[dict]:
    day_agg: dict[str, list[float]] = {}
    for p in posts:
        if not p.published_at:
            continue
        m = _metric_for(p, metrics)
        if m is None or m.reach == 0:
            continue
        day = p.published_at.strftime("%A")
        day_agg.setdefault(day, []).append(_engagement_rate(m))
    ranked = sorted(
        ({"day": d, "avg_engagement_rate": round(sum(v) / len(v), 4)} for d, v in day_agg.items()),
        key=lambda x: x["avg_engagement_rate"],
        reverse=True,
    )
    return ranked[:5]