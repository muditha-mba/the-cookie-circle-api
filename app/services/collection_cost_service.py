"""Collection cost and profitability calculation engine."""

import uuid
from decimal import Decimal

from app.models.collection_item_line import CollectionItemLine
from app.models.collection_product_line import CollectionProductLine
from app.services.product_cost_service import (
    _money,
    calculate_breakdown_for_product,
)
from app.utils.costing import calculate_cost_per_unit


def calculate_collection_ingredient_cost(product_lines: list[CollectionProductLine]) -> Decimal:
    """Calculate total ingredient cost from all collection product lines."""
    total = Decimal("0")
    for line in product_lines:
        breakdown = calculate_breakdown_for_product(line.product)
        total += breakdown.cost_per_unit * line.quantity
    return _money(total)


def calculate_collection_packaging_cost(item_lines: list[CollectionItemLine]) -> Decimal:
    """Calculate total packaging material cost from item lines."""
    total = Decimal("0")
    for line in item_lines:
        item = line.product_item
        cost_per_unit = calculate_cost_per_unit(item.purchase_price, item.purchase_quantity)
        total += cost_per_unit * line.quantity
    return _money(total)
