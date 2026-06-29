"""Supplier data access repository."""

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.utils.search import ilike_contains


class SupplierRepository:
    """Repository for supplier persistence."""

    SORTABLE_COLUMNS = {
        "supplier_name": Supplier.supplier_name,
        "created_at": Supplier.created_at,
        "is_active": Supplier.is_active,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, supplier_id: uuid.UUID) -> Supplier | None:
        return self.db.get(Supplier, supplier_id)

    def get_by_name(self, name: str) -> Supplier | None:
        stmt = select(Supplier).where(
            func.lower(Supplier.supplier_name) == name.strip().lower(),
        )
        return self.db.scalar(stmt)

    def create(self, supplier: Supplier) -> Supplier:
        self.db.add(supplier)
        self.db.flush()
        return supplier

    def delete(self, supplier: Supplier) -> None:
        self.db.delete(supplier)

    def list_active(self) -> list[Supplier]:
        stmt = (
            select(Supplier)
            .where(Supplier.is_active.is_(True))
            .order_by(Supplier.supplier_name.asc())
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
    ) -> tuple[list[Supplier], int]:
        stmt = select(Supplier)
        count_stmt = select(func.count()).select_from(Supplier)

        if search:
            pattern, escape = ilike_contains(search)
            filter_clause = or_(
                Supplier.supplier_name.ilike(pattern, escape=escape),
                Supplier.contact_person.ilike(pattern, escape=escape),
                Supplier.email.ilike(pattern, escape=escape),
                Supplier.phone.ilike(pattern, escape=escape),
            )
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, Supplier.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)

        return list(self.db.scalars(stmt).all()), total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)