"""Test fixtures: fresh in-memory DB per test session."""

import os

# Force deterministic media provider before importing the app (load_dotenv won't override
# an existing os.environ value), so tests never hit the network for image generation.
os.environ["HEADSOF_MEDIA_PROVIDER"] = "mock"

import pytest_asyncio  # noqa: E402

from headofsocial.domain.enums import BrandType, Platform  # noqa: E402
from headofsocial.domain.schemas import ChannelInput  # noqa: E402
from headofsocial.services import brand_service  # noqa: E402
from headofsocial.storage.db import SessionFactory, engine  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _clean_db():
    # Point at a throwaway sqlite file for tests (env override before engine connect).
    from sqlalchemy import text

    # Ensure schema exists (create_all is idempotent).
    from headofsocial.storage.db import create_all

    await create_all()
    # Wipe rows between tests (children before parents — foreign_keys=ON enforces FKs).
    async with engine.begin() as conn:
        for table in (
            "chat_messages",
            "conversations",
            "post_metrics",
            "posts",
            "assets",
            "plans",
            "channels",
            "brand_assets",
            "research_notes",
            "brands",
        ):
            await conn.execute(text(f"DELETE FROM {table}"))
    yield
    async with SessionFactory() as s:
        await s.close()


@pytest_asyncio.fixture
async def session():
    async with SessionFactory() as s:
        yield s


@pytest_asyncio.fixture
async def brand(session):
    return await brand_service.create_brand(
        session, "Kopi Nusantara", BrandType.BUSINESS,
        "Artisan coffee", industry="F&B", language="id",
    )


@pytest_asyncio.fixture
async def channel(session, brand):
    return await brand_service.create_channel(
        session, brand.id,
        ChannelInput(platform=Platform.INSTAGRAM, handle="kopi.nusantara"),
    )