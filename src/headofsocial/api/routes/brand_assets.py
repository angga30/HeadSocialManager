"""Brand asset upload/list API (M1).

Mounted at `/api` in app.py, so the upload endpoint is `POST /api/brands/{id}/assets`
(multipart) — distinct from the content-asset routes under `/api/dashboard`.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from headofsocial.config import settings
from headofsocial.domain.enums import BrandAssetKind
from headofsocial.domain.models import Brand
from headofsocial.services import brand_service
from headofsocial.storage.db import SessionFactory
from headofsocial.tools._deps import brand_asset_to_dict, ensure_db

router = APIRouter(prefix="/brands", tags=["brand-assets"])

_KINDS = {k.value for k in BrandAssetKind}


async def _brand_or_404(session, brand_id: int) -> Brand:
    brand = await session.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail=f"Brand {brand_id} not found")
    return brand


@router.get("/{brand_id}/assets")
async def list_brand_assets(brand_id: int):
    await ensure_db()
    async with SessionFactory() as session:
        await _brand_or_404(session, brand_id)
        assets = await brand_service.list_brand_assets(session, brand_id)
        return [brand_asset_to_dict(a) for a in assets]


@router.post("/{brand_id}/assets")
async def upload_brand_asset(
    brand_id: int,
    kind: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    label: Annotated[str, Form()] = "",
    is_primary: Annotated[bool, Form()] = False,
):
    if kind not in _KINDS:
        raise HTTPException(status_code=400, detail=f"kind must be one of {sorted(_KINDS)}")
    suffix = "." + (file.filename or "asset.png").rsplit(".", 1)[-1].lower()

    await ensure_db()
    tmp = settings.resolved_data_dir / f"_upload_{uuid.uuid4().hex}{suffix}"
    tmp.write_bytes(await file.read())
    try:
        async with SessionFactory() as session:
            await _brand_or_404(session, brand_id)
            try:
                asset = await brand_service.register_brand_asset(
                    session, brand_id, kind, tmp, label or None, is_primary
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return brand_asset_to_dict(asset)
    finally:
        tmp.unlink(missing_ok=True)
