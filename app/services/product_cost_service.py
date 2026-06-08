"""Product cost and profitability calculation engine."""

import uuid
from decimal import Decimal

from app.core.enums import ChargeType
from app.models.labour_charge import LabourCharge
from app.models.product import Product
from app.models.product_recipe_line import ProductRecipeLine
from app.models.tax_charge import TaxCharge
from app.models.utility_charge import UtilityCharge
from app.schemas.product import (
    AdditionalChargesBreakdown,
    ChargeBreakdownLine,
    IngredientBreakdown,
    ProductCostBreakdown,
    RecipeLineResponse,
)
from app.utils.costing import calculate_cost_per_unit

MONEY_PRECISION = Decimal("0.01")
RATIO_PRECISION = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION)


def _apply_charge(
    charge: UtilityCharge | LabourCharge | TaxCharge,
    selling_price: Decimal,
) -> ChargeBreakdownLine:
    """Apply a global charge to a product cost breakdown."""
    if charge.charge_type == ChargeType.FIXED:
        applied = _money(charge.amount)
    else:
        applied = _money((selling_price * charge.amount) / Decimal("100"))

    return ChargeBreakdownLine(
        id=charge.id,
        name=charge.name,
        charge_type=charge.charge_type.value,
        configured_amount=charge.amount,
        applied_cost=applied,
    )


def build_recipe_line_response(line: ProductRecipeLine) -> RecipeLineResponse:
    """Build a recipe line response with calculated line cost."""
    item = line.product_item
    cost_per_unit = calculate_cost_per_unit(item.purchase_price, item.purchase_quantity)
    line_cost = _money(line.quantity * cost_per_unit)
    return RecipeLineResponse(
        id=line.id or uuid.uuid4(),
        product_item_id=item.id,
        product_item_name=item.name,
        quantity=line.quantity,
        unit=item.purchase_unit,
        cost_per_unit=cost_per_unit,
        line_cost=line_cost,
    )


def calculate_product_cost_breakdown(
    *,
    selling_price: Decimal,
    buffer_amount: Decimal,
    yield_quantity: Decimal,
    recipe_lines: list[ProductRecipeLine],
    utility_charges: list[UtilityCharge],
    labour_charges: list[LabourCharge],
    tax_charges: list[TaxCharge],
) -> ProductCostBreakdown:
    """Calculate full product cost and profitability breakdown."""
    ingredient_lines = [build_recipe_line_response(line) for line in recipe_lines]
    ingredients_subtotal = _money(
        sum((line.line_cost for line in ingredient_lines), Decimal("0")),
    )

    utility_lines = [_apply_charge(c, selling_price) for c in utility_charges]
    labour_lines = [_apply_charge(c, selling_price) for c in labour_charges]
    tax_lines = [_apply_charge(c, selling_price) for c in tax_charges]

    additional_subtotal = _money(
        sum(
            (line.applied_cost for line in utility_lines + labour_lines + tax_lines),
            Decimal("0"),
        ),
    )

    buffer = _money(buffer_amount)
    total_cost = _money(ingredients_subtotal + additional_subtotal + buffer)
    selling = _money(selling_price)
    profit = _money(selling - total_cost)
    margin = (
        _money((profit / selling) * Decimal("100"))
        if selling > 0
        else Decimal("0.00")
    )
    yield_qty = yield_quantity
    cost_per_unit = _money(total_cost / yield_qty)
    profit_per_unit = _money(profit / yield_qty)

    return ProductCostBreakdown(
        ingredients=IngredientBreakdown(
            lines=ingredient_lines,
            subtotal=ingredients_subtotal,
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
        cost_per_unit=cost_per_unit,
        profit_per_unit=profit_per_unit,
    )


def calculate_breakdown_for_product(product: Product) -> ProductCostBreakdown:
    """Calculate breakdown from a loaded product model."""
    return calculate_product_cost_breakdown(
        selling_price=product.selling_price,
        buffer_amount=product.buffer_amount,
        yield_quantity=product.yield_quantity,
        recipe_lines=product.recipe_lines,
        utility_charges=product.utility_charges,
        labour_charges=product.labour_charges,
        tax_charges=product.tax_charges,
    )
