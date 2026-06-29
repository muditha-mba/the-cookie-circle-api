"""FAQ category business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.faq_category import FaqCategory
from app.repositories.faq_category_repository import FaqCategoryRepository
from app.schemas.faq_category import FaqCategoryCreate, FaqCategoryResponse, FaqCategoryUpdate


class FaqCategoryService:
    """Handles FAQ category CRUD."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.categories = FaqCategoryRepository(db)

    def create(self, payload: FaqCategoryCreate) -> FaqCategoryResponse:
        if self.categories.get_by_name(payload.name):
            raise ConflictError("A FAQ category with this name already exists")

        category = FaqCategory(
            name=payload.name,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
        self.categories.create(category)
        self.db.commit()
        self.db.refresh(category)
        return self._to_response(category)

    def get(self, category_id: uuid.UUID) -> FaqCategoryResponse:
        category = self.categories.get_by_id(category_id)
        if not category:
            raise NotFoundError("FAQ category not found")
        return self._to_response(category)

    def list_all(self) -> list[FaqCategoryResponse]:
        return [self._to_response(item) for item in self.categories.list_all()]

    def list_active(self) -> list[FaqCategoryResponse]:
        return [self._to_response(item) for item in self.categories.list_active()]

    def update(self, category_id: uuid.UUID, payload: FaqCategoryUpdate) -> FaqCategoryResponse:
        category = self.categories.get_by_id(category_id)
        if not category:
            raise NotFoundError("FAQ category not found")

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        if payload.name is not None:
            existing = self.categories.get_by_name(payload.name)
            if existing and existing.id != category.id:
                raise ConflictError("A FAQ category with this name already exists")

        for field, value in update_data.items():
            setattr(category, field, value)

        self.db.commit()
        self.db.refresh(category)
        return self._to_response(category)

    def delete(self, category_id: uuid.UUID) -> None:
        category = self.categories.get_by_id(category_id)
        if not category:
            raise NotFoundError("FAQ category not found")

        if self.categories.count_faqs(category_id) > 0:
            raise ValidationError("Cannot delete a category that still has FAQs assigned to it")

        self.categories.delete(category)
        self.db.commit()

    def _to_response(self, category: FaqCategory) -> FaqCategoryResponse:
        return FaqCategoryResponse(
            id=category.id,
            name=category.name,
            sort_order=category.sort_order,
            is_active=category.is_active,
            faq_count=self.categories.count_faqs(category.id),
        )
