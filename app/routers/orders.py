"""Order routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.admin_access import can_view_financials
from app.dependencies.admin import get_current_admin_user, get_order_service
from app.models.user import User
from app.schemas.order import (
    OrderCreate,
    OrderDetailResponse,
    OrderPreviewRequest,
    OrderPreviewResponse,
    OrderSummaryResponse,
    OrderUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.financial_redaction import (
    redact_order_detail,
    redact_order_list,
    redact_order_preview,
)
from app.services.order_service import OrderService

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[OrderSummaryResponse])
def list_orders(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[OrderService, Depends(get_order_service)],
) -> PaginatedResponse[OrderSummaryResponse]:
    """List orders with pagination."""
    result = service.list(params)
    if not can_view_financials(current_user):
        return redact_order_list(result)
    return result


@router.post("/preview", response_model=OrderPreviewResponse)
def preview_order(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    payload: OrderPreviewRequest,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderPreviewResponse:
    """Preview order financials without saving."""
    result = service.preview(payload)
    if not can_view_financials(current_user):
        return redact_order_preview(result)
    return result


@router.post("", response_model=OrderDetailResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    payload: OrderCreate,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderDetailResponse:
    """Create an order with collection snapshots."""
    result = service.create(payload)
    if not can_view_financials(current_user):
        return redact_order_detail(result)
    return result


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    order_id: uuid.UUID,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderDetailResponse:
    """Get order detail."""
    result = service.get(order_id)
    if not can_view_financials(current_user):
        return redact_order_detail(result)
    return result


@router.patch("/{order_id}", response_model=OrderDetailResponse)
def update_order(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    order_id: uuid.UUID,
    payload: OrderUpdate,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderDetailResponse:
    """Update an order."""
    result = service.update(order_id, payload)
    if not can_view_financials(current_user):
        return redact_order_detail(result)
    return result


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: uuid.UUID,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> None:
    """Delete an order."""
    service.delete(order_id)
