"""Product item type business logic."""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories.product_item_type_repository import ProductItemTypeRepository
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.product_item_type import (
    ProductItemTypeCreate,
    ProductItemTypeResponse,
    ProductItemTypeUpdate,
)


class ProductItemTypeService:
    """Handles product item type operations."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.types = ProductItemTypeRepository(db)

    def create(self, payload: ProductItemTypeCreate) -> ProductItemTypeResponse:
        if self.types.get_by_name(payload.name):
            raise ConflictError("A product item type with this name already exists")

        record = self.types.create(
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
        )
        self.db.commit()
        self.db.refresh(record)
        return ProductItemTypeResponse.model_validate(record)

    def get(self, type_id: uuid.UUID) -> ProductItemTypeResponse:
        record = self.types.get_by_id(type_id)
        if not record:
            raise NotFoundError("Product item type not found")
        return ProductItemTypeResponse.model_validate(record)

    def list(self, params: PaginationParams) -> PaginatedResponse[ProductItemTypeResponse]:
        items, total = self.types.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        return PaginatedResponse(
            items=[ProductItemTypeResponse.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.types.total_pages(total, params.page_size),
        )

    def update(
        self,
        type_id: uuid.UUID,
        payload: ProductItemTypeUpdate,
    ) -> ProductItemTypeResponse:
        record = self.types.get_by_id(type_id)
        if not record:
            raise NotFoundError("Product item type not found")

        if payload.name is not None:
            existing = self.types.get_by_name(payload.name)
            if existing and existing.id != record.id:
                raise ConflictError("A product item type with this name already exists")

        self.types.update(
            record,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
        )
        self.db.commit()
        self.db.refresh(record)
        return ProductItemTypeResponse.model_validate(record)

    def delete(self, type_id: uuid.UUID) -> None:
        record = self.types.get_by_id(type_id)
        if not record:
            raise NotFoundError("Product item type not found")

        if self.types.count_items_for_type(type_id) > 0:
            raise ConflictError(
                "Cannot delete a product item type that has product items assigned",
            )

        self.types.delete(record)
        self.db.commit()
