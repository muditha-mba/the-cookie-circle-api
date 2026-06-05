"""Product category data access."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.product_category import ProductCategory


class ProductCategoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, category_id: uuid.UUID) -> ProductCategory | None:
        return self.db.get(ProductCategory, category_id)

    def get_by_ids(self, ids: list[uuid.UUID]) -> list[ProductCategory]:
        if not ids:
            return []
        stmt = select(ProductCategory).where(ProductCategory.id.in_(ids))
        return list(self.db.scalars(stmt).all())

    def list_active(self) -> list[ProductCategory]:
        stmt = (
            select(ProductCategory)
            .where(ProductCategory.is_active.is_(True))
            .order_by(ProductCategory.sort_order, ProductCategory.name)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_name(self, name: str) -> ProductCategory | None:
        stmt = select(ProductCategory).where(
            func.lower(ProductCategory.name) == name.strip().lower(),
        )
        return self.db.scalar(stmt)
