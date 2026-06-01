"""Production planning API schemas."""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import OrderStatus


class ProductionBatchOption(BaseModel):
    """Selectable delivery / production batch date."""

    delivery_date: date
    order_count: int
    label: str
    is_delivery_day_batch: bool


class ProductionOrderSummary(BaseModel):
    """Aggregated order metrics from financial snapshots."""

    delivery_date: date
    total_orders: int
    total_customers: int
    total_products_ordered: Decimal
    total_collections_ordered: Decimal
    total_revenue: Decimal
    total_profit: Decimal
    excluded_draft_and_cancelled: bool = True


class ProductDemandLine(BaseModel):
    """Required product quantity for a production batch."""

    product_id: uuid.UUID
    product_name: str
    quantity: Decimal


class IngredientRequirementLine(BaseModel):
    """Ingredient demand derived from current product recipes.

    Structured for future Inventory module consumption.
    """

    product_item_id: uuid.UUID
    product_item_name: str
    quantity: Decimal
    unit: str
    estimated_cost: Decimal


class PackagingRequirementLine(BaseModel):
    """Packaging demand derived from current collection configurations.

    Structured for future Inventory module consumption.
    """

    product_item_id: uuid.UUID
    product_item_name: str
    item_type_name: str | None = None
    quantity: Decimal
    unit: str
    estimated_cost: Decimal


class FulfillmentOrderItem(BaseModel):
    """Order row for fulfillment status grouping."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    customer_name: str
    status: OrderStatus
    total_revenue_snapshot: Decimal
    total_profit_snapshot: Decimal


class FulfillmentStatusGroup(BaseModel):
    """Orders grouped by fulfillment status."""

    status: OrderStatus
    orders: list[FulfillmentOrderItem]


class FulfillmentOverview(BaseModel):
    """All orders for a delivery date grouped by status."""

    delivery_date: date
    groups: list[FulfillmentStatusGroup]
    total_orders: int


class ProductionSummaryResponse(BaseModel):
    """Full production planning summary for a delivery date."""

    delivery_date: date
    order_summary: ProductionOrderSummary
    product_demand: list[ProductDemandLine]
    ingredient_requirements: list[IngredientRequirementLine]
    packaging_requirements: list[PackagingRequirementLine]
    fulfillment: FulfillmentOverview


class IngredientRequirementsResponse(BaseModel):
    delivery_date: date
    items: list[IngredientRequirementLine]


class PackagingRequirementsResponse(BaseModel):
    delivery_date: date
    items: list[PackagingRequirementLine]


class ProductDemandResponse(BaseModel):
    delivery_date: date
    items: list[ProductDemandLine]


class ProductionBatchesResponse(BaseModel):
    delivery_day: str = Field(description="Configured weekly delivery day from business settings")
    batches: list[ProductionBatchOption]
