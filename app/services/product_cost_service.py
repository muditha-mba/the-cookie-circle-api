"""Product cost and profitability calculation engine."""

import uuid
from decimal import Decimal

from app.models.product import Product
from app.models.product_recipe_line import ProductRecipeLine
from app.schemas.product import (
    IngredientBreakdown,
    ProductCostBreakdown,
    RecipeLineResponse,
)
from app.utils.costing import calculate_cost_per_unit

MONEY_PRECISION = Decimal("0.01")
RATIO_PRECISION = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION)


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
) -> ProductCostBreakdown:
    """Calculate full product cost and profitability breakdown (ingredients + buffer only).

    Utility and labour overheads are tracked at the business level as monthly overhead
    entries, not allocated per product. Taxes are applied at the order level.
    """
    ingredient_lines = [build_recipe_line_response(line) for line in recipe_lines]
    ingredients_subtotal = _money(
        sum((line.line_cost for line in ingredient_lines), Decimal("0")),
    )

    buffer = _money(buffer_amount)
    total_cost = _money(ingredients_subtotal + buffer)
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
    )
