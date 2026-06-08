"""Product item type data access repository."""

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.product_item import ProductItem
from app.models.product_item_type import ProductItemType


class ProductItemTypeRepository:
    """Repository for product item type persistence."""

    SORTABLE_COLUMNS = {
        "name": ProductItemType.name,
        "created_at": ProductItemType.created_at,
        "is_active": ProductItemType.is_active,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, type_id: uuid.UUID) -> ProductItemType | None:
        return self.db.get(ProductItemType, type_id)

    def get_by_name(self, name: str) -> ProductItemType | None:
        stmt = select(ProductItemType).where(
            func.lower(ProductItemType.name) == name.strip().lower(),
        )
        return self.db.scalar(stmt)

    def count_items_for_type(self, type_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(ProductItem).where(
            ProductItem.item_type_id == type_id,
        )
        return int(self.db.scalar(stmt) or 0)

    def create(self, *, name: str, description: str | None, is_active: bool) -> ProductItemType:
        record = ProductItemType(
            name=name.strip(),
            description=description,
            is_active=is_active,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def update(
        self,
        record: ProductItemType,
        *,
        name: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> ProductItemType:
        if name is not None:
            record.name = name.strip()
        if description is not None:
            record.description = description
        if is_active is not None:
            record.is_active = is_active
        self.db.add(record)
        return record

    def delete(self, record: ProductItemType) -> None:
        self.db.delete(record)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[ProductItemType], int]:
        stmt = select(ProductItemType)
        count_stmt = select(func.count()).select_from(ProductItemType)

        if search:
            pattern = f"%{search.strip()}%"
            filter_clause = or_(
                ProductItemType.name.ilike(pattern),
                ProductItemType.description.ilike(pattern),
            )
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total = int(self.db.scalar(count_stmt) or 0)

        sort_column = self.SORTABLE_COLUMNS.get(sort_by, ProductItemType.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)

        items = list(self.db.scalars(stmt).all())
        return items, total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)
