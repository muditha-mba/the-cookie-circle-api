"""Tax charge business logic — order-level taxes and fees."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ChargeType
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.tax_charge import TaxCharge
from app.schemas.charge import (
    TaxChargeCreate,
    TaxChargeResponse,
    TaxChargeUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from math import ceil
from sqlalchemy import asc, desc, or_


class TaxChargeService:
    """Handles CRUD for order-level tax charges."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: TaxChargeCreate) -> TaxChargeResponse:
        existing = self.db.scalar(
            select(TaxCharge).where(
                func.lower(TaxCharge.name) == payload.name.strip().lower()
            )
        )
        if existing:
            raise ConflictError("A tax charge with this name already exists")

        record = TaxCharge(
            name=payload.name.strip(),
            description=payload.description,
            charge_type=payload.charge_type,
            amount=payload.amount,
            is_active=payload.is_active,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return TaxChargeResponse.model_validate(record)

    def get(self, charge_id: uuid.UUID) -> TaxChargeResponse:
        record = self._get_or_404(charge_id)
        return TaxChargeResponse.model_validate(record)

    def list(self, params: PaginationParams) -> PaginatedResponse[TaxChargeResponse]:
        stmt = select(TaxCharge)
        count_stmt = select(func.count()).select_from(TaxCharge)

        if params.search:
            from app.utils.search import ilike_contains
            pattern, escape = ilike_contains(params.search)
            filter_clause = or_(
                TaxCharge.name.ilike(pattern, escape=escape),
                TaxCharge.description.ilike(pattern, escape=escape),
            )
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total = int(self.db.scalar(count_stmt) or 0)
        order = asc(TaxCharge.name) if params.sort_order == "asc" else desc(TaxCharge.name)
        stmt = stmt.order_by(order).offset((params.page - 1) * params.page_size).limit(params.page_size)

        items = list(self.db.scalars(stmt).all())
        total_pages = ceil(total / params.page_size) if total > 0 else 0
        return PaginatedResponse(
            items=[TaxChargeResponse.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    def update(self, charge_id: uuid.UUID, payload: TaxChargeUpdate) -> TaxChargeResponse:
        record = self._get_or_404(charge_id)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        if payload.name is not None:
            existing = self.db.scalar(
                select(TaxCharge).where(
                    func.lower(TaxCharge.name) == payload.name.strip().lower()
                )
            )
            if existing and existing.id != record.id:
                raise ConflictError("A tax charge with this name already exists")

        effective_type = payload.charge_type if payload.charge_type is not None else record.charge_type
        effective_amount = payload.amount if payload.amount is not None else record.amount
        if effective_type == ChargeType.PERCENTAGE and effective_amount > Decimal("100"):
            raise ValidationError("Percentage amount cannot exceed 100")

        for key, value in update_data.items():
            setattr(record, key, value.strip() if key == "name" else value)

        self.db.commit()
        self.db.refresh(record)
        return TaxChargeResponse.model_validate(record)

    def delete(self, charge_id: uuid.UUID) -> None:
        record = self._get_or_404(charge_id)
        self.db.delete(record)
        self.db.commit()

    def _get_or_404(self, charge_id: uuid.UUID) -> TaxCharge:
        record = self.db.get(TaxCharge, charge_id)
        if not record:
            raise NotFoundError("Tax charge not found")
        return record
