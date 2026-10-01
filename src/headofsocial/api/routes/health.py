"""Health check route."""

from fastapi import APIRouter

from headofsocial.storage.db import ping

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict:
    db_ok = await ping()
    return {"status": "ok", "db": bool(db_ok)}