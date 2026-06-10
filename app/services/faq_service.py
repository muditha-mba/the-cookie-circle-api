"""FAQ business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.faq import Faq
from app.repositories.faq_category_repository import FaqCategoryRepository
from app.repositories.faq_repository import FaqRepository
from app.schemas.faq import (
    ClientFaqCategoryGroup,
    ClientFaqItem,
    FaqCreate,
    FaqResponse,
    FaqUpdate,
)
from app.schemas.faq_category import FaqCategorySummary


class FaqService:
    """Handles FAQ CRUD."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.faqs = FaqRepository(db)
        self.categories = FaqCategoryRepository(db)

    def create(self, payload: FaqCreate) -> FaqResponse:
        self._require_category(payload.category_id)

        faq = Faq(
            category_id=payload.category_id,
            question=payload.question,
            answer=payload.answer,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
        self.faqs.create(faq)
        self.db.commit()
        faq = self.faqs.get_by_id(faq.id)
        if not faq:
            raise NotFoundError("FAQ not found")
        return self._to_response(faq)

    def get(self, faq_id: uuid.UUID) -> FaqResponse:
        faq = self.faqs.get_by_id(faq_id)
        if not faq:
            raise NotFoundError("FAQ not found")
        return self._to_response(faq)

    def list_all(self) -> list[FaqResponse]:
        return [self._to_response(item) for item in self.faqs.list_all()]

    def list_active_public(self) -> list[ClientFaqCategoryGroup]:
        categories = self.categories.list_active()
        active_faqs = self.faqs.list_active()

        faqs_by_category: dict[uuid.UUID, list[Faq]] = {}
        for faq in active_faqs:
            faqs_by_category.setdefault(faq.category_id, []).append(faq)

        groups: list[ClientFaqCategoryGroup] = []
        for category in categories:
            category_faqs = faqs_by_category.get(category.id, [])
            if not category_faqs:
                continue
            groups.append(
                ClientFaqCategoryGroup(
                    id=category.id,
                    name=category.name,
                    sort_order=category.sort_order,
                    faqs=[
                        ClientFaqItem(
                            id=item.id,
                            question=item.question,
                            answer=item.answer,
                            sort_order=item.sort_order,
                        )
                        for item in category_faqs
                    ],
                ),
            )
        return groups

    def update(self, faq_id: uuid.UUID, payload: FaqUpdate) -> FaqResponse:
        faq = self.faqs.get_by_id(faq_id)
        if not faq:
            raise NotFoundError("FAQ not found")

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        if payload.category_id is not None:
            self._require_category(payload.category_id)

        for field, value in update_data.items():
            setattr(faq, field, value)

        self.db.commit()
        self.db.refresh(faq)
        return self._to_response(faq)

    def delete(self, faq_id: uuid.UUID) -> None:
        faq = self.faqs.get_by_id(faq_id)
        if not faq:
            raise NotFoundError("FAQ not found")
        self.faqs.delete(faq)
        self.db.commit()

    def _require_category(self, category_id: uuid.UUID) -> None:
        if not self.categories.get_by_id(category_id):
            raise NotFoundError("FAQ category not found")

    def _to_response(self, faq: Faq) -> FaqResponse:
        if faq.category is None:
            self.db.refresh(faq, attribute_names=["category"])
        return FaqResponse(
            id=faq.id,
            category_id=faq.category_id,
            category=FaqCategorySummary.model_validate(faq.category),
            question=faq.question,
            answer=faq.answer,
            sort_order=faq.sort_order,
            is_active=faq.is_active,
        )
