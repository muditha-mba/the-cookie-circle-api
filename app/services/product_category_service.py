"""Product category business logic."""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.product_category import ProductCategory
from app.repositories.product_category_repository import ProductCategoryRepository
from app.schemas.product_category import (
    ProductCategoryCreate,
    ProductCategoryResponse,
    ProductCategoryUpdate,
)


class ProductCategoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.categories = ProductCategoryRepository(db)

    def list(self) -> list[ProductCategoryResponse]:
        rows = self.categories.list_active()
        return [ProductCategoryResponse.model_validate(row) for row in rows]

    def create(self, payload: ProductCategoryCreate) -> ProductCategoryResponse:
        if self.categories.get_by_name(payload.name):
            raise ConflictError("A category with this name already exists")
        category = ProductCategory(
            code=payload.code.upper(),
            name=payload.name,
            description=payload.description,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return ProductCategoryResponse.model_validate(category)

    def update(
        self,
        category_id: uuid.UUID,
        payload: ProductCategoryUpdate,
    ) -> ProductCategoryResponse:
        category = self.categories.get_by_id(category_id)
        if not category:
            raise NotFoundError("Product category not found")

        if not payload.model_dump(exclude_unset=True):
            raise ValidationError("No fields provided to update")

        if payload.name is not None:
            existing = self.categories.get_by_name(payload.name)
            if existing and existing.id != category.id:
                raise ConflictError("A category with this name already exists")
            category.name = payload.name
        if payload.description is not None:
            category.description = payload.description
        if payload.sort_order is not None:
            category.sort_order = payload.sort_order
        if payload.is_active is not None:
            category.is_active = payload.is_active

        self.db.commit()
        self.db.refresh(category)
        return ProductCategoryResponse.model_validate(category)
