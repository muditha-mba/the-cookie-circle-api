"""Purchase receipt bill storage in S3."""

from __future__ import annotations

import logging
import uuid
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

_ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

_MAX_BYTES = 10 * 1024 * 1024
_PRESIGN_EXPIRY_SECONDS = 3600


class PurchaseReceiptStorageService:
    """Presigned upload and secure retrieval for supplier bills."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.s3_enabled)

    def extension_for_content_type(self, content_type: str) -> str:
        normalized = content_type.split(";", 1)[0].strip().lower()
        extension = _ALLOWED_CONTENT_TYPES.get(normalized)
        if not extension:
            raise ValidationError("Bill must be a PDF or image (JPEG, PNG, WebP).")
        return extension

    def build_object_key(self, asset_id: uuid.UUID, extension: str) -> str:
        prefix = self.settings.s3_purchase_receipts_prefix.strip("/")
        normalized = extension.lower().removeprefix(".")
        if normalized not in set(_ALLOWED_CONTENT_TYPES.values()):
            raise ValidationError("Unsupported bill file format.")
        return f"{prefix}/{asset_id}.{normalized}"

    def create_presigned_upload(
        self,
        *,
        asset_id: uuid.UUID,
        content_type: str,
    ) -> dict[str, str | int]:
        if not self.enabled:
            raise ValidationError("Bill upload is not configured. Set AWS S3 credentials.")

        extension = self.extension_for_content_type(content_type)
        object_key = self.build_object_key(asset_id, extension)
        client = self._get_client()

        try:
            upload_url = client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.settings.resolved_s3_bucket_name,
                    "Key": object_key,
                    "ContentType": content_type.split(";", 1)[0].strip().lower(),
                },
                ExpiresIn=_PRESIGN_EXPIRY_SECONDS,
            )
        except (ClientError, BotoCoreError) as exc:
            logger.exception("Failed to generate presigned upload URL for %s", object_key)
            raise ValidationError("Unable to prepare bill upload.") from exc

        return {
            "asset_id": str(asset_id),
            "upload_url": upload_url,
            "extension": extension,
            "expires_in": _PRESIGN_EXPIRY_SECONDS,
        }

    def upload_object(
        self,
        *,
        asset_id: uuid.UUID,
        extension: str,
        body: bytes,
        content_type: str,
    ) -> None:
        if not self.enabled:
            raise ValidationError("Bill upload is not configured. Set AWS S3 credentials.")
        if len(body) > _MAX_BYTES:
            raise ValidationError("Bill file exceeds maximum size (10 MB).")

        object_key = self.build_object_key(asset_id, extension)
        normalized_type = content_type.split(";", 1)[0].strip().lower()
        client = self._get_client()

        try:
            client.put_object(
                Bucket=self.settings.resolved_s3_bucket_name,
                Key=object_key,
                Body=body,
                ContentType=normalized_type,
            )
        except (ClientError, BotoCoreError) as exc:
            logger.exception("Failed to upload bill object %s", object_key)
            raise ValidationError("Unable to store bill file.") from exc

    def get_object_bytes(
        self,
        asset_id: uuid.UUID,
        extension: str,
    ) -> tuple[bytes, str]:
        if not self.enabled:
            raise ValidationError("Bill storage is not configured.")

        object_key = self.build_object_key(asset_id, extension)
        client = self._get_client()

        try:
            response = client.get_object(
                Bucket=self.settings.resolved_s3_bucket_name,
                Key=object_key,
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"NoSuchKey", "404", "NotFound"}:
                raise ValidationError("Bill file not found.") from exc
            logger.exception("Failed to read bill object %s", object_key)
            raise ValidationError("Unable to load bill file.") from exc
        except BotoCoreError as exc:
            logger.exception("Failed to read bill object %s", object_key)
            raise ValidationError("Unable to load bill file.") from exc

        body = response["Body"].read()
        if len(body) > _MAX_BYTES:
            raise ValidationError("Bill file exceeds maximum size (10 MB).")

        content_type = response.get("ContentType") or "application/octet-stream"
        return body, content_type

    def delete_asset(self, asset_id: uuid.UUID, extension: str) -> None:
        if not self.enabled:
            return

        object_key = self.build_object_key(asset_id, extension)
        client = self._get_client()
        try:
            client.delete_object(
                Bucket=self.settings.resolved_s3_bucket_name,
                Key=object_key,
            )
        except (ClientError, BotoCoreError):
            logger.exception("Failed to delete bill object %s", object_key)

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
def get_purchase_receipt_storage_service() -> PurchaseReceiptStorageService:
    return PurchaseReceiptStorageService(get_settings())
