"""Redact owner-level financial fields for clerk-admin responses."""

from decimal import Decimal

from app.schemas.customer_crm import (
    CustomerInsightsResponse,
    CustomerListItemResponse,
    CustomerOrderHistoryItem,
)
from app.schemas.dashboard import DashboardOverviewResponse
from app.schemas.order import (
    OrderCollectionLineResponse,
    OrderCollectionLineSelectionResponse,
    OrderDetailResponse,
    OrderPreviewResponse,
    OrderProductLineResponse,
    OrderSummaryResponse,
)
from app.schemas.pagination import PaginatedResponse
from app.schemas.collection import (
    CollectionDetailResponse,
    CollectionSummaryResponse,
)
from app.schemas.product import (
    AttachedChargeSummary,
    ProductDetailResponse,
    ProductSummaryResponse,
    RecipeLineResponse,
)
from app.schemas.production import (
    FulfillmentOverview,
    IngredientRequirementLine,
    IngredientRequirementsResponse,
    PackagingRequirementLine,
    PackagingRequirementsResponse,
    ProductionOrderSummary,
    ProductionSummaryResponse,
)
from app.schemas.product_item import ProductItemResponse
from app.schemas.purchase_planning import PurchasePlanLine, PurchasePlanResponse


def _zero() -> Decimal:
    return Decimal("0")


def redact_order_product_line(line: OrderProductLineResponse) -> OrderProductLineResponse:
    return line.model_copy(
        update={
            "product_cost_snapshot": _zero(),
            "product_profit_snapshot": _zero(),
            "line_cost_snapshot": _zero(),
            "line_profit_snapshot": _zero(),
            "margin_percentage_snapshot": _zero(),
        },
    )


def redact_order_collection_selection(
    selection: OrderCollectionLineSelectionResponse,
) -> OrderCollectionLineSelectionResponse:
    return selection.model_copy(
        update={
            "product_cost_snapshot": None,
            "product_profit_snapshot": None,
            "line_cost_snapshot": None,
            "line_profit_snapshot": None,
            "margin_percentage_snapshot": None,
            "profit_contribution_percentage_snapshot": None,
        },
    )


def redact_order_collection_line(line: OrderCollectionLineResponse) -> OrderCollectionLineResponse:
    return line.model_copy(
        update={
            "collection_cost_snapshot": _zero(),
            "collection_profit_snapshot": _zero(),
            "line_cost_snapshot": _zero(),
            "line_profit_snapshot": _zero(),
            "margin_percentage_snapshot": _zero(),
            "selections": [
                redact_order_collection_selection(selection)
                for selection in line.selections
            ],
        },
    )


def redact_order_summary(order: OrderSummaryResponse) -> OrderSummaryResponse:
    return order.model_copy(update={"total_profit_snapshot": _zero()})


def redact_order_detail(order: OrderDetailResponse) -> OrderDetailResponse:
    return order.model_copy(
        update={
            "financial_performance": None,
            "product_lines": [redact_order_product_line(line) for line in order.product_lines],
            "collection_lines": [
                redact_order_collection_line(line) for line in order.collection_lines
            ],
        },
    )


def redact_order_list(
    response: PaginatedResponse[OrderSummaryResponse],
) -> PaginatedResponse[OrderSummaryResponse]:
    return response.model_copy(
        update={"items": [redact_order_summary(item) for item in response.items]},
    )


def redact_order_preview(preview: OrderPreviewResponse) -> OrderPreviewResponse:
    return preview.model_copy(
        update={
            "total_cost_snapshot": _zero(),
            "total_profit_snapshot": _zero(),
            "margin_percentage_snapshot": _zero(),
            "product_lines": [redact_order_product_line(line) for line in preview.product_lines],
            "collection_lines": [
                redact_order_collection_line(line) for line in preview.collection_lines
            ],
        },
    )


def redact_product_summary(product: ProductSummaryResponse) -> ProductSummaryResponse:
    return product.model_copy(update={"buffer_amount": _zero()})


def redact_recipe_line(line: RecipeLineResponse) -> RecipeLineResponse:
    return line.model_copy(update={"cost_per_unit": _zero(), "line_cost": _zero()})


def redact_attached_charge(charge: AttachedChargeSummary) -> AttachedChargeSummary:
    return charge.model_copy(update={"amount": _zero()})


def redact_product_detail(product: ProductDetailResponse) -> ProductDetailResponse:
    return product.model_copy(
        update={
            "buffer_amount": _zero(),
            "cost_breakdown": None,
            "recipe_lines": [redact_recipe_line(line) for line in product.recipe_lines],
            "utility_charges": [redact_attached_charge(c) for c in product.utility_charges],
            "labour_charges": [redact_attached_charge(c) for c in product.labour_charges],
            "tax_charges": [redact_attached_charge(c) for c in product.tax_charges],
        },
    )


