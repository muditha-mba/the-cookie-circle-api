"""Product data access repository."""

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.product import Product
from app.models.product_recipe_line import ProductRecipeLine
from app.utils.search import ilike_contains


class ProductRepository:
    """Repository for product persistence."""

    SORTABLE_COLUMNS = {
        "name": Product.name,
        "created_at": Product.created_at,
        "is_active": Product.is_active,
        "selling_price": Product.selling_price,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def _detail_options(self):
        return (
            selectinload(Product.recipe_lines).joinedload(ProductRecipeLine.product_item),
        )

    def get_for_costing_by_ids(self, ids: list[uuid.UUID]) -> list[Product]:
        if not ids:
            return []
        stmt = (
            select(Product)
            .options(*self._detail_options())
            .where(Product.id.in_(ids))
        )
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, product_id: uuid.UUID) -> Product | None:
        stmt = (
            select(Product)
            .options(*self._detail_options())
            .where(Product.id == product_id)
        )
        return self.db.scalar(stmt)

    def get_by_name(self, name: str) -> Product | None:
        stmt = select(Product).where(func.lower(Product.name) == name.strip().lower())
        return self.db.scalar(stmt)

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.flush()
        return self.get_by_id(product.id)  # type: ignore[return-value]

    def delete(self, product: Product) -> None:
        self.db.delete(product)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Product], int]:
        stmt = select(Product)
        count_stmt = select(func.count()).select_from(Product)

        if search:
            pattern, escape = ilike_contains(search)
            filter_clause = or_(
                Product.name.ilike(pattern, escape=escape),
                Product.description.ilike(pattern, escape=escape),
            )
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, Product.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)

        return list(self.db.scalars(stmt).all()), total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)
