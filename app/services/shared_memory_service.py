"""Shared memory business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.storage_paths import StorageAssetCategory
from app.models.shared_memory import SharedMemory
from app.repositories.shared_memory_repository import SharedMemoryRepository
from app.schemas.shared_memory import (
    ClientSharedMemoriesResponse,
    ClientSharedMemoryItem,
    SharedMemoryCreate,
    SharedMemoryResponse,
    SharedMemoryUpdate,
    platform_label,
)
from app.services.business_setting_service import BusinessSettingService
from app.services.storage.asset_storage_service import (
    AssetStorageService,
    get_asset_storage_service,
)


class SharedMemoryService:
    """Handles shared memory CRUD and public listing."""

    def __init__(
        self,
        db: Session,
        storage: AssetStorageService | None = None,
    ) -> None:
        self.db = db
        self.memories = SharedMemoryRepository(db)
        self.storage = storage or get_asset_storage_service()

    def create(self, payload: SharedMemoryCreate) -> SharedMemoryResponse:
        memory_id = uuid.uuid4()
        preview_image_url = self._persist_preview_image(
            memory_id=memory_id,
            source_url=payload.preview_image_url,
            previous_url=None,
        )

        memory = SharedMemory(
            id=memory_id,
            title=payload.title,
            preview_image_url=preview_image_url,
            post_url=payload.post_url,
            platform=payload.platform,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
        self.memories.create(memory)
        self.db.commit()
        self.db.refresh(memory)
        return self._to_response(memory)

    def get(self, memory_id: uuid.UUID) -> SharedMemoryResponse:
        memory = self.memories.get_by_id(memory_id)
        if not memory:
            raise NotFoundError("Shared memory not found")
        return self._to_response(memory)

    def list_all(self) -> list[SharedMemoryResponse]:
        return [self._to_response(item) for item in self.memories.list_all()]

    def list_active_public(self) -> ClientSharedMemoriesResponse:
        section_enabled = BusinessSettingService(self.db).get_shared_memories_section_enabled()
        posts: list[ClientSharedMemoryItem] = []

        if section_enabled:
            posts = [
                ClientSharedMemoryItem(
                    id=item.id,
                    title=item.title,
                    preview_image_url=item.preview_image_url,
                    post_url=item.post_url,
                    platform=item.platform,  # type: ignore[arg-type]
                    platform_label=platform_label(item.platform),  # type: ignore[arg-type]
                    sort_order=item.sort_order,
                )
                for item in self.memories.list_active()
            ]

        return ClientSharedMemoriesResponse(section_enabled=section_enabled, posts=posts)

    def update(self, memory_id: uuid.UUID, payload: SharedMemoryUpdate) -> SharedMemoryResponse:
        memory = self.memories.get_by_id(memory_id)
        if not memory:
            raise NotFoundError("Shared memory not found")

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        previous_preview_url = memory.preview_image_url
        if "preview_image_url" in update_data:
            update_data["preview_image_url"] = self._persist_preview_image(
                memory_id=memory.id,
                source_url=update_data["preview_image_url"],
                previous_url=previous_preview_url,
            )

        for field, value in update_data.items():
            setattr(memory, field, value)

        self.db.commit()
        self.db.refresh(memory)
        return self._to_response(memory)

    def delete(self, memory_id: uuid.UUID) -> None:
        memory = self.memories.get_by_id(memory_id)
        if not memory:
            raise NotFoundError("Shared memory not found")

        self.storage.delete_managed_url(memory.preview_image_url)
        self.memories.delete(memory)
        self.db.commit()

    def _persist_preview_image(
        self,
        memory_id: uuid.UUID,
        source_url: str,
        previous_url: str | None,
    ) -> str:
        trimmed = source_url.strip()
        if not trimmed:
            raise ValidationError("Preview image URL is required.")

        if self.storage.is_managed_media_url(trimmed):
            if previous_url and previous_url != trimmed:
                self.storage.delete_managed_url(previous_url)
            return trimmed

        if not self.storage.enabled:
            raise ValidationError(
                "Image storage is not configured. Set AWS credentials for this environment.",
            )

        cached_url = self.storage.cache_image_from_url(
            trimmed,
            StorageAssetCategory.SHARED_MEMORIES,
            memory_id,
        )
        if previous_url and previous_url != cached_url:
            self.storage.delete_managed_url(previous_url)
        return cached_url

    def _to_response(self, memory: SharedMemory) -> SharedMemoryResponse:
        return SharedMemoryResponse(
            id=memory.id,
            title=memory.title,
            preview_image_url=memory.preview_image_url,
            post_url=memory.post_url,
            platform=memory.platform,  # type: ignore[arg-type]
            platform_label=platform_label(memory.platform),  # type: ignore[arg-type]
            sort_order=memory.sort_order,
            is_active=memory.is_active,
        )
