"""Product item type routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import (
    get_current_admin_user,
    get_product_item_type_service,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.product_item_type import (
    ProductItemTypeCreate,
    ProductItemTypeResponse,
    ProductItemTypeUpdate,
)
from app.services.product_item_type_service import ProductItemTypeService

router = APIRouter(
    prefix="/product-item-types",
    tags=["Product Item Types"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get("", response_model=PaginatedResponse[ProductItemTypeResponse])
def list_product_item_types(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[ProductItemTypeService, Depends(get_product_item_type_service)],
) -> PaginatedResponse[ProductItemTypeResponse]:
    """List product item types with pagination."""
    return service.list(params)


@router.post(
    "",
    response_model=ProductItemTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_item_type(
    payload: ProductItemTypeCreate,
    service: Annotated[ProductItemTypeService, Depends(get_product_item_type_service)],
) -> ProductItemTypeResponse:
    """Create a product item type."""
    return service.create(payload)


@router.get("/{type_id}", response_model=ProductItemTypeResponse)
def get_product_item_type(
    type_id: uuid.UUID,
    service: Annotated[ProductItemTypeService, Depends(get_product_item_type_service)],
) -> ProductItemTypeResponse:
    """Get a product item type by ID."""
    return service.get(type_id)


@router.patch("/{type_id}", response_model=ProductItemTypeResponse)
def update_product_item_type(
    type_id: uuid.UUID,
    payload: ProductItemTypeUpdate,
    service: Annotated[ProductItemTypeService, Depends(get_product_item_type_service)],
) -> ProductItemTypeResponse:
    """Update a product item type."""
    return service.update(type_id, payload)


@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_item_type(
    type_id: uuid.UUID,
    service: Annotated[ProductItemTypeService, Depends(get_product_item_type_service)],
) -> None:
    """Delete a product item type."""
    service.delete(type_id)
