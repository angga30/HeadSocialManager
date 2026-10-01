"""Monthly plan persistence and fan-out into concrete post slots."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from headofsocial.domain.enums import PostStatus
from headofsocial.domain.models import Brand, Plan, Post
from headofsocial.domain.schemas import MonthlyPlan
from headofsocial.storage import repos


async def create_plan(session: AsyncSession, brand_id: int, plan: MonthlyPlan) -> Plan:
    row = Plan(
        brand_id=brand_id,
        period=plan.period,
        status="draft",
        theme=plan.theme,
        weekly_themes=[t.model_dump() for t in plan.weekly_themes],
        cadence=plan.cadence,
        content_mix=plan.content_mix,
        key_dates=plan.key_dates,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_existing_plan(session: AsyncSession, brand_id: int, period: str) -> Plan | None:
    for p in await repos.list_plans(session, brand_id):
        if p.period == period:
            return p
    return None


async def fan_out_plan(session: AsyncSession, plan_id: int) -> list[Post]:
    """Materialize a plan into draft post slots across its channels.

    Uses each channel's cadence (posts/week) from the plan. Draft slots are created
    without content — the Content Agent fills them later. Pillar is rotated across the
    brand's content pillars so no slot is empty.
    """
    plan = await session.get(Plan, plan_id)
    if plan is None:
        raise ValueError(f"Plan {plan_id} not found")

    brand = await session.get(Brand, plan.brand_id)
    channels = await repos.list_channels(session, plan.brand_id)
    if not channels:
        return []

    cadence = plan.cadence or {}
    pillars = brand.content_pillars or [{"name": "default"}]
    created: list[Post] = []
    slot_seq = 0

    for channel in channels:
        posts_per_week = cadence.get(channel.platform, 3)
        # approximate: spread weekly slots across 4 weeks of the period
        weeks = max(len(plan.weekly_themes) or 4, 1)
        for week in range(weeks):
            for _ in range(posts_per_week):
                pillar_obj = pillars[slot_seq % len(pillars)]
                pillar_name = (
                    pillar_obj.get("name", "default") if isinstance(pillar_obj, dict) else str(pillar_obj)
                )
                scheduled_at = _estimate_slot(plan.period, week, posts_per_week)
                post = Post(
                    brand_id=plan.brand_id,
                    channel_id=channel.id,
                    plan_id=plan.id,
                    scheduled_at=scheduled_at,
                    status=PostStatus.DRAFT,
                    pillar=pillar_name,
                )
                session.add(post)
                created.append(post)
                slot_seq += 1

    await session.commit()
    # Re-load with eager relationships so callers don't trigger a lazy load in the
    # async session (which raises MissingGreenlet).
    ids = [p.id for p in created]
    result = await session.execute(
        select(Post)
        .where(Post.id.in_(ids))
        .options(selectinload(Post.channel), selectinload(Post.asset), selectinload(Post.plan))
    )
    loaded = list(result.scalars().all())
    return sorted(loaded, key=lambda p: p.id)


def _estimate_slot(period: str, week: int, per_week: int) -> datetime:
    """Spread slots Mon-Fri within the given SLOT week of a month period."""
    from calendar import monthrange

    year, month = (int(x) for x in period.split("-"))
    first_weekday, n_days = monthrange(year, month)
    # anchor at week*7 days into the month
    base = datetime(year, month, 1) + timedelta(days=7 * week)
    # distribute within the week across weekdays
    offset_minutes = (per_week % 5) * 4 * 60  # stagger posting hours
    slot = base + timedelta(days=2, hours=9, minutes=offset_minutes % 600)
    if slot.month != month or slot.day > n_days:
        slot = datetime(year, month, min(n_days, base.day))
    return slot