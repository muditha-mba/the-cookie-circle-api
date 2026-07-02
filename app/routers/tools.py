"""Admin utility tools."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.admin_access import can_view_financials
from app.dependencies.admin import get_current_admin_user, get_recipe_calculator_service
from app.models.user import User
from app.schemas.recipe_calculator import (
    RecipeCalculatorCalculateRequest,
    RecipeCalculatorProductOptionsResponse,
    RecipeCalculatorResponse,
)
from app.services.financial_redaction import redact_recipe_calculator_response
from app.services.recipe_calculator_service import RecipeCalculatorService

router = APIRouter(
    prefix="/tools",
    tags=["Tools"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get(
    "/recipe-calculator/products",
    response_model=RecipeCalculatorProductOptionsResponse,
)
def list_recipe_calculator_products(
    service: Annotated[RecipeCalculatorService, Depends(get_recipe_calculator_service)],
) -> RecipeCalculatorProductOptionsResponse:
    """List products eligible for recipe scaling (recipe lines + positive yield)."""
    return service.list_eligible_products()


@router.post("/recipe-calculator/calculate", response_model=RecipeCalculatorResponse)
def calculate_recipe(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    payload: RecipeCalculatorCalculateRequest,
    service: Annotated[RecipeCalculatorService, Depends(get_recipe_calculator_service)],
) -> RecipeCalculatorResponse:
    """Scale a product recipe to a target quantity."""
    include_costs = can_view_financials(current_user)
    result = service.calculate(payload, include_costs=include_costs)
    if not include_costs:
        return redact_recipe_calculator_response(result)
    return result
