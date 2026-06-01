"""Product routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_current_admin_user, get_product_service
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.product import (
    ProductCostBreakdown,
    ProductCostPreviewRequest,
    ProductCreate,
    ProductDetailResponse,
    ProductSummaryResponse,
    ProductUpdate,
)
from app.services.product_service import ProductService

router = APIRouter(
    prefix="/products",
    tags=["Products"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[ProductSummaryResponse])
def list_products(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[ProductService, Depends(get_product_service)],
) -> PaginatedResponse[ProductSummaryResponse]:
    """List products with pagination."""
    return service.list(params)


@router.post("/cost-preview", response_model=ProductCostBreakdown)
def preview_product_cost(
    payload: ProductCostPreviewRequest,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductCostBreakdown:
    """Calculate product cost breakdown without saving."""
    return service.preview_cost(payload)


@router.post("", response_model=ProductDetailResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductDetailResponse:
    """Create a product with recipe and attached charges."""
    return service.create(payload)


@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product(
    product_id: uuid.UUID,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductDetailResponse:
    """Get product detail with full cost breakdown."""
    return service.get(product_id)


@router.patch("/{product_id}", response_model=ProductDetailResponse)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductDetailResponse:
    """Update a product."""
    return service.update(product_id, payload)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: uuid.UUID,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> None:
    """Delete a product."""
    service.delete(product_id)
