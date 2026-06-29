"""Promotion slide service — CRUD, reorder."""

from __future__ import annotations

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.promotion_slide import PromotionSlide
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.promotion_slide import (
    PromotionSlideCreate,
    PromotionSlideResponse,
    PromotionSlideReorder,
    PromotionSlideUpdate,
)


class PromotionSlideService:
    """CRUD and reorder for admin promotion slides."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: PromotionSlideCreate) -> PromotionSlideResponse:
        record = PromotionSlide(
            title=payload.title,
            description=payload.description,
            image_url=payload.image_url,
            cta_text=payload.cta_text,
            cta_destination=payload.cta_destination,
            sort_order=payload.sort_order,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            is_active=payload.is_active,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return PromotionSlideResponse.model_validate(record)

    def get(self, slide_id: uuid.UUID) -> PromotionSlideResponse:
        return PromotionSlideResponse.model_validate(self._get_or_404(slide_id))

    def list(self, params: PaginationParams) -> PaginatedResponse[PromotionSlideResponse]:
        stmt = select(PromotionSlide)
        count_stmt = select(func.count()).select_from(PromotionSlide)

        if params.search:
            from app.utils.search import ilike_contains
            pattern, escape = ilike_contains(params.search)
            clause = PromotionSlide.title.ilike(pattern, escape=escape)
            stmt = stmt.where(clause)
            count_stmt = count_stmt.where(clause)

        total = int(self.db.scalar(count_stmt) or 0)
        order = (
            asc(PromotionSlide.sort_order)
            if params.sort_order == "asc"
            else desc(PromotionSlide.sort_order)
        )
        stmt = (
            stmt.order_by(order, asc(PromotionSlide.created_at))
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
        items = list(self.db.scalars(stmt).all())
        total_pages = ceil(total / params.page_size) if total > 0 else 0
        return PaginatedResponse(
            items=[PromotionSlideResponse.model_validate(r) for r in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    def update(
        self, slide_id: uuid.UUID, payload: PromotionSlideUpdate
    ) -> PromotionSlideResponse:
        record = self._get_or_404(slide_id)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        if not (record.image_url and record.image_url.strip()):
            raise ValidationError("image_url is required")

        for key, value in update_data.items():
            setattr(record, key, value)

        self.db.commit()
        self.db.refresh(record)
        return PromotionSlideResponse.model_validate(record)

    def delete(self, slide_id: uuid.UUID) -> None:
        record = self._get_or_404(slide_id)
        self.db.delete(record)
        self.db.commit()

    def reorder(self, payload: PromotionSlideReorder) -> list[PromotionSlideResponse]:
        """Assign sort_order positions based on the provided ordered list of IDs."""
        slides: dict[uuid.UUID, PromotionSlide] = {
            r.id: r
            for r in self.db.scalars(
                select(PromotionSlide).where(
                    PromotionSlide.id.in_(payload.slide_ids)
                )
            ).all()
        }

        missing = [str(sid) for sid in payload.slide_ids if sid not in slides]
        if missing:
            raise NotFoundError(f"Slides not found: {', '.join(missing)}")

        for position, slide_id in enumerate(payload.slide_ids):
            slides[slide_id].sort_order = position

        self.db.commit()

        all_slides = list(
            self.db.scalars(
                select(PromotionSlide).order_by(
                    asc(PromotionSlide.sort_order), asc(PromotionSlide.created_at)
                )
            ).all()
        )
        return [PromotionSlideResponse.model_validate(s) for s in all_slides]

    def _get_or_404(self, slide_id: uuid.UUID) -> PromotionSlide:
        record = self.db.get(PromotionSlide, slide_id)
        if not record:
            raise NotFoundError("Promotion slide not found")
        return record
