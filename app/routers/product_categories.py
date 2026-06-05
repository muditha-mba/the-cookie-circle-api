"""Product category routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.database.session import get_db
from app.dependencies.admin import get_current_admin_user
from app.schemas.product_category import (
    ProductCategoryCreate,
    ProductCategoryResponse,
    ProductCategoryUpdate,
)
from app.services.product_category_service import ProductCategoryService
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/product-categories",
    tags=["Product Categories"],
    dependencies=[Depends(get_current_admin_user)],
)


def get_product_category_service(db: Annotated[Session, Depends(get_db)]) -> ProductCategoryService:
    return ProductCategoryService(db)


@router.get("", response_model=list[ProductCategoryResponse])
def list_product_categories(
    service: Annotated[ProductCategoryService, Depends(get_product_category_service)],
) -> list[ProductCategoryResponse]:
    return service.list()


@router.post("", response_model=ProductCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_product_category(
    payload: ProductCategoryCreate,
    service: Annotated[ProductCategoryService, Depends(get_product_category_service)],
) -> ProductCategoryResponse:
    return service.create(payload)


@router.patch("/{category_id}", response_model=ProductCategoryResponse)
def update_product_category(
    category_id: uuid.UUID,
    payload: ProductCategoryUpdate,
    service: Annotated[ProductCategoryService, Depends(get_product_category_service)],
) -> ProductCategoryResponse:
    return service.update(category_id, payload)
