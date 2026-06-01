"""Order profitability snapshots and analytics-readiness queries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.collection import Collection
from app.models.order import Order
from app.models.order_collection_line import OrderCollectionLine
from app.models.order_product_line import OrderProductLine
from app.models.product import Product
from app.repositories.collection_repository import CollectionRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import OrderCollectionLineInput, OrderProductLineInput
from app.schemas.order_profitability import (
    OrderFinancialSnapshot,
    ProfitableCollectionSoldRow,
    ProfitableProductSoldRow,
    TopProfitableOrderRow,
)
from app.services.collection_cost_service import calculate_breakdown_for_collection
from app.services.product_cost_service import _money, calculate_breakdown_for_product


@dataclass(frozen=True)
class OrderSnapshotBuildResult:
    """Fully validated snapshots ready to persist on an order."""

    product_lines: list[OrderProductLine]
    collection_lines: list[OrderCollectionLine]
    financials: OrderFinancialSnapshot


class OrderProfitabilityService:
    """
    Calculates profitability using live catalog costs at order save time,
    then persists immutable snapshots. Reads for display never recalculate.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.collections = CollectionRepository(db)
        self.orders = OrderRepository(db)

    def build_order_snapshots(
        self,
        *,
        product_lines: list[OrderProductLineInput],
        collection_lines: list[OrderCollectionLineInput],
        delivery_fee: Decimal,
    ) -> OrderSnapshotBuildResult:
        if not product_lines and not collection_lines:
            raise ValidationError("At least one product or collection line is required")

        self._ensure_no_duplicate_product_ids(product_lines)
        self._ensure_no_duplicate_collection_ids(collection_lines)

        built_products = [self._build_product_line_snapshot(line) for line in product_lines]
        built_collections = [
            self._build_collection_line_snapshot(line) for line in collection_lines
        ]

        products_subtotal = _money(
            sum(
                line.product_selling_price_snapshot * line.quantity for line in built_products
            ),
        )
        collections_subtotal = _money(
            sum(
                line.collection_selling_price_snapshot * line.quantity
                for line in built_collections
            ),
        )
        products_cost = _money(
            sum(line.product_cost_snapshot * line.quantity for line in built_products),
        )
        collections_cost = _money(
            sum(line.collection_cost_snapshot * line.quantity for line in built_collections),
        )

        delivery = _money(delivery_fee)
        total_revenue = _money(products_subtotal + collections_subtotal + delivery)
        total_cost = _money(products_cost + collections_cost)
        total_profit = _money(total_revenue - total_cost)
        margin = (
            _money((total_profit / total_revenue) * Decimal("100"))
            if total_revenue > 0
            else Decimal("0.00")
        )

        financials = OrderFinancialSnapshot(
            products_subtotal_snapshot=products_subtotal,
            collections_subtotal_snapshot=collections_subtotal,
            delivery_fee_snapshot=delivery,
            total_revenue_snapshot=total_revenue,
            total_cost_snapshot=total_cost,
            total_profit_snapshot=total_profit,
            margin_percentage_snapshot=margin,
        )

        return OrderSnapshotBuildResult(
            product_lines=built_products,
            collection_lines=built_collections,
            financials=financials,
        )

    def apply_snapshots_to_order(self, order: Order, result: OrderSnapshotBuildResult) -> None:
        """Write calculated snapshots onto an order model (create or line update)."""
        order.products_subtotal_snapshot = result.financials.products_subtotal_snapshot
        order.collections_subtotal_snapshot = result.financials.collections_subtotal_snapshot
        order.delivery_fee_snapshot = result.financials.delivery_fee_snapshot
        order.total_revenue_snapshot = result.financials.total_revenue_snapshot
        order.total_cost_snapshot = result.financials.total_cost_snapshot
        order.total_profit_snapshot = result.financials.total_profit_snapshot
        order.margin_percentage_snapshot = result.financials.margin_percentage_snapshot

    def apply_delivery_fee_snapshot(self, order: Order, delivery_fee: Decimal) -> None:
        """
        Recompute order-level revenue/profit from existing line snapshots only.
        Used when delivery area changes without line edits.
        """
        delivery = _money(delivery_fee)
        products = _money(order.products_subtotal_snapshot)
        collections = _money(order.collections_subtotal_snapshot)
        total_revenue = _money(products + collections + delivery)
        total_profit = _money(total_revenue - order.total_cost_snapshot)

        order.delivery_fee_snapshot = delivery
        order.total_revenue_snapshot = total_revenue
        order.total_profit_snapshot = total_profit
        order.margin_percentage_snapshot = (
            _money((total_profit / total_revenue) * Decimal("100"))
            if total_revenue > 0
            else Decimal("0.00")
        )

    @staticmethod
    def financial_snapshot_from_order(order: Order) -> OrderFinancialSnapshot:
        """Read persisted snapshots only — never recalculates from catalog."""
        return OrderFinancialSnapshot(
            products_subtotal_snapshot=order.products_subtotal_snapshot,
            collections_subtotal_snapshot=order.collections_subtotal_snapshot,
            delivery_fee_snapshot=order.delivery_fee_snapshot,
            total_revenue_snapshot=order.total_revenue_snapshot,
            total_cost_snapshot=order.total_cost_snapshot,
            total_profit_snapshot=order.total_profit_snapshot,
            margin_percentage_snapshot=order.margin_percentage_snapshot,
        )

    def get_top_profitable_orders(self, *, limit: int = 10) -> list[TopProfitableOrderRow]:
        orders = self.orders.fetch_top_profitable_orders(limit=limit)
        return [
            TopProfitableOrderRow(
                order_id=order.id,
                order_number=order.order_number,
                total_revenue_snapshot=order.total_revenue_snapshot,
                total_profit_snapshot=order.total_profit_snapshot,
                margin_percentage_snapshot=order.margin_percentage_snapshot,
                created_at=order.created_at,
            )
            for order in orders
        ]

    def get_most_profitable_products_sold(
        self,
        *,
        limit: int = 10,
    ) -> list[ProfitableProductSoldRow]:
        rows = self.orders.fetch_most_profitable_products_sold(limit=limit)
        return [ProfitableProductSoldRow.model_validate(row) for row in rows]

    def get_most_profitable_collections_sold(
        self,
        *,
        limit: int = 10,
    ) -> list[ProfitableCollectionSoldRow]:
        rows = self.orders.fetch_most_profitable_collections_sold(limit=limit)
        return [ProfitableCollectionSoldRow.model_validate(row) for row in rows]

    def _build_product_line_snapshot(self, line_input: OrderProductLineInput) -> OrderProductLine:
        products = self.products.get_for_costing_by_ids([line_input.product_id])
        if not products:
            raise NotFoundError(f"Product not found: {line_input.product_id}")

        product = products[0]
        self._validate_product_for_snapshot(product)

        try:
            breakdown = calculate_breakdown_for_product(product)
        except Exception as exc:  # noqa: BLE001 — surface as validation failure
            raise ValidationError(
                f"Unable to calculate product cost breakdown for '{product.name}'",
            ) from exc

        unit_price = _money(product.selling_price)
        unit_cost = _money(breakdown.total_cost)
        unit_profit = _money(unit_price - unit_cost)

        return OrderProductLine(
            product_id=product.id,
            quantity=line_input.quantity,
            product_name_snapshot=product.name,
            product_selling_price_snapshot=unit_price,
            product_cost_snapshot=unit_cost,
            product_profit_snapshot=unit_profit,
        )

    def _build_collection_line_snapshot(
        self,
        line_input: OrderCollectionLineInput,
    ) -> OrderCollectionLine:
        collection = self.collections.get_by_id(line_input.collection_id)
        if not collection:
            raise NotFoundError(f"Collection not found: {line_input.collection_id}")

        self._validate_collection_for_snapshot(collection)

        try:
            breakdown = calculate_breakdown_for_collection(collection)
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(
                f"Unable to calculate collection cost breakdown for '{collection.name}'",
            ) from exc

        unit_price = _money(collection.selling_price)
        unit_cost = _money(breakdown.total_cost)
        unit_profit = _money(unit_price - unit_cost)

        return OrderCollectionLine(
            collection_id=collection.id,
            quantity=line_input.quantity,
            collection_name_snapshot=collection.name,
            collection_selling_price_snapshot=unit_price,
            collection_cost_snapshot=unit_cost,
            collection_profit_snapshot=unit_profit,
        )

    @staticmethod
    def _validate_product_for_snapshot(product: Product) -> None:
        if not product.is_active:
            raise ValidationError(f"Product is inactive: {product.name}")
        if product.selling_price is None:
            raise ValidationError(f"Product '{product.name}' has no selling price")
        if not product.name.strip():
            raise ValidationError("Product name is required for order snapshot")

    @staticmethod
    def _validate_collection_for_snapshot(collection: Collection) -> None:
        if not collection.is_active:
            raise ValidationError(f"Collection is inactive: {collection.name}")
        if collection.selling_price is None:
            raise ValidationError(f"Collection '{collection.name}' has no selling price")
        if not collection.name.strip():
            raise ValidationError("Collection name is required for order snapshot")

    @staticmethod
    def _ensure_no_duplicate_product_ids(lines: list[OrderProductLineInput]) -> None:
        seen: set[uuid.UUID] = set()
        for line in lines:
            if line.product_id in seen:
                raise ValidationError("Duplicate product in order")
            seen.add(line.product_id)

    @staticmethod
    def _ensure_no_duplicate_collection_ids(lines: list[OrderCollectionLineInput]) -> None:
        seen: set[uuid.UUID] = set()
        for line in lines:
            if line.collection_id in seen:
                raise ValidationError("Duplicate collection in order")
            seen.add(line.collection_id)
