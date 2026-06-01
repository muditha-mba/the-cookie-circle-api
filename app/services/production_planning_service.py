"""Production planning and fulfillment aggregation (read-only)."""

import csv
import io
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import OrderStatus, Weekday
from app.core.exceptions import ValidationError
from app.models.collection import Collection
from app.models.order import Order
from app.models.product import Product
from app.repositories.business_setting_repository import BusinessSettingRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.production_repository import ProductionRepository
from app.schemas.production import (
    FulfillmentOrderItem,
    FulfillmentOverview,
    FulfillmentStatusGroup,
    IngredientRequirementLine,
    IngredientRequirementsResponse,
    PackagingRequirementLine,
    PackagingRequirementsResponse,
    ProductDemandLine,
    ProductDemandResponse,
    ProductionBatchOption,
    ProductionBatchesResponse,
    ProductionOrderSummary,
    ProductionSummaryResponse,
)
from app.core import business_settings_keys as keys
from app.utils.costing import calculate_cost_per_unit
from app.utils.weekday import parse_weekday, weekday_to_index

QTY_PRECISION = Decimal("0.0001")
MONEY_PRECISION = Decimal("0.01")

PRODUCTION_EXCLUDED_STATUSES = frozenset({OrderStatus.DRAFT, OrderStatus.CANCELLED})

FULFILLMENT_STATUS_ORDER: tuple[OrderStatus, ...] = (
    OrderStatus.PENDING,
    OrderStatus.CONFIRMED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
    OrderStatus.DELIVERED,
    OrderStatus.CANCELLED,
    OrderStatus.DRAFT,
)


@dataclass(frozen=True)
class IngredientDemand:
    """Internal ingredient demand — consumable by future Inventory module."""

    product_item_id: uuid.UUID
    product_item_name: str
    quantity: Decimal
    unit: str
    estimated_cost: Decimal


@dataclass(frozen=True)
class PackagingDemand:
    """Internal packaging demand — consumable by future Inventory module."""

    product_item_id: uuid.UUID
    product_item_name: str
    item_type_name: str | None
    quantity: Decimal
    unit: str
    estimated_cost: Decimal


