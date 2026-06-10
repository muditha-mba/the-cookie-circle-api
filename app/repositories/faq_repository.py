"""FAQ data access."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.faq import Faq


class FaqRepository:
    """Repository for FAQ records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, faq: Faq) -> Faq:
        self.db.add(faq)
        return faq

    def get_by_id(self, faq_id: uuid.UUID) -> Faq | None:
        stmt = (
            select(Faq)
            .options(selectinload(Faq.category))
            .where(Faq.id == faq_id)
        )
        return self.db.scalar(stmt)

    def list_all(self) -> list[Faq]:
        stmt = (
            select(Faq)
            .options(selectinload(Faq.category))
            .order_by(Faq.sort_order.asc(), Faq.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_active(self) -> list[Faq]:
        stmt = (
            select(Faq)
            .options(selectinload(Faq.category))
            .where(Faq.is_active.is_(True))
            .order_by(Faq.sort_order.asc(), Faq.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, faq: Faq) -> None:
        self.db.delete(faq)

    def next_sort_order(self) -> int:
        stmt = select(func.coalesce(func.max(Faq.sort_order), -1))
        current_max = self.db.scalar(stmt)
        return int(current_max or -1) + 1
