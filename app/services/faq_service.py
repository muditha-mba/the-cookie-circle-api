"""FAQ business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.faq import Faq
from app.repositories.faq_category_repository import FaqCategoryRepository
from app.repositories.faq_repository import FaqRepository
from app.services.business_setting_service import BusinessSettingService
from app.schemas.faq import (
    ClientFaqCategoryGroup,
    ClientFaqItem,
    ClientFaqsResponse,
    FaqCreate,
    FaqResponse,
    FaqUpdate,
)
from app.schemas.faq_category import FaqCategorySummary
from app.services.delivery_schedule_copy_service import get_delivery_schedule_copy
from app.utils.faq_schedule import resolve_schedule_faq_answer


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

    def list_active_public(self) -> ClientFaqsResponse:
        section_enabled = BusinessSettingService(self.db).get_faqs_section_enabled()
        groups: list[ClientFaqCategoryGroup] = []

        if section_enabled:
            schedule_copy = get_delivery_schedule_copy(self.db)
            categories = self.categories.list_active()
            active_faqs = self.faqs.list_active()

            faqs_by_category: dict[uuid.UUID, list[Faq]] = {}
            for faq in active_faqs:
                faqs_by_category.setdefault(faq.category_id, []).append(faq)

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
                                answer=resolve_schedule_faq_answer(
                                    question=item.question,
                                    stored_answer=item.answer,
                                    copy=schedule_copy,
                                ),
                                sort_order=item.sort_order,
                            )
                            for item in category_faqs
                        ],
                    ),
                )

        return ClientFaqsResponse(section_enabled=section_enabled, categories=groups)

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
