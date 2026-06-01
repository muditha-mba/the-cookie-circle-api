"""Delivery area business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.delivery_area import DeliveryArea
from app.repositories.delivery_area_repository import DeliveryAreaRepository
from app.schemas.delivery_area import (
    DeliveryAreaCreate,
    DeliveryAreaResponse,
    DeliveryAreaUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams


class DeliveryAreaService:
    """Handles delivery area CRUD."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.areas = DeliveryAreaRepository(db)

    def create(self, payload: DeliveryAreaCreate) -> DeliveryAreaResponse:
        if self.areas.get_by_name(payload.name):
            raise ConflictError("A delivery area with this name already exists")

        area = DeliveryArea(
            name=payload.name,
            description=payload.description,
            delivery_fee_override=payload.delivery_fee_override,
            pickup_only=payload.pickup_only,
            is_active=payload.is_active,
        )
        self.areas.create(area)
        self.db.commit()
        self.db.refresh(area)
        return DeliveryAreaResponse.model_validate(area)

    def get(self, area_id: uuid.UUID) -> DeliveryAreaResponse:
        area = self.areas.get_by_id(area_id)
        if not area:
            raise NotFoundError("Delivery area not found")
        return DeliveryAreaResponse.model_validate(area)

    def list(self, params: PaginationParams) -> PaginatedResponse[DeliveryAreaResponse]:
        items, total = self.areas.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        return PaginatedResponse(
            items=[DeliveryAreaResponse.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.areas.total_pages(total, params.page_size),
        )

    def list_active(self) -> list[DeliveryAreaResponse]:
        return [DeliveryAreaResponse.model_validate(a) for a in self.areas.list_active()]

    def update(self, area_id: uuid.UUID, payload: DeliveryAreaUpdate) -> DeliveryAreaResponse:
        area = self.areas.get_by_id(area_id)
        if not area:
            raise NotFoundError("Delivery area not found")

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        if payload.name is not None:
            existing = self.areas.get_by_name(payload.name)
            if existing and existing.id != area.id:
                raise ConflictError("A delivery area with this name already exists")
            area.name = payload.name
        if payload.description is not None:
            area.description = payload.description
        if "delivery_fee_override" in update_data:
            area.delivery_fee_override = payload.delivery_fee_override
        if payload.pickup_only is not None:
            area.pickup_only = payload.pickup_only
        if payload.is_active is not None:
            area.is_active = payload.is_active

        self.db.add(area)
        self.db.commit()
        self.db.refresh(area)
        return DeliveryAreaResponse.model_validate(area)

    def delete(self, area_id: uuid.UUID) -> None:
        area = self.areas.get_by_id(area_id)
        if not area:
            raise NotFoundError("Delivery area not found")
        self.areas.delete(area)
        self.db.commit()
