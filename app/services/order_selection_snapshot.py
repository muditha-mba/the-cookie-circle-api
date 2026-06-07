"""Helpers for persisting per-cookie selection snapshots on orders."""

from __future__ import annotations

from decimal import Decimal

from app.models.order_collection_line_selection import OrderCollectionLineSelection
from app.models.product import Product
from app.services.package_pricing_service import unit_cost, unit_selling_price
from app.services.product_cost_service import _money


def build_order_collection_line_selection(
    *,
    product: Product,
    quantity: Decimal,
) -> OrderCollectionLineSelection:
    """Capture per-cookie unit financial snapshots at order time."""
    selling = unit_selling_price(product)
    cost = unit_cost(product)
    profit = _money(selling - cost)

    return OrderCollectionLineSelection(
        product_id=product.id,
        quantity=quantity,
        product_name_snapshot=product.name,
        is_premium_snapshot=product.is_premium,
        product_selling_price_snapshot=selling,
        product_cost_snapshot=cost,
        product_profit_snapshot=profit,
    )
