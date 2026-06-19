"""Purchase receipt data access."""

import uuid
from math import ceil

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import PurchaseReceiptStatus
from app.models.product_item import ProductItem
from app.models.purchase_receipt import PurchaseReceipt
from app.models.purchase_receipt_line import PurchaseReceiptLine
from app.models.supplier import Supplier
from app.utils.search import ilike_contains


class PurchaseReceiptRepository:
    """Repository for purchase receipt persistence."""

    SORTABLE_COLUMNS = {
        "receipt_date": PurchaseReceipt.receipt_date,
        "total_amount": PurchaseReceipt.total_amount,
        "status": PurchaseReceipt.status,
        "created_at": PurchaseReceipt.created_at,
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, receipt_id: uuid.UUID) -> PurchaseReceipt | None:
        stmt = (
            select(PurchaseReceipt)
            .options(
                joinedload(PurchaseReceipt.supplier),
                joinedload(PurchaseReceipt.lines).joinedload(PurchaseReceiptLine.product_item),
            )
            .where(PurchaseReceipt.id == receipt_id)
        )
        return self.db.scalar(stmt)

    def create(self, receipt: PurchaseReceipt) -> PurchaseReceipt:
        self.db.add(receipt)
        self.db.flush()
        return receipt

    def delete(self, receipt: PurchaseReceipt) -> None:
        self.db.delete(receipt)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        sort_by: str,
        sort_order: str,
        status: PurchaseReceiptStatus | None = None,
        supplier_id: uuid.UUID | None = None,
    ) -> tuple[list[PurchaseReceipt], int]:
        stmt = select(PurchaseReceipt).options(joinedload(PurchaseReceipt.supplier))
        count_stmt = select(func.count()).select_from(PurchaseReceipt)

        if status is not None:
            stmt = stmt.where(PurchaseReceipt.status == status)
            count_stmt = count_stmt.where(PurchaseReceipt.status == status)

        if supplier_id is not None:
            stmt = stmt.where(PurchaseReceipt.supplier_id == supplier_id)
            count_stmt = count_stmt.where(PurchaseReceipt.supplier_id == supplier_id)

        if search:
            pattern, escape = ilike_contains(search)
            search_filter = or_(
                PurchaseReceipt.reference_number.ilike(pattern, escape=escape),
                Supplier.supplier_name.ilike(pattern, escape=escape),
            )
            stmt = stmt.join(Supplier).where(search_filter)
            count_stmt = count_stmt.join(Supplier).where(search_filter)

        total = int(self.db.scalar(count_stmt) or 0)
        sort_column = self.SORTABLE_COLUMNS.get(sort_by, PurchaseReceipt.receipt_date)
        order = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)
        return list(self.db.scalars(stmt).unique().all()), total

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)
