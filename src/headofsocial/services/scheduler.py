"""APScheduler job that publishes due posts. Started by the TUI (and later FastAPI lifespan)."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from headofsocial.services.publishing_service import publish_due
from headofsocial.storage.db import SessionFactory

logger = logging.getLogger(__name__)

_POLL_SECONDS = 15


async def _run_due_publishing() -> None:
    """Publish posts that are scheduled and past due; called on an interval."""
    try:
        async with SessionFactory() as session:
            published = await publish_due(session)
        if published:
            logger.info("Published %d due post(s)", len(published))
    except Exception as exc:  # never let the scheduler loop die
        logger.exception("Scheduler tick failed: %s", exc)


class PublishingScheduler:
    """Small wrapper so the TUI/app can start/stop the loop without knowing APScheduler."""

    def __init__(self, poll_seconds: int = _POLL_SECONDS) -> None:
        self._poll_seconds = poll_seconds
        self._scheduler: AsyncIOScheduler | None = None

    def start(self) -> None:
        if self._scheduler and self._scheduler.running:
            return
        sched = AsyncIOScheduler(timezone="UTC")
        sched.add_job(
            _run_due_publishing,
            trigger=IntervalTrigger(seconds=self._poll_seconds),
            id="publish_due",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        sched.start()
        self._scheduler = sched
        logger.info("Publishing scheduler started (every %ds)", self._poll_seconds)

    def stop(self) -> None:
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    @property
    def running(self) -> bool:
        return bool(self._scheduler and self._scheduler.running)


# Re-export the standalone async function for direct use/tests.
run_due_publishing = _run_due_publishing


def spin_once_for_test() -> None:
    """Run the due-publishing tick once (used by tests / manual verification)."""
    asyncio.run(_run_due_publishing())