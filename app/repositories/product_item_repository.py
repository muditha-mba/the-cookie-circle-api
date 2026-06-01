"""Product item data access repository."""

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.product_item import ProductItem
from app.models.product_item_type import ProductItemType


class ProductItemRepository:
    """Repository for product item persistence."""

    SORTABLE_COLUMNS = {
        "name": ProductItem.name,
        "created_at": ProductItem.created_at,
        "is_active": ProductItem.is_active,
        "purchase_price": ProductItem.purchase_price,
        "purchase_quantity": ProductItem.purchase_quantity,
        "cost_per_unit": ProductItem.purchase_price / ProductItem.purchase_quantity,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_ids_with_type(self, ids: list[uuid.UUID]) -> list[ProductItem]:
        if not ids:
            return []
        stmt = (
            select(ProductItem)
            .options(joinedload(ProductItem.item_type))
            .where(ProductItem.id.in_(ids))
        )
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, item_id: uuid.UUID) -> ProductItem | None:
        stmt = (
            select(ProductItem)
            .options(joinedload(ProductItem.item_type))
            .where(ProductItem.id == item_id)
        )
        return self.db.scalar(stmt)

    def get_by_name(self, name: str) -> ProductItem | None:
        stmt = (
            select(ProductItem)
            .options(joinedload(ProductItem.item_type))
            .where(func.lower(ProductItem.name) == name.strip().lower())
        )
        return self.db.scalar(stmt)

    def create(
        self,
        *,
        item_type_id: uuid.UUID,
        name: str,
        description: str | None,
        purchase_price,
        purchase_quantity,
        purchase_unit: str,
        is_active: bool,
    ) -> ProductItem:
        record = ProductItem(
            item_type_id=item_type_id,
            name=name.strip(),
            description=description,
            purchase_price=purchase_price,
            purchase_quantity=purchase_quantity,
            purchase_unit=purchase_unit.strip().lower(),
            is_active=is_active,
        )
        self.db.add(record)
        self.db.flush()
        return self._reload(record.id)

    def update(self, record: ProductItem, **fields) -> ProductItem:
        for key, value in fields.items():
            if value is None:
                continue
            if key == "name":
                setattr(record, key, value.strip())
            elif key == "purchase_unit":
                setattr(record, key, value.strip().lower())
            else:
                setattr(record, key, value)
        self.db.add(record)
        self.db.flush()
        return self._reload(record.id)

    def delete(self, record: ProductItem) -> None:
        self.db.delete(record)

    def _reload(self, item_id: uuid.UUID) -> ProductItem:
        item = self.get_by_id(item_id)
        if item is None:
            raise RuntimeError("Failed to reload product item")
        return item

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
        item_type_id: uuid.UUID | None = None,
    ) -> tuple[list[ProductItem], int]:
        stmt = select(ProductItem).options(joinedload(ProductItem.item_type))
        count_stmt = select(func.count()).select_from(ProductItem)

        filters = []
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    ProductItem.name.ilike(pattern),
                    ProductItem.description.ilike(pattern),
                    ProductItem.purchase_unit.ilike(pattern),
                ),
            )
        if item_type_id is not None:
            filters.append(ProductItem.item_type_id == item_type_id)

        for filter_clause in filters:
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total = int(self.db.scalar(count_stmt) or 0)

        sort_column = self.SORTABLE_COLUMNS.get(sort_by, ProductItem.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)

        items = list(self.db.scalars(stmt).unique().all())
        return items, total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)

    def item_type_exists(self, type_id: uuid.UUID) -> bool:
        stmt = select(ProductItemType.id).where(ProductItemType.id == type_id)
        return self.db.scalar(stmt) is not None
