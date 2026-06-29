"""Tests for S3 asset storage helpers."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import Settings
from app.core.storage_paths import StorageAssetCategory
from app.services.storage.asset_storage_service import AssetStorageService
from app.utils.safe_url import assert_safe_remote_url


@pytest.fixture
def storage() -> AssetStorageService:
    settings = Settings(
        API_PUBLIC_URL="http://localhost:8000",
        API_V1_PREFIX="/api/v1",
        AWS_ACCESS_KEY_ID="test-key",
        AWS_SECRET_ACCESS_KEY="test-secret",
        S3_BUCKET_NAME="test-bucket",
    )
    return AssetStorageService(settings)


def test_assert_safe_remote_url_rejects_localhost() -> None:
    with pytest.raises(Exception, match="private address"):
        assert_safe_remote_url("http://localhost/image.jpg")


def test_build_media_url(storage: AssetStorageService) -> None:
    asset_id = uuid.UUID("11111111-2222-3333-4444-555555555555")
    url = storage.build_media_url(StorageAssetCategory.SHARED_MEMORIES, asset_id, "jpg")
    assert url == (
        "http://localhost:8000/api/v1/media/shared-memories/"
        "11111111-2222-3333-4444-555555555555.jpg"
    )


def test_is_managed_media_url(storage: AssetStorageService) -> None:
    asset_id = uuid.UUID("11111111-2222-3333-4444-555555555555")
    managed = storage.build_media_url(StorageAssetCategory.REVIEWS, asset_id, "png")
    assert storage.is_managed_media_url(managed) is True
    assert storage.is_managed_media_url("https://cdn.instagram.com/preview.jpg") is False


def test_parse_managed_media_url(storage: AssetStorageService) -> None:
    asset_id = uuid.UUID("11111111-2222-3333-4444-555555555555")
    managed = storage.build_media_url(StorageAssetCategory.SHARED_MEMORIES, asset_id, "webp")
    parsed = storage.parse_managed_media_url(managed)
    assert parsed == (StorageAssetCategory.SHARED_MEMORIES, asset_id, "webp")
