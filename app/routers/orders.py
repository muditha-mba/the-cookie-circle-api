"""Order routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_current_admin_user, get_order_service
from app.schemas.order import (
    OrderCreate,
    OrderDetailResponse,
    OrderPreviewRequest,
    OrderPreviewResponse,
    OrderSummaryResponse,
    OrderUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.order_service import OrderService

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[OrderSummaryResponse])
def list_orders(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[OrderService, Depends(get_order_service)],
) -> PaginatedResponse[OrderSummaryResponse]:
    """List orders with pagination."""
    return service.list(params)


@router.post("/preview", response_model=OrderPreviewResponse)
def preview_order(
    payload: OrderPreviewRequest,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderPreviewResponse:
    """Preview order financials without saving."""
    return service.preview(payload)


@router.post("", response_model=OrderDetailResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderDetailResponse:
    """Create an order with collection snapshots."""
    return service.create(payload)


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order(
    order_id: uuid.UUID,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderDetailResponse:
    """Get order detail."""
    return service.get(order_id)


@router.patch("/{order_id}", response_model=OrderDetailResponse)
def update_order(
    order_id: uuid.UUID,
    payload: OrderUpdate,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderDetailResponse:
    """Update an order."""
    return service.update(order_id, payload)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: uuid.UUID,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> None:
    """Delete an order."""
    service.delete(order_id)
