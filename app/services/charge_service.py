"""Generic business logic for global charge entities."""

import uuid
from decimal import Decimal
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.core.enums import ChargeType

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.repositories.charge_repository import ChargeRepository
from app.schemas.charge import ChargeBase, ChargeResponse, ChargeUpdate
from app.schemas.pagination import PaginatedResponse, PaginationParams

ModelT = TypeVar("ModelT")
CreateT = TypeVar("CreateT", bound=ChargeBase)
UpdateT = TypeVar("UpdateT", bound=ChargeUpdate)
ResponseT = TypeVar("ResponseT", bound=ChargeResponse)


class ChargeService(Generic[ModelT, CreateT, UpdateT, ResponseT]):
    """Handles CRUD for a single charge model."""

    def __init__(
        self,
        db: Session,
        *,
        model: type[ModelT],
        response_schema: type[ResponseT],
        entity_label: str,
        duplicate_name_message: str,
    ) -> None:
        self.db = db
        self.response_schema = response_schema
        self.entity_label = entity_label
        self.duplicate_name_message = duplicate_name_message
        self.charges = ChargeRepository(db, model)

    def create(self, payload: CreateT) -> ResponseT:
        if self.charges.get_by_name(payload.name):
            raise ConflictError(self.duplicate_name_message)

        record = self.charges.create(
            name=payload.name,
            description=payload.description,
            charge_type=payload.charge_type,
            amount=payload.amount,
            applicability=payload.applicability,
            is_active=payload.is_active,
        )
        self.db.commit()
        self.db.refresh(record)
        return self.response_schema.model_validate(record)

    def get(self, charge_id: uuid.UUID) -> ResponseT:
        record = self.charges.get_by_id(charge_id)
        if not record:
            raise NotFoundError(f"{self.entity_label} not found")
        return self.response_schema.model_validate(record)

    def list(self, params: PaginationParams) -> PaginatedResponse[ResponseT]:
        items, total = self.charges.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        return PaginatedResponse(
            items=[self.response_schema.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.charges.total_pages(total, params.page_size),
        )

    def update(self, charge_id: uuid.UUID, payload: UpdateT) -> ResponseT:
        record = self.charges.get_by_id(charge_id)
        if not record:
            raise NotFoundError(f"{self.entity_label} not found")

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        if payload.name is not None:
            existing = self.charges.get_by_name(payload.name)
            if existing and existing.id != record.id:
                raise ConflictError(self.duplicate_name_message)

        effective_type = payload.charge_type if payload.charge_type is not None else record.charge_type
        effective_amount = payload.amount if payload.amount is not None else record.amount
        if effective_type == ChargeType.PERCENTAGE and effective_amount > Decimal("100"):
            raise ValidationError("Percentage amount cannot exceed 100")

        self.charges.update(record, **update_data)
        self.db.commit()
        self.db.refresh(record)
        return self.response_schema.model_validate(record)

    def delete(self, charge_id: uuid.UUID) -> None:
        record = self.charges.get_by_id(charge_id)
        if not record:
            raise NotFoundError(f"{self.entity_label} not found")
        self.charges.delete(record)
        self.db.commit()
