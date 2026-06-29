"""Generic business logic for overhead (utility/labour) charge entities with monthly bill entries."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.schemas.charge import (
    BillEntryCreate,
    BillEntryResponse,
    BillEntryUpdate,
    OverheadChargeBase,
    OverheadChargeDetailResponse,
    OverheadChargeResponse,
    OverheadChargeUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.utils.search import ilike_contains
from math import ceil

from sqlalchemy import asc, desc, func, or_


class OverheadChargeService[ModelT, BillEntryT]:
    """Handles CRUD for overhead charge models (utility or labour) with monthly bill entries."""

    def __init__(
        self,
        db: Session,
        *,
        model: type[ModelT],
        bill_entry_model: type[BillEntryT],
        charge_fk_attr: str,
        response_schema: type[OverheadChargeResponse],
        detail_response_schema: type[OverheadChargeDetailResponse],
        entity_label: str,
        duplicate_name_message: str,
    ) -> None:
        self.db = db
        self.model = model
        self.bill_entry_model = bill_entry_model
        self.charge_fk_attr = charge_fk_attr
        self.response_schema = response_schema
        self.detail_response_schema = detail_response_schema
        self.entity_label = entity_label
        self.duplicate_name_message = duplicate_name_message

    # ── Charge CRUD ──────────────────────────────────────────────────────────

    def create(self, payload: OverheadChargeBase) -> OverheadChargeDetailResponse:
        existing = self.db.scalar(
            select(self.model).where(
                func.lower(self.model.name) == payload.name.strip().lower()
            )
        )
        if existing:
            raise ConflictError(self.duplicate_name_message)

        record = self.model(
            name=payload.name.strip(),
            description=payload.description,
            is_active=payload.is_active,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return self.detail_response_schema.model_validate(record)

    def get(self, charge_id: uuid.UUID) -> OverheadChargeDetailResponse:
        record = self._get_or_404(charge_id)
        return self.detail_response_schema.model_validate(record)

    def list(self, params: PaginationParams) -> PaginatedResponse[OverheadChargeResponse]:
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        if params.search:
            from app.utils.search import ilike_contains
            pattern, escape = ilike_contains(params.search)
            filter_clause = or_(
                self.model.name.ilike(pattern, escape=escape),
                self.model.description.ilike(pattern, escape=escape),
            )
            stmt = stmt.where(filter_clause)
            count_stmt = count_stmt.where(filter_clause)

        total = int(self.db.scalar(count_stmt) or 0)
        order = asc(self.model.name) if params.sort_order == "asc" else desc(self.model.name)
        stmt = stmt.order_by(order).offset((params.page - 1) * params.page_size).limit(params.page_size)

        items = list(self.db.scalars(stmt).all())
        total_pages = ceil(total / params.page_size) if total > 0 else 0
        return PaginatedResponse(
            items=[self.response_schema.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    def update(self, charge_id: uuid.UUID, payload: OverheadChargeUpdate) -> OverheadChargeDetailResponse:
        record = self._get_or_404(charge_id)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        if payload.name is not None:
            existing = self.db.scalar(
                select(self.model).where(
                    func.lower(self.model.name) == payload.name.strip().lower()
                )
            )
            if existing and existing.id != record.id:
                raise ConflictError(self.duplicate_name_message)

        for key, value in update_data.items():
            setattr(record, key, value.strip() if key == "name" else value)

        self.db.commit()
        self.db.refresh(record)
        return self.detail_response_schema.model_validate(record)

    def delete(self, charge_id: uuid.UUID) -> None:
        record = self._get_or_404(charge_id)
        self.db.delete(record)
        self.db.commit()

    # ── Bill Entry CRUD ───────────────────────────────────────────────────────

    def add_bill_entry(
        self,
        charge_id: uuid.UUID,
        payload: BillEntryCreate,
    ) -> BillEntryResponse:
        self._get_or_404(charge_id)
        self._assert_no_duplicate_entry(charge_id, payload.year, payload.month)

        entry = self.bill_entry_model(
            **{self.charge_fk_attr: charge_id},
            year=payload.year,
            month=payload.month,
            amount=payload.amount,
            notes=payload.notes,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return BillEntryResponse.model_validate(entry)

    def update_bill_entry(
        self,
        charge_id: uuid.UUID,
        entry_id: uuid.UUID,
        payload: BillEntryUpdate,
    ) -> BillEntryResponse:
        entry = self._get_entry_or_404(charge_id, entry_id)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        for key, value in update_data.items():
            setattr(entry, key, value)

        self.db.commit()
        self.db.refresh(entry)
        return BillEntryResponse.model_validate(entry)

    def delete_bill_entry(self, charge_id: uuid.UUID, entry_id: uuid.UUID) -> None:
        entry = self._get_entry_or_404(charge_id, entry_id)
        self.db.delete(entry)
        self.db.commit()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_or_404(self, charge_id: uuid.UUID) -> ModelT:
        record = self.db.get(self.model, charge_id)
        if not record:
            raise NotFoundError(f"{self.entity_label} not found")
        return record

    def _get_entry_or_404(self, charge_id: uuid.UUID, entry_id: uuid.UUID) -> BillEntryT:
        entry = self.db.get(self.bill_entry_model, entry_id)
        if not entry or getattr(entry, self.charge_fk_attr) != charge_id:
            raise NotFoundError(f"{self.entity_label} bill entry not found")
        return entry

    def _assert_no_duplicate_entry(
        self,
        charge_id: uuid.UUID,
        year: int,
        month: int,
    ) -> None:
        stmt = select(self.bill_entry_model).where(
            getattr(self.bill_entry_model, self.charge_fk_attr) == charge_id,
            self.bill_entry_model.year == year,
            self.bill_entry_model.month == month,
        )
        existing = self.db.scalar(stmt)
        if existing:
            raise ConflictError(
                f"A bill entry for {year}-{month:02d} already exists for this {self.entity_label.lower()}"
            )
