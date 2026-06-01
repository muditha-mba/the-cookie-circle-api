"""Collection routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_collection_service, get_current_admin_user
from app.schemas.collection import (
    CollectionCostBreakdown,
    CollectionCostPreviewRequest,
    CollectionCreate,
    CollectionDetailResponse,
    CollectionSummaryResponse,
    CollectionUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.collection_service import CollectionService

router = APIRouter(
    prefix="/collections",
    tags=["Collections"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[CollectionSummaryResponse])
def list_collections(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[CollectionService, Depends(get_collection_service)],
) -> PaginatedResponse[CollectionSummaryResponse]:
    """List collections with pagination."""
    return service.list(params)


@router.post("/cost-preview", response_model=CollectionCostBreakdown)
def preview_collection_cost(
    payload: CollectionCostPreviewRequest,
    service: Annotated[CollectionService, Depends(get_collection_service)],
) -> CollectionCostBreakdown:
    """Calculate collection cost breakdown without saving."""
    return service.preview_cost(payload)


@router.post("", response_model=CollectionDetailResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionCreate,
    service: Annotated[CollectionService, Depends(get_collection_service)],
) -> CollectionDetailResponse:
    """Create a collection with products and attached charges."""
    return service.create(payload)


@router.get("/{collection_id}", response_model=CollectionDetailResponse)
def get_collection(
    collection_id: uuid.UUID,
    service: Annotated[CollectionService, Depends(get_collection_service)],
) -> CollectionDetailResponse:
    """Get collection detail with full cost breakdown."""
    return service.get(collection_id)


@router.patch("/{collection_id}", response_model=CollectionDetailResponse)
def update_collection(
    collection_id: uuid.UUID,
    payload: CollectionUpdate,
    service: Annotated[CollectionService, Depends(get_collection_service)],
) -> CollectionDetailResponse:
    """Update a collection."""
    return service.update(collection_id, payload)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: uuid.UUID,
    service: Annotated[CollectionService, Depends(get_collection_service)],
) -> None:
    """Delete a collection."""
    service.delete(collection_id)
