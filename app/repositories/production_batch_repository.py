"""Production batch data access repository."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.production_batch import ProductionBatch
from app.models.production_batch_purchase_item import ProductionBatchPurchaseItem


class ProductionBatchRepository:
    """Repository for production batch persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, batch_id: uuid.UUID) -> ProductionBatch | None:
        stmt = (
            select(ProductionBatch)
            .options(selectinload(ProductionBatch.purchase_items))
            .where(ProductionBatch.id == batch_id)
        )
        return self.db.scalar(stmt)

    def get_by_delivery_date(self, delivery_date: date) -> ProductionBatch | None:
        stmt = (
            select(ProductionBatch)
            .options(selectinload(ProductionBatch.purchase_items))
            .where(ProductionBatch.delivery_date == delivery_date)
        )
        return self.db.scalar(stmt)

    def create(self, batch: ProductionBatch) -> ProductionBatch:
        self.db.add(batch)
        self.db.flush()
        return batch

    def get_purchase_item(
        self,
        batch_id: uuid.UUID,
        product_item_id: uuid.UUID,
    ) -> ProductionBatchPurchaseItem | None:
        stmt = select(ProductionBatchPurchaseItem).where(
            ProductionBatchPurchaseItem.production_batch_id == batch_id,
            ProductionBatchPurchaseItem.product_item_id == product_item_id,
        )
        return self.db.scalar(stmt)

    def list_purchase_items(self, batch_id: uuid.UUID) -> list[ProductionBatchPurchaseItem]:
        stmt = select(ProductionBatchPurchaseItem).where(
            ProductionBatchPurchaseItem.production_batch_id == batch_id,
        )
        return list(self.db.scalars(stmt).all())

    def upsert_purchase_item(
        self,
        *,
        batch_id: uuid.UUID,
        product_item_id: uuid.UUID,
    ) -> ProductionBatchPurchaseItem:
        existing = self.get_purchase_item(batch_id, product_item_id)
        if existing:
            return existing
        row = ProductionBatchPurchaseItem(
            production_batch_id=batch_id,
            product_item_id=product_item_id,
        )
        self.db.add(row)
        self.db.flush()
        return row
