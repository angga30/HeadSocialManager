"""Planning — create monthly plan and fan out to post slots."""

from headofsocial.domain.enums import Platform, PostStatus
from headofsocial.domain.schemas import ChannelInput, MonthlyPlan, WeeklyTheme
from headofsocial.services import brand_service, planning_service


async def _mk_plan():
    return MonthlyPlan(
        period="2026-11",
        theme="Harvest season",
        weekly_themes=[WeeklyTheme(week=i, focus=f"W{i}", goal="awareness") for i in range(1, 5)],
        cadence={"instagram": 3, "linkedin": 2},
        key_dates=[{"title": "Coffee Day", "date": "2026-11-01"}],
    )


async def test_fan_out_creates_slots(session, brand):
    await brand_service.create_channel(
        session, brand.id, ChannelInput(platform=Platform.INSTAGRAM, handle="ig")
    )
    await brand_service.create_channel(
        session, brand.id, ChannelInput(platform=Platform.LINKEDIN, handle="li")
    )
    plan = await planning_service.create_plan(session, brand.id, await _mk_plan())
    posts = await planning_service.fan_out_plan(session, plan.id)

    # 4 weeks * (3 IG + 2 LI) = 20 slots
    assert len(posts) == 20
    for p in posts:
        assert p.status == PostStatus.DRAFT
        assert p.brand_id == brand.id
        assert p.plan_id == plan.id
        assert p.pillar  # every slot tagged with a pillar


async def test_get_existing_plan(session, brand):
    assert await planning_service.get_existing_plan(session, brand.id, "2026-11") is None
    plan = await planning_service.create_plan(session, brand.id, await _mk_plan())
    found = await planning_service.get_existing_plan(session, brand.id, "2026-11")
    assert found is not None and found.id == plan.id