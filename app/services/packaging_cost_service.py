"""Packaging materials cost from collection configuration."""

from decimal import Decimal

from app.models.collection import Collection
from app.services.product_cost_service import _money
from app.utils.costing import calculate_cost_per_unit


def calculate_packaging_materials_cost_per_pack(collection: Collection) -> Decimal:
    """
    Sum configured packaging item costs for one collection pack.

    Only collections that charge a package fee include packaging materials in
    order profitability — basic Mix & Match packs keep packaging out of this
    snapshot even when production items are configured on the collection.
    """
    if collection.package_fee <= 0:
        return Decimal("0.00")

    total = Decimal("0")
    for line in collection.item_lines:
        item = line.product_item
        if item.purchase_quantity <= 0:
            continue
        cost_per_unit = calculate_cost_per_unit(item.purchase_price, item.purchase_quantity)
        total += line.quantity * cost_per_unit
    return _money(total)
