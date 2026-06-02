"""Collection package routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import (
    get_collection_package_service,
    get_current_admin_user,
)
from app.schemas.collection_package import (
    CollectionPackageCreate,
    CollectionPackageResponse,
    CollectionPackageUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.collection_package_service import CollectionPackageService

router = APIRouter(
    prefix="/collection-packages",
    tags=["Collection Packages"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[CollectionPackageResponse])
def list_collection_packages(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[CollectionPackageService, Depends(get_collection_package_service)],
) -> PaginatedResponse[CollectionPackageResponse]:
    """List collection packages with pagination."""
    return service.list(params)


@router.post("", response_model=CollectionPackageResponse, status_code=status.HTTP_201_CREATED)
def create_collection_package(
    payload: CollectionPackageCreate,
    service: Annotated[CollectionPackageService, Depends(get_collection_package_service)],
) -> CollectionPackageResponse:
    """Create a collection package."""
    return service.create(payload)


@router.get("/{package_id}", response_model=CollectionPackageResponse)
def get_collection_package(
    package_id: uuid.UUID,
    service: Annotated[CollectionPackageService, Depends(get_collection_package_service)],
) -> CollectionPackageResponse:
    """Get a collection package by ID."""
    return service.get(package_id)


@router.patch("/{package_id}", response_model=CollectionPackageResponse)
def update_collection_package(
    package_id: uuid.UUID,
    payload: CollectionPackageUpdate,
    service: Annotated[CollectionPackageService, Depends(get_collection_package_service)],
) -> CollectionPackageResponse:
    """Update a collection package."""
    return service.update(package_id, payload)


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection_package(
    package_id: uuid.UUID,
    service: Annotated[CollectionPackageService, Depends(get_collection_package_service)],
) -> None:
    """Delete a collection package."""
    service.delete(package_id)
