"""Collection routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.admin_access import can_view_financials
from app.dependencies.admin import get_collection_service, get_current_admin_user
from app.models.user import User
from app.schemas.collection import (
    CollectionCreate,
    CollectionDetailResponse,
    CollectionListParams,
    CollectionSummaryResponse,
    CollectionUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.services.collection_service import CollectionService
from app.services.financial_redaction import redact_collection_detail, redact_collection_list

router = APIRouter(
    prefix="/collections",
    tags=["Collections"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[CollectionSummaryResponse])
def list_collections(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    params: Annotated[CollectionListParams, Depends()],
    service: Annotated[CollectionService, Depends(get_collection_service)],
) -> PaginatedResponse[CollectionSummaryResponse]:
    """List collections with pagination."""
    result = service.list(params)
    if not can_view_financials(current_user):
        return redact_collection_list(result)
    return result


@router.post("", response_model=CollectionDetailResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    payload: CollectionCreate,
    service: Annotated[CollectionService, Depends(get_collection_service)],
) -> CollectionDetailResponse:
    """Create a collection with products and attached charges."""
    result = service.create(payload)
    if not can_view_financials(current_user):
        return redact_collection_detail(result)
    return result


@router.get("/{collection_id}", response_model=CollectionDetailResponse)
def get_collection(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    collection_id: uuid.UUID,
    service: Annotated[CollectionService, Depends(get_collection_service)],
) -> CollectionDetailResponse:
    """Get collection detail with full cost breakdown."""
    result = service.get(collection_id)
    if not can_view_financials(current_user):
        return redact_collection_detail(result)
    return result


@router.patch("/{collection_id}", response_model=CollectionDetailResponse)
def update_collection(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    collection_id: uuid.UUID,
    payload: CollectionUpdate,
    service: Annotated[CollectionService, Depends(get_collection_service)],
) -> CollectionDetailResponse:
    """Update a collection."""
    result = service.update(collection_id, payload)
    if not can_view_financials(current_user):
        return redact_collection_detail(result)
    return result


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: uuid.UUID,
    service: Annotated[CollectionService, Depends(get_collection_service)],
) -> None:
    """Delete a collection."""
    service.delete(collection_id)
