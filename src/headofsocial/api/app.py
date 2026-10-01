"""FastAPI app factory (skeleton). Shares the services layer with the TUI.

Future dashboard routes (brands, plans, posts, insights) will mount here.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from headofsocial.api.routes.brand_assets import router as brand_assets_router
from headofsocial.api.routes.chat import router as chat_router
from headofsocial.api.routes.dashboard import router as dashboard_router
from headofsocial.api.routes.health import router as health_router
from headofsocial.config import settings
from headofsocial.logging_config import configure_logging
from headofsocial.services import conversation_service
from headofsocial.services.scheduler import PublishingScheduler
from headofsocial.storage.db import SessionFactory, create_all, verify_writable


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    verify_writable()  # fail fast with a clear message if data/ can't be written
    await create_all()
    # Any conversation left mid-stream by a crash/restart is no longer processing.
    async with SessionFactory() as session:
        await conversation_service.reset_stale_processing(session)
    scheduler = PublishingScheduler()
    scheduler.start()
    yield
    scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="Head of Social Media Agent", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")
    app.include_router(brand_assets_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")

    # Serve generated media (data/media) at /media so the UI can display images/videos.
    media_dir = settings.resolved_data_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

    # Serve uploaded brand assets (data/brand_assets) so the Brands gallery can display them.
    brand_assets_dir = settings.resolved_brand_assets_dir
    brand_assets_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/brand-assets", StaticFiles(directory=str(brand_assets_dir)), name="brand-assets")

    # Serve the built SPA (web/dist) at /app when present; skip in dev (Vite serves it).
    dist = Path(__file__).resolve().parents[3] / "web" / "dist"
    if dist.is_dir():
        app.mount("/app", StaticFiles(directory=str(dist), html=True), name="spa")
    return app


app = create_app()