class ProductionPlanningService:
    """Aggregate operational production requirements from orders and current recipes."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.production_repo = ProductionRepository(db)
        self.product_repo = ProductRepository(db)
        self.collection_repo = CollectionRepository(db)
        self.settings_repo = BusinessSettingRepository(db)

    def list_batches(self, *, delivery_day_only: bool = False) -> ProductionBatchesResponse:
        delivery_day = self._get_delivery_day()
        delivery_weekday = weekday_to_index(delivery_day) if delivery_day_only else None
        rows = self.production_repo.list_delivery_dates_with_counts(
            delivery_weekday=delivery_weekday,
        )
        delivery_weekday_index = weekday_to_index(delivery_day)
        batches = [
            ProductionBatchOption(
                delivery_date=delivery_date,
                order_count=count,
                label=self._format_batch_label(delivery_date),
                is_delivery_day_batch=delivery_date.weekday() == delivery_weekday_index,
            )
            for delivery_date, count in rows
        ]
        return ProductionBatchesResponse(delivery_day=delivery_day.value, batches=batches)

    def get_summary(self, delivery_date: date) -> ProductionSummaryResponse:
        orders = self.production_repo.get_orders_for_delivery_date(delivery_date)
        production_orders = self._production_orders(orders)
        product_demand = self._build_product_demand(production_orders)
        ingredient_lines = self._build_ingredient_requirements(product_demand)
        packaging_lines = self._build_packaging_requirements(production_orders)

        return ProductionSummaryResponse(
            delivery_date=delivery_date,
            order_summary=self._build_order_summary(
                delivery_date,
                all_orders=orders,
                production_orders=production_orders,
            ),
            product_demand=product_demand,
            ingredient_requirements=[
                self._to_ingredient_line(line) for line in ingredient_lines
            ],
            packaging_requirements=[
                self._to_packaging_line(line) for line in packaging_lines
            ],
            fulfillment=self._build_fulfillment_overview(delivery_date, orders),
        )

    def get_order_summary(self, delivery_date: date) -> ProductionOrderSummary:
        orders = self.production_repo.get_orders_for_delivery_date(delivery_date)
        production_orders = self._production_orders(orders)
        return self._build_order_summary(
            delivery_date,
            all_orders=orders,
            production_orders=production_orders,
        )

    def get_product_demand(self, delivery_date: date) -> ProductDemandResponse:
        orders = self.production_repo.get_orders_for_delivery_date(delivery_date)
        lines = self._build_product_demand(self._production_orders(orders))
        return ProductDemandResponse(delivery_date=delivery_date, items=lines)

    def get_ingredient_requirements(
        self,
        delivery_date: date,
    ) -> IngredientRequirementsResponse:
        """Expose ingredient demand for operational planning and future Inventory."""
        orders = self.production_repo.get_orders_for_delivery_date(delivery_date)
        product_demand = self._build_product_demand(self._production_orders(orders))
        lines = self._build_ingredient_requirements(product_demand)
        return IngredientRequirementsResponse(
            delivery_date=delivery_date,
            items=[self._to_ingredient_line(line) for line in lines],
        )

    def get_packaging_requirements(
        self,
        delivery_date: date,
    ) -> PackagingRequirementsResponse:
        """Expose packaging demand for operational planning and future Inventory."""
        orders = self.production_repo.get_orders_for_delivery_date(delivery_date)
        lines = self._build_packaging_requirements(self._production_orders(orders))
        return PackagingRequirementsResponse(
            delivery_date=delivery_date,
            items=[self._to_packaging_line(line) for line in lines],
        )

    def get_ingredient_demand(self, delivery_date: date) -> list[IngredientDemand]:
        """Inventory-ready ingredient demand without API schema wrapping."""
        orders = self.production_repo.get_orders_for_delivery_date(delivery_date)
        product_demand = self._build_product_demand(self._production_orders(orders))
        return self._build_ingredient_requirements(product_demand)

    def get_packaging_demand(self, delivery_date: date) -> list[PackagingDemand]:
        """Inventory-ready packaging demand without API schema wrapping."""
        orders = self.production_repo.get_orders_for_delivery_date(delivery_date)
        return self._build_packaging_requirements(self._production_orders(orders))

    def get_fulfillment_overview(self, delivery_date: date) -> FulfillmentOverview:
        orders = self.production_repo.get_orders_for_delivery_date(delivery_date)
        return self._build_fulfillment_overview(delivery_date, orders)

    def export_csv(self, delivery_date: date) -> tuple[str, str]:
        """Build production summary CSV. Returns (filename, csv_content)."""
        summary = self.get_summary(delivery_date)
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(["Production Summary"])
        writer.writerow(["Delivery Date", delivery_date.isoformat()])
        writer.writerow(["Generated At", datetime.now().isoformat(timespec="seconds")])
        writer.writerow([])

        writer.writerow(["Order Summary"])
        osum = summary.order_summary
        writer.writerow(["Total Orders", osum.total_orders])
        writer.writerow(["Total Customers", osum.total_customers])
        writer.writerow(["Total Products Ordered", str(osum.total_products_ordered)])
        writer.writerow(["Total Collections Ordered", str(osum.total_collections_ordered)])
        writer.writerow(["Total Revenue", str(osum.total_revenue)])
        writer.writerow(["Total Profit", str(osum.total_profit)])
        writer.writerow([])

        writer.writerow(["Product Demand"])
        writer.writerow(["Product", "Quantity"])
        for line in summary.product_demand:
            writer.writerow([line.product_name, str(line.quantity)])
        writer.writerow([])

        writer.writerow(["Ingredient Requirements"])
        writer.writerow(["Ingredient", "Quantity", "Unit", "Estimated Cost"])
        for line in summary.ingredient_requirements:
            writer.writerow(
                [
                    line.product_item_name,
                    str(line.quantity),
                    line.unit,
                    str(line.estimated_cost),
                ],
            )
        writer.writerow([])

        writer.writerow(["Packaging Requirements"])
        writer.writerow(["Item", "Type", "Quantity", "Unit", "Estimated Cost"])
        for line in summary.packaging_requirements:
            writer.writerow(
                [
                    line.product_item_name,
                    line.item_type_name or "",
                    str(line.quantity),
                    line.unit,
                    str(line.estimated_cost),
                ],
            )
        writer.writerow([])

        writer.writerow(["Orders"])
        writer.writerow(
            ["Order Number", "Customer", "Status", "Revenue", "Profit"],
        )
        for group in summary.fulfillment.groups:
            for order in group.orders:
                writer.writerow(
                    [
                        order.order_number,
                        order.customer_name,
                        order.status.value,
                        str(order.total_revenue_snapshot),
                        str(order.total_profit_snapshot),
                    ],
                )

        filename = f"production-summary-{delivery_date.isoformat()}.csv"
        return filename, buffer.getvalue()

    def _get_delivery_day(self) -> Weekday:
        settings = self.settings_repo.get_all()
        raw = settings.get(keys.DELIVERY_DAY, Weekday.SATURDAY.value)
        return parse_weekday(raw)

    @staticmethod
    def _format_batch_label(delivery_date: date) -> str:
        return delivery_date.strftime(f"%A, %B {delivery_date.day}, %Y")

    @staticmethod
    def _production_orders(orders: list[Order]) -> list[Order]:
        return [o for o in orders if o.status not in PRODUCTION_EXCLUDED_STATUSES]

    def _build_order_summary(
        self,
        delivery_date: date,
        *,
        all_orders: list[Order],
        production_orders: list[Order],
    ) -> ProductionOrderSummary:
        customer_ids: set[uuid.UUID] = set()
        total_products = Decimal("0")
        total_collections = Decimal("0")
        total_revenue = Decimal("0")
        total_profit = Decimal("0")

        for order in production_orders:
            customer_ids.add(order.customer_id)
            total_revenue += order.total_revenue_snapshot
            total_profit += order.total_profit_snapshot
            for line in order.product_lines:
                total_products += line.quantity
            for line in order.collection_lines:
                total_collections += line.quantity

        return ProductionOrderSummary(
            delivery_date=delivery_date,
            total_orders=len(all_orders),
            total_customers=len(customer_ids),
            total_products_ordered=total_products.quantize(QTY_PRECISION),
            total_collections_ordered=total_collections.quantize(QTY_PRECISION),
            total_revenue=total_revenue.quantize(MONEY_PRECISION),
            total_profit=total_profit.quantize(MONEY_PRECISION),
        )

    def _build_product_demand(
        self,
        production_orders: list[Order],
    ) -> list[ProductDemandLine]:
        quantities: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        names: dict[uuid.UUID, str] = {}

        collection_ids: set[uuid.UUID] = set()
        for order in production_orders:
            for line in order.product_lines:
                quantities[line.product_id] += line.quantity
                names[line.product_id] = line.product_name_snapshot
            for line in order.collection_lines:
                collection_ids.add(line.collection_id)

        collections_by_id = self._load_collections(collection_ids)
        for order in production_orders:
            for line in order.collection_lines:
                collection = collections_by_id.get(line.collection_id)
                if collection is None:
                    raise ValidationError(
                        f"Collection {line.collection_id} referenced on order "
                        f"{order.order_number} was not found.",
                    )
                for product_line in collection.product_lines:
                    pid = product_line.product_id
                    quantities[pid] += line.quantity * product_line.quantity
                    if pid not in names and product_line.product:
                        names[pid] = product_line.product.name

        return [
            ProductDemandLine(
                product_id=product_id,
                product_name=names.get(product_id, "Unknown product"),
                quantity=qty.quantize(QTY_PRECISION),
            )
            for product_id, qty in sorted(
                quantities.items(),
                key=lambda item: names.get(item[0], "").lower(),
            )
            if qty > 0
        ]

    def _build_ingredient_requirements(
        self,
        product_demand: list[ProductDemandLine],
    ) -> list[IngredientDemand]:
        if not product_demand:
            return []

        product_ids = [line.product_id for line in product_demand]
        products = {
            p.id: p for p in self.product_repo.get_for_costing_by_ids(product_ids)
        }
        demand_by_product = {line.product_id: line.quantity for line in product_demand}

        aggregated_qty: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        item_meta: dict[uuid.UUID, tuple[str, str]] = {}

        for product_id, total_qty in demand_by_product.items():
            product = products.get(product_id)
            if product is None:
                raise ValidationError(f"Product {product_id} was not found for recipe costing.")
            if not product.recipe_lines:
                raise ValidationError(
                    f"Product '{product.name}' has no recipe; cannot calculate ingredients.",
                )
            if product.yield_quantity <= 0:
                raise ValidationError(
                    f"Product '{product.name}' has invalid yield quantity.",
                )
            scale = total_qty / product.yield_quantity
            for recipe_line in product.recipe_lines:
                item = recipe_line.product_item
                required = (scale * recipe_line.quantity).quantize(QTY_PRECISION)
                aggregated_qty[item.id] += required
                item_meta[item.id] = (item.name, item.purchase_unit)

        return self._finalize_ingredient_demand(aggregated_qty, item_meta, products)

    def _finalize_ingredient_demand(
        self,
        aggregated_qty: dict[uuid.UUID, Decimal],
        item_meta: dict[uuid.UUID, tuple[str, str]],
        products: dict[uuid.UUID, Product],
    ) -> list[IngredientDemand]:
        item_cost_per_unit: dict[uuid.UUID, Decimal] = {}
        for product in products.values():
            for recipe_line in product.recipe_lines:
                item = recipe_line.product_item
                item_cost_per_unit[item.id] = calculate_cost_per_unit(
                    item.purchase_price,
                    item.purchase_quantity,
                )

        lines: list[IngredientDemand] = []
        for item_id, qty in sorted(
            aggregated_qty.items(),
            key=lambda row: item_meta.get(row[0], ("", ""))[0].lower(),
        ):
            if qty <= 0:
                continue
            name, unit = item_meta[item_id]
            cost_per_unit = item_cost_per_unit.get(item_id, Decimal("0"))
            lines.append(
                IngredientDemand(
                    product_item_id=item_id,
                    product_item_name=name,
                    quantity=qty,
                    unit=unit,
                    estimated_cost=(qty * cost_per_unit).quantize(MONEY_PRECISION),
                ),
            )
        return lines

    def _build_packaging_requirements(
        self,
        production_orders: list[Order],
    ) -> list[PackagingDemand]:
        collection_ids: set[uuid.UUID] = set()
        for order in production_orders:
            for line in order.collection_lines:
                collection_ids.add(line.collection_id)

        if not collection_ids:
            return []

        collections_by_id = self._load_collections(collection_ids)
        aggregated_qty: dict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        item_meta: dict[uuid.UUID, tuple[str, str | None, str]] = {}
        item_cost_per_unit: dict[uuid.UUID, Decimal] = {}

        for order in production_orders:
            for line in order.collection_lines:
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
                    item_cost_per_unit[item.id] = calculate_cost_per_unit(
                        item.purchase_price,
                        item.purchase_quantity,
                    )

        lines: list[PackagingDemand] = []
        for item_id, qty in sorted(
            aggregated_qty.items(),
            key=lambda row: item_meta.get(row[0], ("", None, ""))[0].lower(),
        ):
            if qty <= 0:
                continue
            name, type_name, unit = item_meta[item_id]
            cost_per_unit = item_cost_per_unit[item_id]
            lines.append(
                PackagingDemand(
                    product_item_id=item_id,
                    product_item_name=name,
                    item_type_name=type_name,
                    quantity=qty,
                    unit=unit,
                    estimated_cost=(qty * cost_per_unit).quantize(MONEY_PRECISION),
                ),
            )
        return lines

    def _load_collections(
        self,
        collection_ids: set[uuid.UUID],
    ) -> dict[uuid.UUID, Collection]:
        if not collection_ids:
            return {}
        collections = self.collection_repo.get_for_costing_by_ids(list(collection_ids))
        return {c.id: c for c in collections}

    def _build_fulfillment_overview(
        self,
        delivery_date: date,
        orders: list[Order],
    ) -> FulfillmentOverview:
        by_status: dict[OrderStatus, list[FulfillmentOrderItem]] = defaultdict(list)
        for order in orders:
            if order.customer:
                customer_name = (
                    f"{order.customer.first_name} {order.customer.last_name}".strip()
                )
            else:
                customer_name = "—"
            by_status[order.status].append(
                FulfillmentOrderItem(
                    id=order.id,
                    order_number=order.order_number,
                    customer_name=customer_name,
                    status=order.status,
                    total_revenue_snapshot=order.total_revenue_snapshot,
                    total_profit_snapshot=order.total_profit_snapshot,
                ),
            )

        groups: list[FulfillmentStatusGroup] = []
        for status in FULFILLMENT_STATUS_ORDER:
            items = by_status.get(status)
            if items:
                groups.append(
                    FulfillmentStatusGroup(
                        status=status,
                        orders=sorted(items, key=lambda o: o.order_number),
                    ),
                )

        return FulfillmentOverview(
            delivery_date=delivery_date,
            groups=groups,
            total_orders=len(orders),
        )

    @staticmethod
    def _to_ingredient_line(line: IngredientDemand) -> IngredientRequirementLine:
        return IngredientRequirementLine(
            product_item_id=line.product_item_id,
            product_item_name=line.product_item_name,
            quantity=line.quantity,
            unit=line.unit,
            estimated_cost=line.estimated_cost,
        )

    @staticmethod
    def _to_packaging_line(line: PackagingDemand) -> PackagingRequirementLine:
        return PackagingRequirementLine(
            product_item_id=line.product_item_id,
            product_item_name=line.product_item_name,
            item_type_name=line.item_type_name,
            quantity=line.quantity,
            unit=line.unit,
            estimated_cost=line.estimated_cost,
        )
