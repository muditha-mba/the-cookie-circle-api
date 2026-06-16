"""Order profitability snapshot and analytics schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class OrderFinancialSnapshot(BaseModel):
    """Immutable order-level financial values captured at placement."""

    products_subtotal_snapshot: Decimal
    collections_subtotal_snapshot: Decimal
    delivery_fee_snapshot: Decimal
    delivery_cost_snapshot: Decimal
    package_fee_revenue_snapshot: Decimal
    packaging_cost_snapshot: Decimal
    products_cost_snapshot: Decimal
    collections_cost_snapshot: Decimal
    total_revenue_snapshot: Decimal
    total_cost_snapshot: Decimal
    total_profit_snapshot: Decimal
    margin_percentage_snapshot: Decimal


class TopProfitableOrderRow(BaseModel):
    """Order ranked by stored profit snapshot."""

    order_id: UUID
    order_number: str
    total_revenue_snapshot: Decimal
    total_profit_snapshot: Decimal
    margin_percentage_snapshot: Decimal
    created_at: datetime


class ProfitableProductSoldRow(BaseModel):
    """Aggregated product profitability from order line snapshots."""

    product_id: UUID
    product_name_snapshot: str
    units_sold: Decimal
    revenue_snapshot: Decimal
    cost_snapshot: Decimal
    profit_snapshot: Decimal


class ProfitableCollectionSoldRow(BaseModel):
    """Aggregated collection profitability from order line snapshots."""

    collection_id: UUID
    collection_name_snapshot: str
    units_sold: Decimal
    revenue_snapshot: Decimal
    cost_snapshot: Decimal
    profit_snapshot: Decimal
