"""Product item routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.admin_access import can_view_financials
from app.dependencies.admin import get_current_admin_user, get_product_item_service
from app.dependencies.permissions import require_super_admin
from app.models.user import User
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.product_item import (
    ProductItemCreate,
    ProductItemResponse,
    ProductItemUpdate,
)
from app.services.financial_redaction import redact_product_item, redact_product_item_list
from app.services.product_item_service import ProductItemService

router = APIRouter(
    prefix="/product-items",
    tags=["Product Items"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[ProductItemResponse])
def list_product_items(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[ProductItemService, Depends(get_product_item_service)],
    item_type_id: uuid.UUID | None = Query(default=None),
) -> PaginatedResponse[ProductItemResponse]:
    """List product items with pagination."""
    result = service.list(params, item_type_id=item_type_id)
    if not can_view_financials(current_user):
        return redact_product_item_list(result)
    return result


@router.post("", response_model=ProductItemResponse, status_code=status.HTTP_201_CREATED)
def create_product_item(
    _: Annotated[User, Depends(require_super_admin)],
    payload: ProductItemCreate,
    service: Annotated[ProductItemService, Depends(get_product_item_service)],
) -> ProductItemResponse:
    """Create a product item."""
    return service.create(payload)


@router.get("/{item_id}", response_model=ProductItemResponse)
def get_product_item(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    item_id: uuid.UUID,
    service: Annotated[ProductItemService, Depends(get_product_item_service)],
) -> ProductItemResponse:
    """Get a product item by ID."""
    result = service.get(item_id)
    if not can_view_financials(current_user):
        return redact_product_item(result)
    return result


@router.patch("/{item_id}", response_model=ProductItemResponse)
def update_product_item(
    _: Annotated[User, Depends(require_super_admin)],
    item_id: uuid.UUID,
    payload: ProductItemUpdate,
    service: Annotated[ProductItemService, Depends(get_product_item_service)],
) -> ProductItemResponse:
    """Update a product item."""
    return service.update(item_id, payload)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_item(
    _: Annotated[User, Depends(require_super_admin)],
    item_id: uuid.UUID,
    service: Annotated[ProductItemService, Depends(get_product_item_service)],
) -> None:
    """Delete a product item."""
    service.delete(item_id)
