"""Collection cost and profitability calculation engine."""

import uuid
from decimal import Decimal

from app.models.collection_item_line import CollectionItemLine
from app.models.collection_product_line import CollectionProductLine
from app.models.labour_charge import LabourCharge
from app.models.product import Product
from app.models.tax_charge import TaxCharge
from app.models.utility_charge import UtilityCharge
from app.schemas.collection import (
    CollectionCostBreakdown,
    CollectionItemLineResponse,
    CollectionItemsBreakdown,
    CollectionProductLineResponse,
    CollectionProductsBreakdown,
)
from app.schemas.product import AdditionalChargesBreakdown
from app.services.product_cost_service import (
    _apply_charge,
    _money,
    calculate_breakdown_for_product,
)
from app.utils.costing import calculate_cost_per_unit


def build_collection_product_line_response(
    line: CollectionProductLine,
    *,
    unit_total_cost: Decimal,
) -> CollectionProductLineResponse:
    """Build a collection product line with cost contribution."""
    contribution = _money(unit_total_cost * line.quantity)
    return CollectionProductLineResponse(
        id=line.id or uuid.uuid4(),
        product_id=line.product.id,
        product_name=line.product.name,
        quantity=line.quantity,
        unit_total_cost=_money(unit_total_cost),
        cost_contribution=contribution,
    )


def build_collection_item_line_response(
    line: CollectionItemLine,
) -> CollectionItemLineResponse:
    """Build a packaging item line with applied cost."""
    item = line.product_item
    cost_per_unit = calculate_cost_per_unit(item.purchase_price, item.purchase_quantity)
    applied_cost = _money(line.quantity * cost_per_unit)
    return CollectionItemLineResponse(
        id=line.id or uuid.uuid4(),
        product_item_id=item.id,
        product_item_name=item.name,
        quantity=line.quantity,
        unit=item.purchase_unit,
        cost_per_unit=cost_per_unit,
        applied_cost=applied_cost,
    )


def calculate_collection_cost_breakdown(
    *,
    selling_price: Decimal,
    buffer_amount: Decimal,
    product_lines: list[CollectionProductLine],
    item_lines: list[CollectionItemLine],
    utility_charges: list[UtilityCharge],
    labour_charges: list[LabourCharge],
    tax_charges: list[TaxCharge],
) -> CollectionCostBreakdown:
    """Calculate full collection cost and profitability breakdown."""
    product_breakdown_lines: list[CollectionProductLineResponse] = []
    products_subtotal = Decimal("0")

    for line in product_lines:
        product_breakdown = calculate_breakdown_for_product(line.product)
        # Collection product quantities represent product units (cookies), so
        # contribution must use per-unit product cost, not full batch cost.
        unit_total = product_breakdown.cost_per_unit
        product_breakdown_lines.append(
            build_collection_product_line_response(line, unit_total_cost=unit_total),
        )
        products_subtotal += unit_total * line.quantity

    products_subtotal = _money(products_subtotal)

    item_breakdown_lines = [build_collection_item_line_response(line) for line in item_lines]
    items_subtotal = _money(
        sum((line.applied_cost for line in item_breakdown_lines), Decimal("0")),
    )

    selling = _money(selling_price)

    utility_lines = [_apply_charge(c, selling) for c in utility_charges]
    labour_lines = [_apply_charge(c, selling) for c in labour_charges]
    tax_lines = [_apply_charge(c, selling) for c in tax_charges]

    additional_subtotal = _money(
        sum(
            (line.applied_cost for line in utility_lines + labour_lines + tax_lines),
            Decimal("0"),
        ),
    )

    buffer = _money(buffer_amount)
    total_cost = _money(products_subtotal + items_subtotal + additional_subtotal + buffer)
    profit = _money(selling - total_cost)
    margin = (
        _money((profit / selling) * Decimal("100"))
        if selling > 0
        else Decimal("0.00")
    )

    return CollectionCostBreakdown(
        products=CollectionProductsBreakdown(
            lines=product_breakdown_lines,
            subtotal=products_subtotal,
        ),
        collection_items=CollectionItemsBreakdown(
            lines=item_breakdown_lines,
            subtotal=items_subtotal,
        ),
        additional_charges=AdditionalChargesBreakdown(
            utility_charges=utility_lines,
            labour_charges=labour_lines,
            tax_charges=tax_lines,
            subtotal=additional_subtotal,
        ),
        buffer_amount=buffer,
        total_cost=total_cost,
        selling_price=selling,
        profit_amount=profit,
        profit_margin_percent=margin,
    )


def calculate_breakdown_for_collection(collection) -> CollectionCostBreakdown:
    """Calculate breakdown from a loaded collection model."""
    return calculate_collection_cost_breakdown(
        selling_price=collection.selling_price,
        buffer_amount=collection.buffer_amount,
        product_lines=collection.product_lines,
        item_lines=collection.item_lines,
        utility_charges=collection.utility_charges,
        labour_charges=collection.labour_charges,
        tax_charges=collection.tax_charges,
    )
