"""Purchase spend summaries from confirmed receipts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import PurchaseReceiptStatus
from app.core.exceptions import ValidationError
from app.models.product_item import ProductItem
from app.models.product_item_type import ProductItemType
from app.models.purchase_receipt import PurchaseReceipt
from app.models.purchase_receipt_line import PurchaseReceiptLine
from app.models.supplier import Supplier
from app.schemas.inventory_readiness import (
    InventoryExpenseItemTypeRow,
    InventoryExpenseSummaryResponse,
    InventoryExpenseSupplierRow,
)

MONEY_PRECISION = Decimal("0.01")


class InventoryExpenseService:
    """Aggregate confirmed purchase receipt spend."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_summary(self, *, from_date: date, to_date: date) -> InventoryExpenseSummaryResponse:
        if from_date > to_date:
            raise ValidationError("from_date must be on or before to_date")

        receipt_filters = (
            PurchaseReceipt.status == PurchaseReceiptStatus.CONFIRMED,
            PurchaseReceipt.receipt_date >= from_date,
            PurchaseReceipt.receipt_date <= to_date,
        )

        total_amount = Decimal(
            str(
                self.db.scalar(
                    select(func.coalesce(func.sum(PurchaseReceipt.total_amount), 0)).where(
                        *receipt_filters,
                    ),
                )
                or 0,
            ),
        ).quantize(MONEY_PRECISION)
        receipt_count = int(
            self.db.scalar(select(func.count()).select_from(PurchaseReceipt).where(*receipt_filters))
            or 0,
        )

        supplier_rows = self.db.execute(
            select(
                PurchaseReceipt.supplier_id,
                Supplier.supplier_name,
                func.count(PurchaseReceipt.id),
                func.coalesce(func.sum(PurchaseReceipt.total_amount), 0),
            )
            .join(Supplier, Supplier.id == PurchaseReceipt.supplier_id)
            .where(*receipt_filters)
            .group_by(PurchaseReceipt.supplier_id, Supplier.supplier_name)
            .order_by(func.sum(PurchaseReceipt.total_amount).desc()),
        ).all()

        item_type_rows = self.db.execute(
            select(
                ProductItemType.id,
                ProductItemType.name,
                func.coalesce(func.sum(PurchaseReceiptLine.line_total), 0),
            )
            .select_from(PurchaseReceiptLine)
            .join(PurchaseReceipt, PurchaseReceipt.id == PurchaseReceiptLine.purchase_receipt_id)
            .join(ProductItem, ProductItem.id == PurchaseReceiptLine.product_item_id)
            .join(ProductItemType, ProductItemType.id == ProductItem.item_type_id)
            .where(*receipt_filters)
            .group_by(ProductItemType.id, ProductItemType.name)
            .order_by(func.sum(PurchaseReceiptLine.line_total).desc()),
        ).all()

        return InventoryExpenseSummaryResponse(
            from_date=from_date,
            to_date=to_date,
            total_amount=total_amount,
            receipt_count=receipt_count,
            by_supplier=[
                InventoryExpenseSupplierRow(
                    supplier_id=row[0],
                    supplier_name=row[1],
                    receipt_count=int(row[2]),
                    total_amount=Decimal(str(row[3])).quantize(MONEY_PRECISION),
                )
                for row in supplier_rows
            ],
            by_item_type=[
                InventoryExpenseItemTypeRow(
                    item_type_id=row[0],
                    item_type_name=row[1],
                    total_amount=Decimal(str(row[2])).quantize(MONEY_PRECISION),
                )
                for row in item_type_rows
            ],
        )