def redact_product_item(item: ProductItemResponse) -> ProductItemResponse:
    return item.model_copy(update={"cost_per_unit": _zero()})


def redact_product_item_list(
    response: PaginatedResponse[ProductItemResponse],
) -> PaginatedResponse[ProductItemResponse]:
    return response.model_copy(
        update={"items": [redact_product_item(item) for item in response.items]},
    )


def redact_product_list(
    response: PaginatedResponse[ProductSummaryResponse],
) -> PaginatedResponse[ProductSummaryResponse]:
    return response.model_copy(
        update={"items": [redact_product_summary(item) for item in response.items]},
    )


def redact_dashboard_overview(
    overview: DashboardOverviewResponse,
) -> DashboardOverviewResponse:
    return overview.model_copy(
        update={
            "today_snapshot": overview.today_snapshot.model_copy(
                update={"revenue_today": _zero()},
            ),
        },
    )


def redact_customer_list_item(customer: CustomerListItemResponse) -> CustomerListItemResponse:
    return customer.model_copy(update={"lifetime_spend": _zero()})


def redact_customer_list(
    response: PaginatedResponse[CustomerListItemResponse],
) -> PaginatedResponse[CustomerListItemResponse]:
    return response.model_copy(
        update={"items": [redact_customer_list_item(item) for item in response.items]},
    )


def redact_customer_insights(insights: CustomerInsightsResponse) -> CustomerInsightsResponse:
    return insights.model_copy(
        update={
            "lifetime_spend": _zero(),
            "average_order_value": _zero(),
        },
    )


def redact_customer_order_row(row: CustomerOrderHistoryItem) -> CustomerOrderHistoryItem:
    return row.model_copy(update={"total_profit_snapshot": _zero()})


def redact_collection_detail(collection: CollectionDetailResponse) -> CollectionDetailResponse:
    return collection.model_copy(
        update={
            "utility_charges": [redact_attached_charge(c) for c in collection.utility_charges],
            "labour_charges": [redact_attached_charge(c) for c in collection.labour_charges],
            "tax_charges": [redact_attached_charge(c) for c in collection.tax_charges],
        },
    )


def redact_collection_list(
    response: PaginatedResponse[CollectionSummaryResponse],
) -> PaginatedResponse[CollectionSummaryResponse]:
    return response


def redact_production_order_summary(summary: ProductionOrderSummary) -> ProductionOrderSummary:
    return summary.model_copy(update={"total_profit": _zero()})


def redact_ingredient_line(line: IngredientRequirementLine) -> IngredientRequirementLine:
    return line.model_copy(update={"estimated_cost": _zero()})


def redact_packaging_line(line: PackagingRequirementLine) -> PackagingRequirementLine:
    return line.model_copy(update={"estimated_cost": _zero()})


def redact_fulfillment_overview(overview: FulfillmentOverview) -> FulfillmentOverview:
    groups = []
    for group in overview.groups:
        groups.append(
            group.model_copy(
                update={
                    "orders": [
                        order.model_copy(update={"total_profit_snapshot": _zero()})
                        for order in group.orders
                    ],
                },
            ),
        )
    return overview.model_copy(update={"groups": groups})


def redact_ingredient_requirements(
    response: IngredientRequirementsResponse,
) -> IngredientRequirementsResponse:
    return response.model_copy(
        update={"items": [redact_ingredient_line(item) for item in response.items]},
    )


def redact_packaging_requirements(
    response: PackagingRequirementsResponse,
) -> PackagingRequirementsResponse:
    return response.model_copy(
        update={"items": [redact_packaging_line(item) for item in response.items]},
    )


def redact_purchase_plan_line(line: PurchasePlanLine) -> PurchasePlanLine:
    return line.model_copy(update={"estimated_cost": _zero()})


def redact_purchase_plan(plan: PurchasePlanResponse) -> PurchasePlanResponse:
    return plan.model_copy(
        update={"items": [redact_purchase_plan_line(item) for item in plan.items]},
    )


def redact_production_summary(summary: ProductionSummaryResponse) -> ProductionSummaryResponse:
    return summary.model_copy(
        update={
            "order_summary": redact_production_order_summary(summary.order_summary),
            "ingredient_requirements": [
                redact_ingredient_line(row) for row in summary.ingredient_requirements
            ],
            "packaging_requirements": [
                redact_packaging_line(row) for row in summary.packaging_requirements
            ],
            "fulfillment": redact_fulfillment_overview(summary.fulfillment),
        },
    )
