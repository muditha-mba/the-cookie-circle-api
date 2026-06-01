"""Customer data access repository."""

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.customer import Customer


class CustomerRepository:
    """Repository for customer persistence."""

    SORTABLE_COLUMNS = {
        "first_name": Customer.first_name,
        "last_name": Customer.last_name,
        "email": Customer.email,
        "created_at": Customer.created_at,
        "is_active": Customer.is_active,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        stmt = (
            select(Customer)
            .options(joinedload(Customer.user))
            .where(Customer.id == customer_id)
        )
        return self.db.scalar(stmt)

    def get_by_user_id(self, user_id: uuid.UUID) -> Customer | None:
        stmt = select(Customer).where(Customer.user_id == user_id)
        return self.db.scalar(stmt)

    def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        return self.get_by_id(customer.id)  # type: ignore[return-value]

    def delete(self, customer: Customer) -> None:
        self.db.delete(customer)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Customer], int]:
        stmt = select(Customer).options(joinedload(Customer.user))
        count_stmt = select(func.count()).select_from(Customer)

        if search:
            pattern = f"%{search.strip()}%"
            filter_clause = or_(
                Customer.first_name.ilike(pattern),
                Customer.last_name.ilike(pattern),
                Customer.email.ilike(pattern),
                Customer.phone.ilike(pattern),
            )
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, Customer.created_at)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)

        return list(self.db.scalars(stmt).unique().all()), total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)
