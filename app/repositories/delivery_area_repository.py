"""Delivery area data access repository."""

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.delivery_area import DeliveryArea


class DeliveryAreaRepository:
    """Repository for delivery area persistence."""

    SORTABLE_COLUMNS = {
        "name": DeliveryArea.name,
        "created_at": DeliveryArea.created_at,
        "is_active": DeliveryArea.is_active,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, area_id: uuid.UUID) -> DeliveryArea | None:
        return self.db.get(DeliveryArea, area_id)

    def get_by_name(self, name: str) -> DeliveryArea | None:
        stmt = select(DeliveryArea).where(func.lower(DeliveryArea.name) == name.strip().lower())
        return self.db.scalar(stmt)

    def create(self, area: DeliveryArea) -> DeliveryArea:
        self.db.add(area)
        self.db.flush()
        return area

    def delete(self, area: DeliveryArea) -> None:
        self.db.delete(area)

    def list_active(self) -> list[DeliveryArea]:
        stmt = (
            select(DeliveryArea)
            .where(DeliveryArea.is_active.is_(True))
            .order_by(asc(DeliveryArea.name))
        )
        return list(self.db.scalars(stmt).all())

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[DeliveryArea], int]:
        stmt = select(DeliveryArea)
        count_stmt = select(func.count()).select_from(DeliveryArea)

        if search:
            pattern = f"%{search.strip()}%"
            filter_clause = or_(
                DeliveryArea.name.ilike(pattern),
                DeliveryArea.description.ilike(pattern),
            )
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, DeliveryArea.name)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)

        return list(self.db.scalars(stmt).all()), total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)
