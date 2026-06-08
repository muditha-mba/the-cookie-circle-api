"""Generic repository for global charge entities."""

import uuid
from math import ceil
from typing import Generic, TypeVar

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.enums import ChargeApplicability, ChargeType

T = TypeVar("T")


class ChargeRepository(Generic[T]):
    """Repository for charge-like models with shared list/search behavior."""

    SORTABLE_COLUMNS: dict[str, str] = {}

    def __init__(self, db: Session, model: type[T]) -> None:
        self.db = db
        self.model = model
        self._init_sortable_columns()

    def _init_sortable_columns(self) -> None:
        model = self.model
        self.SORTABLE_COLUMNS = {
            "name": model.name,
            "created_at": model.created_at,
            "is_active": model.is_active,
            "charge_type": model.charge_type,
            "amount": model.amount,
        }

    def get_by_id(self, charge_id: uuid.UUID) -> T | None:
        return self.db.get(self.model, charge_id)

    def get_by_name(self, name: str) -> T | None:
        stmt = select(self.model).where(
            func.lower(self.model.name) == name.strip().lower(),
        )
        return self.db.scalar(stmt)

    def create(
        self,
        *,
        name: str,
        description: str | None,
        charge_type: ChargeType,
        amount,
        is_active: bool,
        applicability: ChargeApplicability = ChargeApplicability.BOTH,
    ) -> T:
        record = self.model(
            name=name.strip(),
            description=description,
            charge_type=charge_type,
            amount=amount,
            applicability=applicability,
            is_active=is_active,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def update(self, record: T, **fields) -> T:
        for key, value in fields.items():
            if value is None:
                continue
            if key == "name":
                setattr(record, key, value.strip())
            else:
                setattr(record, key, value)
        self.db.add(record)
        return record

    def delete(self, record: T) -> None:
        self.db.delete(record)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[T], int]:
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        if search:
            pattern = f"%{search.strip()}%"
            filter_clause = or_(
                self.model.name.ilike(pattern),
                self.model.description.ilike(pattern),
            )
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total = int(self.db.scalar(count_stmt) or 0)

        sort_column = self.SORTABLE_COLUMNS.get(sort_by, self.model.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)

        return list(self.db.scalars(stmt).all()), total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)
