"""Public media proxy for private S3 assets."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Response

from app.core.exceptions import NotFoundError, ValidationError
from app.core.storage_paths import StorageAssetCategory
from app.services.storage.asset_storage_service import get_asset_storage_service

router = APIRouter(tags=["Media"])

_ALLOWED_CATEGORIES = frozenset(StorageAssetCategory)


@router.get("/media/{category}/{asset_id}.{extension}")
def get_media_asset(
    category: str,
    asset_id: uuid.UUID,
    extension: str,
) -> Response:
    """Stream a cached asset from S3 via a stable API URL."""
    storage = get_asset_storage_service()
    try:
        asset_category = StorageAssetCategory(category)
    except ValueError as exc:
        raise NotFoundError("Media asset not found.") from exc

    if asset_category not in _ALLOWED_CATEGORIES:
        raise NotFoundError("Media asset not found.")

    if not storage.enabled:
        raise NotFoundError("Media asset not found.")

    try:
        body, content_type = storage.get_object_bytes(asset_category, asset_id, extension)
    except ValidationError as exc:
        raise NotFoundError("Media asset not found.") from exc

    return Response(
        content=body,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
