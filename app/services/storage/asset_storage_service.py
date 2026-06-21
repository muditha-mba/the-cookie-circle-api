"""AWS S3 asset storage for durable media URLs."""

from __future__ import annotations

import logging
import re
import uuid
from functools import lru_cache
from typing import Any

import boto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationError
from app.core.storage_paths import StorageAssetCategory
from app.utils.safe_url import assert_safe_remote_url

logger = logging.getLogger(__name__)

_MEDIA_FILENAME_PATTERN = re.compile(
    r"^(?P<asset_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.(?P<extension>jpg|jpeg|png|webp|gif)$",
    re.IGNORECASE,
)

_CONTENT_TYPE_EXTENSIONS: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}

_ALLOWED_EXTENSIONS = frozenset(_CONTENT_TYPE_EXTENSIONS.values())

_MAX_IMAGE_BYTES = 5 * 1024 * 1024

_DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TheCookieCircle/1.0; +https://thecookiecircle.lk)",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}


class AssetStorageService:
    """Upload, serve, and delete cached images in S3."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.aws_access_key_id
            and self.settings.aws_secret_access_key
            and self.settings.s3_bucket_name,
        )

    def prefix_for(self, category: StorageAssetCategory) -> str:
        if category is StorageAssetCategory.SHARED_MEMORIES:
            return self.settings.s3_shared_memories_prefix
        if category is StorageAssetCategory.REVIEWS:
            return self.settings.s3_reviews_prefix
        raise ValidationError(f"Unsupported asset category: {category}")

    def build_object_key(
        self,
        category: StorageAssetCategory,
        asset_id: uuid.UUID,
        extension: str,
    ) -> str:
        normalized_extension = extension.lower().removeprefix(".")
        if normalized_extension not in _ALLOWED_EXTENSIONS:
            raise ValidationError("Unsupported image format.")
        return f"{self.prefix_for(category)}/{asset_id}.{normalized_extension}"

    def build_media_url(
        self,
        category: StorageAssetCategory,
        asset_id: uuid.UUID,
        extension: str,
    ) -> str:
        normalized_extension = extension.lower().removeprefix(".")
        base = self.settings.api_public_url.rstrip("/")
        prefix = self.settings.api_v1_prefix.rstrip("/")
        return f"{base}{prefix}/media/{category.value}/{asset_id}.{normalized_extension}"

    def is_managed_media_url(self, url: str | None) -> bool:
        if not url:
            return False
        base = self.settings.api_public_url.rstrip("/")
        prefix = self.settings.api_v1_prefix.rstrip("/")
        return url.startswith(f"{base}{prefix}/media/")

    def parse_managed_media_url(
        self,
        url: str,
    ) -> tuple[StorageAssetCategory, uuid.UUID, str] | None:
        if not self.is_managed_media_url(url):
            return None

        base = self.settings.api_public_url.rstrip("/")
        prefix = self.settings.api_v1_prefix.rstrip("/")
        relative = url.removeprefix(f"{base}{prefix}/media/").strip("/")
        parts = relative.split("/", maxsplit=1)
        if len(parts) != 2:
            return None

        category_value, filename = parts
        try:
            category = StorageAssetCategory(category_value)
        except ValueError:
            return None

        match = _MEDIA_FILENAME_PATTERN.match(filename)
        if not match:
            return None

        return (
            category,
            uuid.UUID(match.group("asset_id")),
            match.group("extension").lower(),
        )

    def cache_image_from_url(
        self,
        source_url: str,
        category: StorageAssetCategory,
        asset_id: uuid.UUID,
    ) -> str:
        if not self.enabled:
            return source_url

        safe_url = assert_safe_remote_url(source_url)
        image_bytes, content_type = self._download_image(safe_url)
        extension = _CONTENT_TYPE_EXTENSIONS.get(content_type.lower())
        if not extension:
            raise ValidationError("Preview image must be JPEG, PNG, WebP, or GIF.")

        object_key = self.build_object_key(category, asset_id, extension)
        self._upload_object(object_key, image_bytes, content_type)
        return self.build_media_url(category, asset_id, extension)

    def get_object_bytes(
        self,
        category: StorageAssetCategory,
        asset_id: uuid.UUID,
        extension: str,
    ) -> tuple[bytes, str]:
        object_key = self.build_object_key(category, asset_id, extension)
        client = self._get_client()

        try:
            response = client.get_object(
                Bucket=self.settings.resolved_s3_bucket_name,
                Key=object_key,
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"NoSuchKey", "404", "NotFound"}:
                raise ValidationError("Media asset not found.") from exc
            logger.exception("Failed to read S3 object %s", object_key)
            raise ValidationError("Unable to load media asset.") from exc
        except BotoCoreError as exc:
            logger.exception("Failed to read S3 object %s", object_key)
            raise ValidationError("Unable to load media asset.") from exc

        body = response["Body"].read()
        content_type = response.get("ContentType") or "application/octet-stream"
        return body, content_type

    def delete_asset(
        self,
        category: StorageAssetCategory,
        asset_id: uuid.UUID,
        extension: str | None = None,
    ) -> None:
        if not self.enabled:
            return

        extensions = [extension] if extension else sorted(_ALLOWED_EXTENSIONS)
        client = self._get_client()

        for candidate in extensions:
            if not candidate:
                continue
            object_key = self.build_object_key(category, asset_id, candidate)
            try:
                client.delete_object(
                    Bucket=self.settings.resolved_s3_bucket_name,
                    Key=object_key,
                )
            except (ClientError, BotoCoreError):
                logger.exception("Failed to delete S3 object %s", object_key)

    def delete_managed_url(self, url: str | None) -> None:
        parsed = self.parse_managed_media_url(url or "")
        if not parsed:
            return
        category, asset_id, extension = parsed
        self.delete_asset(category, asset_id, extension)

    def _download_image(self, source_url: str) -> tuple[bytes, str]:
        try:
            with httpx.Client(
                timeout=httpx.Timeout(20.0, connect=10.0),
                follow_redirects=True,
                headers=_DOWNLOAD_HEADERS,
            ) as client:
                response = client.get(source_url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Failed to download preview image from %s", source_url)
            raise ValidationError(
                "Unable to download the preview image. Fetch preview again, then save.",
            ) from exc

        content_type = (response.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
        if not content_type.startswith("image/"):
            raise ValidationError("Preview URL did not return an image.")

        image_bytes = response.content
        if len(image_bytes) > _MAX_IMAGE_BYTES:
            raise ValidationError("Preview image is too large (max 5 MB).")

        return image_bytes, content_type

    def _upload_object(self, object_key: str, body: bytes, content_type: str) -> None:
        client = self._get_client()
        try:
            client.put_object(
                Bucket=self.settings.resolved_s3_bucket_name,
                Key=object_key,
                Body=body,
                ContentType=content_type,
                CacheControl="public, max-age=31536000, immutable",
            )
            logger.info(
                "Uploaded asset to s3://%s/%s",
                self.settings.resolved_s3_bucket_name,
                object_key,
            )
        except (ClientError, BotoCoreError) as exc:
            logger.exception("Failed to upload S3 object %s", object_key)
            raise ValidationError("Unable to store preview image.") from exc

    def _get_client(self) -> Any:
        return _get_s3_client(
            self.settings.aws_access_key_id or "",
            self.settings.aws_secret_access_key or "",
            self.settings.aws_region,
        )


@lru_cache
def _get_s3_client(access_key_id: str, secret_access_key: str, region: str) -> Any:
    return boto3.client(
        "s3",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
    )


@lru_cache
def get_asset_storage_service() -> AssetStorageService:
    return AssetStorageService(get_settings())
