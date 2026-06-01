"""Purchase planning from production demand and supplier links."""

import csv
import io
import uuid
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.core.enums import PurchasePlanningStatus
from app.core.exceptions import NotFoundError
from app.models.product_item import ProductItem
from app.repositories.product_item_repository import ProductItemRepository
from app.repositories.production_batch_repository import ProductionBatchRepository
from app.schemas.production_batch import ProductionBatchResponse
from app.schemas.purchase_planning import (
    PurchasePlanLine,
    PurchasePlanResponse,
    PurchasePlanStatusUpdate,
)
from app.schemas.supplier import SupplierSummary
from app.services.production_batch_service import ProductionBatchService
from app.services.production_planning_service import ProductionPlanningService

MONEY_PRECISION = Decimal("0.01")
QTY_PRECISION = Decimal("0.0001")


class PurchasePlanningService:
    """Build purchase lists and track planning status per production batch."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.production_planning = ProductionPlanningService(db)
        self.batch_service = ProductionBatchService(db)
        self.batch_repo = ProductionBatchRepository(db)
        self.product_items = ProductItemRepository(db)

    def get_purchase_plan(self, delivery_date: date) -> PurchasePlanResponse:
        batch = self.batch_service.get_model_for_date(delivery_date, auto_create=True)
        lines = self._build_plan_lines(delivery_date, batch.id)
        return PurchasePlanResponse(
            delivery_date=delivery_date,
            production_batch=ProductionBatchResponse.model_validate(batch),
            items=lines,
        )

    def update_purchase_status(self, payload: PurchasePlanStatusUpdate) -> PurchasePlanLine:
        batch = self.batch_service.get_model_for_date(payload.delivery_date, auto_create=True)
        purchase_row = self.batch_repo.get_purchase_item(batch.id, payload.product_item_id)
        if not purchase_row:
            purchase_row = self.batch_repo.upsert_purchase_item(
                batch_id=batch.id,
                product_item_id=payload.product_item_id,
            )
        purchase_row.purchase_status = payload.purchase_status
        self.db.add(purchase_row)
        self.db.commit()

        plan = self.get_purchase_plan(payload.delivery_date)
        for line in plan.items:
            if line.product_item_id == payload.product_item_id:
                return line
        raise NotFoundError("Purchase plan line not found after update")

    def export_csv(self, delivery_date: date) -> tuple[str, str]:
        plan = self.get_purchase_plan(delivery_date)
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(["Purchase List"])
        writer.writerow(["Delivery Date", delivery_date.isoformat()])
        writer.writerow(["Generated At", datetime.now().isoformat(timespec="seconds")])
        writer.writerow([])

        grouped = self._group_by_supplier(plan.items)
        for supplier_name, items in grouped:
            writer.writerow([f"Supplier: {supplier_name}"])
            writer.writerow(["Item", "Quantity", "Unit", "Estimated Cost", "Status"])
            for line in items:
                writer.writerow(
                    [
                        line.product_item_name,
                        str(line.quantity),
                        line.unit,
                        str(line.estimated_cost),
                        line.purchase_status.value,
                    ],
                )
            writer.writerow([])

        filename = f"purchase-list-{delivery_date.isoformat()}.csv"
        return filename, buffer.getvalue()

    def get_purchase_plan_lines(self, delivery_date: date) -> list[PurchasePlanLine]:
        """Inventory-ready purchase plan lines without response wrapping."""
        batch = self.batch_service.get_model_for_date(delivery_date, auto_create=True)
        return self._build_plan_lines(delivery_date, batch.id)

    def _build_plan_lines(
        self,
        delivery_date: date,
        batch_id: uuid.UUID,
    ) -> list[PurchasePlanLine]:
        ingredient_demand = self.production_planning.get_ingredient_demand(delivery_date)
        packaging_demand = self.production_planning.get_packaging_demand(delivery_date)

        merged_qty: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        merged_cost: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        names: dict[uuid.UUID, str] = {}
        units: dict[uuid.UUID, str] = {}

        for row in ingredient_demand:
            merged_qty[row.product_item_id] += row.quantity
            merged_cost[row.product_item_id] += row.estimated_cost
            names[row.product_item_id] = row.product_item_name
            units[row.product_item_id] = row.unit

        for row in packaging_demand:
            merged_qty[row.product_item_id] += row.quantity
            merged_cost[row.product_item_id] += row.estimated_cost
            names[row.product_item_id] = row.product_item_name
            units[row.product_item_id] = row.unit

        item_ids = [item_id for item_id, qty in merged_qty.items() if qty > 0]
        if not item_ids:
            return []

        items_with_supplier = self._load_items_with_suppliers(item_ids)
        items_by_id = {item.id: item for item in items_with_supplier}

        for item_id in item_ids:
            if merged_qty[item_id] > 0:
                self.batch_repo.upsert_purchase_item(batch_id=batch_id, product_item_id=item_id)
        self.db.flush()

        status_by_item = {
            row.product_item_id: row.purchase_status
            for row in self.batch_repo.list_purchase_items(batch_id)
        }

        lines: list[PurchasePlanLine] = []
        for item_id in sorted(item_ids, key=lambda i: names.get(i, "").lower()):
            qty = merged_qty[item_id].quantize(QTY_PRECISION)
            if qty <= 0:
                continue

            status = status_by_item.get(item_id, PurchasePlanningStatus.NOT_PLANNED)

            item = items_by_id.get(item_id)
            supplier_summary = None
            if item and item.primary_supplier:
                supplier_summary = SupplierSummary.model_validate(item.primary_supplier)

            lines.append(
                PurchasePlanLine(
                    product_item_id=item_id,
                    product_item_name=names[item_id],
                    quantity=qty,
                    unit=units[item_id],
                    estimated_cost=merged_cost[item_id].quantize(MONEY_PRECISION),
                    supplier=supplier_summary,
                    purchase_status=status,
                ),
            )

        self.db.commit()
        return lines

    def _load_items_with_suppliers(self, item_ids: list[uuid.UUID]) -> list[ProductItem]:
        from sqlalchemy import select

        stmt = (
            select(ProductItem)
            .options(joinedload(ProductItem.primary_supplier))
            .where(ProductItem.id.in_(item_ids))
        )
        return list(self.db.scalars(stmt).unique().all())

    @staticmethod
    def _group_by_supplier(
        items: list[PurchasePlanLine],
    ) -> list[tuple[str, list[PurchasePlanLine]]]:
        groups: dict[str, list[PurchasePlanLine]] = defaultdict(list)
        for line in items:
            key = line.supplier.supplier_name if line.supplier else "Unassigned"
            groups[key].append(line)

        return sorted(groups.items(), key=lambda pair: pair[0].lower())
