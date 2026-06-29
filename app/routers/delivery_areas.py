"""Delivery area routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_current_admin_user, get_delivery_area_service
from app.schemas.delivery_area import (
    DeliveryAreaCreate,
    DeliveryAreaResponse,
    DeliveryAreaUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.delivery_area_service import DeliveryAreaService

router = APIRouter(
    prefix="/delivery-areas",
    tags=["Delivery Areas"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[DeliveryAreaResponse])
def list_delivery_areas(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[DeliveryAreaService, Depends(get_delivery_area_service)],
) -> PaginatedResponse[DeliveryAreaResponse]:
    """List delivery areas with pagination."""
    return service.list(params)


@router.get("/active", response_model=list[DeliveryAreaResponse])
def list_active_delivery_areas(
    service: Annotated[DeliveryAreaService, Depends(get_delivery_area_service)],
) -> list[DeliveryAreaResponse]:
    """List active delivery areas for order forms."""
    return service.list_active()


@router.post("", response_model=DeliveryAreaResponse, status_code=status.HTTP_201_CREATED)
def create_delivery_area(
    payload: DeliveryAreaCreate,
    service: Annotated[DeliveryAreaService, Depends(get_delivery_area_service)],
) -> DeliveryAreaResponse:
    """Create a delivery area."""
    return service.create(payload)


@router.get("/{area_id}", response_model=DeliveryAreaResponse)
def get_delivery_area(
    area_id: uuid.UUID,
    service: Annotated[DeliveryAreaService, Depends(get_delivery_area_service)],
) -> DeliveryAreaResponse:
    """Get a delivery area by ID."""
    return service.get(area_id)


@router.patch("/{area_id}", response_model=DeliveryAreaResponse)
def update_delivery_area(
    area_id: uuid.UUID,
    payload: DeliveryAreaUpdate,
    service: Annotated[DeliveryAreaService, Depends(get_delivery_area_service)],
) -> DeliveryAreaResponse:
    """Update a delivery area."""
    return service.update(area_id, payload)


@router.delete("/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery_area(
    area_id: uuid.UUID,
    service: Annotated[DeliveryAreaService, Depends(get_delivery_area_service)],
) -> None:
    """Delete a delivery area."""
    service.delete(area_id)
