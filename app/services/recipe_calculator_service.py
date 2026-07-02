"""Scale product recipes to arbitrary target quantities."""

import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.recipe_calculator import (
    RecipeCalculatorCalculateRequest,
    RecipeCalculatorCostSummary,
    RecipeCalculatorIngredientLine,
    RecipeCalculatorProductOption,
    RecipeCalculatorProductOptionsResponse,
    RecipeCalculatorResponse,
)
from app.services.product_cost_service import (
    MONEY_PRECISION,
    calculate_breakdown_for_product,
)
from app.utils.units import is_discrete_unit

QTY_PRECISION = Decimal("0.0001")
SCALE_PRECISION = Decimal("0.0001")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION)


def _quantize_quantity(value: Decimal) -> Decimal:
    return value.quantize(QTY_PRECISION)


def suggest_discrete_quantity(scaled_quantity: Decimal) -> int:
    """Round count/packaging units to a practical whole number for the kitchen."""
    if scaled_quantity <= 0:
        return 0

    rounded = int(scaled_quantity.to_integral_value(rounding=ROUND_HALF_UP))
    if rounded == 0:
        return 1
    return rounded


class RecipeCalculatorService:
    """Calculate scaled ingredient requirements for a single product."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.product_repo = ProductRepository(db)

    def list_eligible_products(self) -> RecipeCalculatorProductOptionsResponse:
        products = self.product_repo.list_recipe_calculator_eligible()
        return RecipeCalculatorProductOptionsResponse(
            products=[
                RecipeCalculatorProductOption(
                    id=product.id,
                    name=product.name,
                    yield_quantity=product.yield_quantity,
                )
                for product in products
            ],
        )

    def calculate(
        self,
        payload: RecipeCalculatorCalculateRequest,
        *,
        include_costs: bool,
    ) -> RecipeCalculatorResponse:
        product = self.product_repo.get_by_id(payload.product_id)
        if product is None:
            raise NotFoundError("Product not found")

        self._validate_product(product)

        scale = (payload.target_quantity / product.yield_quantity).quantize(SCALE_PRECISION)
        breakdown = calculate_breakdown_for_product(product) if include_costs else None

        ingredients: list[RecipeCalculatorIngredientLine] = []
        cost_lines_by_item_id: dict[uuid.UUID, object] = {}
        if breakdown is not None:
            cost_lines_by_item_id = {
                line.product_item_id: line for line in breakdown.ingredients.lines
            }

        for recipe_line in product.recipe_lines:
            item = recipe_line.product_item
            unit = item.purchase_unit
            scaled_quantity = _quantize_quantity(scale * recipe_line.quantity)
            discrete = is_discrete_unit(unit)
            cost_line = cost_lines_by_item_id.get(item.id)

            ingredients.append(
                RecipeCalculatorIngredientLine(
                    product_item_id=item.id,
                    product_item_name=item.name,
                    recipe_quantity=recipe_line.quantity,
                    scaled_quantity=scaled_quantity,
                    unit=unit,
                    is_discrete=discrete,
                    suggested_quantity=suggest_discrete_quantity(scaled_quantity)
                    if discrete
                    else None,
                    cost_per_unit=cost_line.cost_per_unit if cost_line else None,
                    scaled_line_cost=_money(scale * cost_line.line_cost) if cost_line else None,
                ),
            )

        cost_summary = None
        if breakdown is not None:
            cost_summary = RecipeCalculatorCostSummary(
                ingredients_subtotal=_money(scale * breakdown.ingredients.subtotal),
                buffer_amount=_money(scale * breakdown.buffer_amount),
                total_cost=_money(scale * breakdown.total_cost),
                cost_per_unit=_money(
                    (scale * breakdown.total_cost) / payload.target_quantity,
                ),
            )

        return RecipeCalculatorResponse(
            product_id=product.id,
            product_name=product.name,
            yield_quantity=product.yield_quantity,
            target_quantity=payload.target_quantity,
            scale_factor=scale,
            production_notes=product.production_notes,
            ingredients=ingredients,
            cost_summary=cost_summary,
        )

    @staticmethod
    def _validate_product(product: Product) -> None:
        if not product.recipe_lines:
            raise ValidationError(
                f"Product '{product.name}' has no recipe; cannot calculate ingredients.",
            )
        if product.yield_quantity <= 0:
            raise ValidationError(
                f"Product '{product.name}' has invalid recipe yield quantity.",
            )
