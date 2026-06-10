"""Shared memory admin routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_current_admin_user, get_shared_memory_service
from app.schemas.shared_memory import SharedMemoryCreate, SharedMemoryResponse, SharedMemoryUpdate
from app.services.shared_memory_service import SharedMemoryService

router = APIRouter(
    prefix="/shared-memories",
    tags=["Shared Memories"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=list[SharedMemoryResponse])
def list_shared_memories(
    service: Annotated[SharedMemoryService, Depends(get_shared_memory_service)],
) -> list[SharedMemoryResponse]:
    """List all shared memories for admin management."""
    return service.list_all()


@router.post("", response_model=SharedMemoryResponse, status_code=status.HTTP_201_CREATED)
def create_shared_memory(
    payload: SharedMemoryCreate,
    service: Annotated[SharedMemoryService, Depends(get_shared_memory_service)],
) -> SharedMemoryResponse:
    """Create a shared memory."""
    return service.create(payload)


@router.get("/{memory_id}", response_model=SharedMemoryResponse)
def get_shared_memory(
    memory_id: uuid.UUID,
    service: Annotated[SharedMemoryService, Depends(get_shared_memory_service)],
) -> SharedMemoryResponse:
    """Get a shared memory by ID."""
    return service.get(memory_id)


@router.patch("/{memory_id}", response_model=SharedMemoryResponse)
def update_shared_memory(
    memory_id: uuid.UUID,
    payload: SharedMemoryUpdate,
    service: Annotated[SharedMemoryService, Depends(get_shared_memory_service)],
) -> SharedMemoryResponse:
    """Update a shared memory."""
    return service.update(memory_id, payload)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shared_memory(
    memory_id: uuid.UUID,
    service: Annotated[SharedMemoryService, Depends(get_shared_memory_service)],
) -> None:
    """Delete a shared memory."""
    service.delete(memory_id)
