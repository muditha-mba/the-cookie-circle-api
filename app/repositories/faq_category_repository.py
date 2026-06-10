"""FAQ category data access."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.faq import Faq
from app.models.faq_category import FaqCategory


class FaqCategoryRepository:
    """Repository for FAQ category records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, category: FaqCategory) -> FaqCategory:
        self.db.add(category)
        return category

    def get_by_id(self, category_id: uuid.UUID) -> FaqCategory | None:
        return self.db.get(FaqCategory, category_id)

    def get_by_name(self, name: str) -> FaqCategory | None:
        stmt = select(FaqCategory).where(FaqCategory.name == name)
        return self.db.scalar(stmt)

    def list_all(self) -> list[FaqCategory]:
        stmt = select(FaqCategory).order_by(
            FaqCategory.sort_order.asc(),
            FaqCategory.name.asc(),
        )
        return list(self.db.scalars(stmt).all())

    def list_active(self) -> list[FaqCategory]:
        stmt = (
            select(FaqCategory)
            .where(FaqCategory.is_active.is_(True))
            .order_by(FaqCategory.sort_order.asc(), FaqCategory.name.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete(self, category: FaqCategory) -> None:
        self.db.delete(category)

    def count_faqs(self, category_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Faq).where(Faq.category_id == category_id)
        return int(self.db.scalar(stmt) or 0)
