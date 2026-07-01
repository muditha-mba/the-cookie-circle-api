"""Product routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.admin_access import can_view_financials
from app.dependencies.admin import get_current_admin_user, get_product_service
from app.dependencies.permissions import require_super_admin
from app.models.user import User
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.product import (
    ProductCostBreakdown,
    ProductCostPreviewRequest,
    ProductCreate,
    ProductDetailResponse,
    ProductSummaryResponse,
    ProductUpdate,
)
from app.services.financial_redaction import redact_product_detail, redact_product_list
from app.services.product_service import ProductService

router = APIRouter(
    prefix="/products",
    tags=["Products"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[ProductSummaryResponse])
def list_products(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[ProductService, Depends(get_product_service)],
) -> PaginatedResponse[ProductSummaryResponse]:
    """List products with pagination."""
    result = service.list(params)
    if not can_view_financials(current_user):
        return redact_product_list(result)
    return result


@router.post("/cost-preview", response_model=ProductCostBreakdown)
def preview_product_cost(
    _: Annotated[User, Depends(require_super_admin)],
    payload: ProductCostPreviewRequest,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductCostBreakdown:
    """Calculate product cost breakdown without saving."""
    return service.preview_cost(payload)


@router.post("", response_model=ProductDetailResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    payload: ProductCreate,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductDetailResponse:
    """Create a product with recipe and attached charges."""
    result = service.create(payload)
    if not can_view_financials(current_user):
        return redact_product_detail(result)
    return result


@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    product_id: uuid.UUID,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductDetailResponse:
    """Get product detail with full cost breakdown."""
    result = service.get(product_id)
    if not can_view_financials(current_user):
        return redact_product_detail(result)
    return result


@router.patch("/{product_id}", response_model=ProductDetailResponse)
def update_product(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    product_id: uuid.UUID,
    payload: ProductUpdate,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductDetailResponse:
    """Update a product."""
    result = service.update(product_id, payload)
    if not can_view_financials(current_user):
        return redact_product_detail(result)
    return result


@router.post(
    "/{product_id}/duplicate",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_product(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    product_id: uuid.UUID,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductDetailResponse:
    """Duplicate a product and its recipe lines under a new unique name."""
    result = service.duplicate(product_id)
    if not can_view_financials(current_user):
        return redact_product_detail(result)
    return result


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: uuid.UUID,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> None:
    """Delete a product."""
    service.delete(product_id)
