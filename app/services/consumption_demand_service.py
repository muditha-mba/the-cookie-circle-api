"""Build ingredient and packaging demand for consumption proposals."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import ConsumptionDemandType
from app.core.exceptions import ValidationError
from app.models.order import Order
from app.repositories.product_item_repository import ProductItemRepository
from app.services.inventory_balance_service import InventoryBalanceService
from app.services.production_planning_service import ProductionPlanningService

QTY_PRECISION = Decimal("0.0001")


@dataclass(frozen=True)
class ConsumptionDemandLine:
    product_item_id: uuid.UUID
    product_item_name: str
    demand_type: ConsumptionDemandType
    quantity: Decimal
    unit: str
    track_inventory: bool
    quantity_on_hand: Decimal


class ConsumptionDemandService:
    """Aggregate consumption demand from delivered orders."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.planning = ProductionPlanningService(db)
        self.items = ProductItemRepository(db)
        self.balances = InventoryBalanceService(db)

    def build_demand_lines(self, orders: list[Order]) -> list[ConsumptionDemandLine]:
        if not orders:
            return []

        production_orders = self.planning._production_orders(orders)
        product_demand = self.planning._build_product_demand(production_orders)
        ingredient_lines = self.planning._build_ingredient_requirements(product_demand)
        packaging_lines = self._build_packaging_requirements_for_consumption(production_orders)

        merged: dict[tuple[uuid.UUID, ConsumptionDemandType], ConsumptionDemandLine] = {}

        for line in ingredient_lines:
            key = (line.product_item_id, ConsumptionDemandType.INGREDIENT)
            merged[key] = self._to_demand_line(
                product_item_id=line.product_item_id,
                product_item_name=line.product_item_name,
                demand_type=ConsumptionDemandType.INGREDIENT,
                quantity=line.quantity,
                unit=line.unit,
            )

        for line in packaging_lines:
            key = (line.product_item_id, ConsumptionDemandType.PACKAGING)
            existing = merged.get(key)
            quantity = line.quantity
            if existing:
                quantity = (existing.quantity + line.quantity).quantize(QTY_PRECISION)
            merged[key] = self._to_demand_line(
                product_item_id=line.product_item_id,
                product_item_name=line.product_item_name,
                demand_type=ConsumptionDemandType.PACKAGING,
                quantity=quantity,
                unit=line.unit,
            )

        return sorted(
            merged.values(),
            key=lambda row: (row.product_item_name.lower(), row.demand_type.value),
        )

    def _to_demand_line(
        self,
        *,
        product_item_id: uuid.UUID,
        product_item_name: str,
        demand_type: ConsumptionDemandType,
        quantity: Decimal,
        unit: str,
    ) -> ConsumptionDemandLine:
        item = self.items.get_by_id(product_item_id)
        track_inventory = bool(item and item.track_inventory)
        on_hand = self.balances.sum_on_hand(product_item_id) if track_inventory else Decimal("0")
        return ConsumptionDemandLine(
            product_item_id=product_item_id,
            product_item_name=product_item_name,
            demand_type=demand_type,
            quantity=quantity.quantize(QTY_PRECISION),
            unit=unit,
            track_inventory=track_inventory,
            quantity_on_hand=on_hand,
        )

    def _build_packaging_requirements_for_consumption(
        self,
        production_orders: list[Order],
    ):
        """Packaging demand only for collection lines with a package fee snapshot."""
        from app.services.production_planning_service import PackagingDemand

        collection_ids: set[uuid.UUID] = set()
        for order in production_orders:
            for line in order.collection_lines:
                if (line.package_fee_snapshot or Decimal("0")) > 0:
                    collection_ids.add(line.collection_id)

        if not collection_ids:
            return []

        collections_by_id = self.planning._load_collections(collection_ids)
        aggregated_qty: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        item_meta: dict[uuid.UUID, tuple[str, str | None, str]] = {}

        for order in production_orders:
            for line in order.collection_lines:
                if (line.package_fee_snapshot or Decimal("0")) <= 0:
                    continue
                collection = collections_by_id.get(line.collection_id)
                if collection is None:
                    raise ValidationError(
                        f"Collection {line.collection_id} referenced on order "
                        f"{order.order_number} was not found.",
                    )
                for item_line in collection.item_lines:
                    item = item_line.product_item
                    required = (line.quantity * item_line.quantity).quantize(QTY_PRECISION)
                    aggregated_qty[item.id] += required
                    type_name = item.item_type.name if item.item_type else None
                    item_meta[item.id] = (item.name, type_name, item.purchase_unit)

        lines: list[PackagingDemand] = []
        for item_id, qty in sorted(
            aggregated_qty.items(),
            key=lambda row: item_meta.get(row[0], ("", None, ""))[0].lower(),
        ):
            if qty <= 0:
                continue
            name, type_name, unit = item_meta[item_id]
            lines.append(
                PackagingDemand(
                    product_item_id=item_id,
                    product_item_name=name,
                    item_type_name=type_name,
                    quantity=qty,
                    unit=unit,
                    estimated_cost=Decimal("0"),
                ),
            )
        return lines
