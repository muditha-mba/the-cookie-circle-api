"""Production batch business logic."""

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.core.enums import ProductionBatchStatus
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.production_batch import ProductionBatch
from app.repositories.production_batch_repository import ProductionBatchRepository
from app.schemas.production_batch import (
    ProductionBatchCreate,
    ProductionBatchResponse,
    ProductionBatchUpdate,
)


class ProductionBatchService:
    """Manage saved production planning batches."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.batches = ProductionBatchRepository(db)

    def get_by_delivery_date(self, delivery_date: date) -> ProductionBatchResponse | None:
        batch = self.batches.get_by_delivery_date(delivery_date)
        if not batch:
            return None
        return ProductionBatchResponse.model_validate(batch)

    def get_or_create_for_date(
        self,
        delivery_date: date,
        *,
        auto_create: bool = True,
    ) -> ProductionBatchResponse:
        batch = self.batches.get_by_delivery_date(delivery_date)
        if batch:
            return ProductionBatchResponse.model_validate(batch)
        if not auto_create:
            raise NotFoundError("Production batch not found for this delivery date")
        return self.create(ProductionBatchCreate(delivery_date=delivery_date))

    def create(self, payload: ProductionBatchCreate) -> ProductionBatchResponse:
        if self.batches.get_by_delivery_date(payload.delivery_date):
            raise ConflictError("A production batch already exists for this delivery date")

        batch = ProductionBatch(
            delivery_date=payload.delivery_date,
            notes=payload.notes,
            status=ProductionBatchStatus.DRAFT,
        )
        self.batches.create(batch)
        self.db.commit()
        self.db.refresh(batch)
        return ProductionBatchResponse.model_validate(batch)

    def update(
        self,
        batch_id: uuid.UUID,
        payload: ProductionBatchUpdate,
    ) -> ProductionBatchResponse:
        batch = self.batches.get_by_id(batch_id)
        if not batch:
            raise NotFoundError("Production batch not found")

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided to update")

        if payload.status is not None:
            batch.status = payload.status
        if payload.notes is not None:
            batch.notes = payload.notes

        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return ProductionBatchResponse.model_validate(batch)

    def get_model_for_date(self, delivery_date: date, *, auto_create: bool = True) -> ProductionBatch:
        batch = self.batches.get_by_delivery_date(delivery_date)
        if batch:
            return batch
        if not auto_create:
            raise NotFoundError("Production batch not found for this delivery date")
        batch = ProductionBatch(delivery_date=delivery_date)
        self.batches.create(batch)
        self.db.flush()
        return batch
