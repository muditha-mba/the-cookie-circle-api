"""Package fee helpers for internal reporting — never expose to customers."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from app.models.order import Order
from app.models.order_collection_line import OrderCollectionLine
from app.services.product_cost_service import _money


def package_fee_revenue_from_collection_lines(
    lines: Iterable[OrderCollectionLine],
) -> Decimal:
    total = Decimal("0")
    for line in lines:
        fee = line.package_fee_snapshot
        if fee is not None and fee > 0:
            total += fee * line.quantity
    return _money(total)


def package_fee_revenue_from_order(order: Order) -> Decimal:
    return package_fee_revenue_from_collection_lines(order.collection_lines)
