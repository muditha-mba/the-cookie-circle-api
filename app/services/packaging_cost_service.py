"""Packaging materials cost from collection configuration."""

from decimal import Decimal

from app.models.collection import Collection
from app.services.product_cost_service import _money
from app.utils.collection_packaging_fee import resolve_collection_packaging_fee
from app.utils.costing import calculate_cost_per_unit


def calculate_packaging_materials_cost_per_pack(
    collection: Collection,
    *,
    cookie_count: Decimal | None = None,
) -> Decimal:
    """
    Sum configured packaging item costs for one collection pack.

    Only when a packaging fee applies (package-type fee or legacy collection fee)
    are packaging materials included in order profitability.
    """
    count = cookie_count if cookie_count is not None else Decimal(collection.package_size)
    if resolve_collection_packaging_fee(collection, cookie_count=count) <= 0:
        return Decimal("0.00")

    total = Decimal("0")
    for line in collection.item_lines:
        item = line.product_item
        if item.purchase_quantity <= 0:
            continue
        cost_per_unit = calculate_cost_per_unit(item.purchase_price, item.purchase_quantity)
        total += line.quantity * cost_per_unit
    return _money(total)
