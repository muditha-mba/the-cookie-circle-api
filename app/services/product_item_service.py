"""Product item business logic."""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.repositories.product_item_repository import ProductItemRepository
from app.repositories.product_item_type_repository import ProductItemTypeRepository
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.product_item import (
    ProductItemCreate,
    ProductItemResponse,
    ProductItemUpdate,
)


class ProductItemService:
    """Handles product item operations."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.items = ProductItemRepository(db)
        self.types = ProductItemTypeRepository(db)
        self.suppliers = SupplierRepository(db)

    def create(self, payload: ProductItemCreate) -> ProductItemResponse:
        self._ensure_item_type_exists(payload.item_type_id)
        self._ensure_supplier_exists(payload.primary_supplier_id)
        if self.items.get_by_name(payload.name):
            raise ConflictError("A product item with this name already exists")

        record = self.items.create(
            item_type_id=payload.item_type_id,
            name=payload.name,
            description=payload.description,
            purchase_price=payload.purchase_price,
            purchase_quantity=payload.purchase_quantity,
            purchase_unit=payload.purchase_unit,
            is_active=payload.is_active,
            primary_supplier_id=payload.primary_supplier_id,
        )
        self.db.commit()
        return ProductItemResponse.from_model(record)

    def get(self, item_id: uuid.UUID) -> ProductItemResponse:
        record = self.items.get_by_id(item_id)
        if not record:
            raise NotFoundError("Product item not found")
        return ProductItemResponse.from_model(record)

    def list(
        self,
        params: PaginationParams,
        *,
        item_type_id: uuid.UUID | None = None,
    ) -> PaginatedResponse[ProductItemResponse]:
        if item_type_id is not None and not self.types.get_by_id(item_type_id):
            raise NotFoundError("Product item type not found")

        items, total = self.items.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            item_type_id=item_type_id,
        )
        return PaginatedResponse(
            items=[ProductItemResponse.from_model(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.items.total_pages(total, params.page_size),
        )

    def update(self, item_id: uuid.UUID, payload: ProductItemUpdate) -> ProductItemResponse:
        record = self.items.get_by_id(item_id)
        if not record:
            raise NotFoundError("Product item not found")

        if payload.item_type_id is not None:
            self._ensure_item_type_exists(payload.item_type_id)

        if "primary_supplier_id" in payload.model_dump(exclude_unset=True):
            self._ensure_supplier_exists(payload.primary_supplier_id)

        if payload.name is not None:
            existing = self.items.get_by_name(payload.name)
            if existing and existing.id != record.id:
                raise ConflictError("A product item with this name already exists")

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        record = self.items.update(record, **update_data)
        self.db.commit()
        return ProductItemResponse.from_model(record)

    def delete(self, item_id: uuid.UUID) -> None:
        record = self.items.get_by_id(item_id)
        if not record:
            raise NotFoundError("Product item not found")
        self.items.delete(record)
        self.db.commit()

    def _ensure_item_type_exists(self, type_id: uuid.UUID) -> None:
        if not self.types.get_by_id(type_id):
            raise NotFoundError("Product item type not found")

    def _ensure_supplier_exists(self, supplier_id: uuid.UUID | None) -> None:
        if supplier_id is None:
            return
        if not self.suppliers.get_by_id(supplier_id):
            raise NotFoundError("Supplier not found")
