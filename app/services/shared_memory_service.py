"""Shared memory business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
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


class SharedMemoryService:
    """Handles shared memory CRUD and public listing."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.memories = SharedMemoryRepository(db)

    def create(self, payload: SharedMemoryCreate) -> SharedMemoryResponse:
        memory = SharedMemory(
            title=payload.title,
            preview_image_url=payload.preview_image_url,
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

        for field, value in update_data.items():
            setattr(memory, field, value)

        self.db.commit()
        self.db.refresh(memory)
        return self._to_response(memory)

    def delete(self, memory_id: uuid.UUID) -> None:
        memory = self.memories.get_by_id(memory_id)
        if not memory:
            raise NotFoundError("Shared memory not found")
        self.memories.delete(memory)
        self.db.commit()

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
