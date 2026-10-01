"""Async SQLAlchemy engine + session factory for SQLite (Postgres-ready).

Robustness notes:
- The DB URL is absolutised (see settings.resolved_db_url) so the path never depends on CWD.
- WAL + busy_timeout are set: two engines write to the same file (ours + ADK's
  DatabaseSessionService), and WAL avoids most "database is locked" contention.
- verify_writable() fails loudly *before* a run with a clear message, instead of every
  write later failing with "attempt to write a readonly database".
"""

import logging
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from headofsocial.config import settings
from headofsocial.domain.models import Base

logger = logging.getLogger(__name__)


def _ensure_data_dir(url: str, data_dir: Path) -> None:
    """Create the data dir for file-based DBs (sqlite) before the engine connects."""
    if url.startswith("sqlite"):
        data_dir.mkdir(parents=True, exist_ok=True)


def create_engine():
    url = settings.resolved_db_url
    _ensure_data_dir(url, settings.resolved_data_dir)
    eng = create_async_engine(url, echo=False, connect_args={"timeout": 30})

    if url.startswith("sqlite"):
        @event.listens_for(eng.sync_engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):  # noqa: ANN001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return eng


engine = create_engine()
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def db_path() -> Path | None:
    """Filesystem path of a file-based sqlite DB, else None."""
    url = settings.resolved_db_url
    if url.startswith("sqlite") and ":///" in url:
        return Path(url.partition(":///")[2])
    return None


def verify_writable() -> None:
    """Raise a clear error if the data dir (or DB file) cannot be written.

    A read-only data dir makes SQLite fail with "attempt to write a readonly database"
    on every write — better to surface it once, clearly, at startup.
    """
    if not settings.resolved_db_url.startswith("sqlite"):
        return
    data_dir = settings.resolved_data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    probe = data_dir / ".write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise RuntimeError(
            f"Direktori data tidak bisa ditulis: {data_dir} ({exc}). "
            "Perbaiki izin folder, atau hapus lalu buat ulang, kemudian restart server."
        ) from exc
    logger.info("Database: %s (direktori data writable)", db_path())


async def create_all() -> None:
    """Create tables in a fresh DB. For MVP schema bootstrap; use Alembic later."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with SessionFactory() as session:
        yield session


async def ping() -> bool:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True