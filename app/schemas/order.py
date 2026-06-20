"""Order Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.enums import OrderSource, OrderStatus, OrderType, PaymentMethod, PaymentStatus
from app.schemas.client_ordering import CollectionCookieSelectionInput
from app.schemas.delivery_area import DeliveryAreaSummary
from app.schemas.order_profitability import OrderFinancialSnapshot
from app.schemas.order_review import OrderReviewSummaryEmbed


class OrderProductLineInput(BaseModel):
    """Product line for create/preview."""

    product_id: UUID
    quantity: Decimal = Field(gt=0)


class OrderCollectionLineInput(BaseModel):
    """Collection line for create/preview."""

    collection_id: UUID
    quantity: Decimal = Field(gt=0)
    selections: list[CollectionCookieSelectionInput] | None = None


class OrderBillingFields(BaseModel):
    """Billing address snapshot on an order."""

    billing_same_as_shipping: bool = True
    billing_address_line_1: str | None = Field(default=None, max_length=255)
    billing_address_line_2: str | None = Field(default=None, max_length=255)
    billing_city: str | None = Field(default=None, max_length=100)
    billing_postal_code: str | None = Field(default=None, max_length=20)
    billing_landmark: str | None = Field(default=None, max_length=255)


class OrderDeliveryFields(BaseModel):
    """Delivery contact and address on an order."""

    delivery_contact_name: str | None = Field(default=None, max_length=200)
    delivery_phone_primary: str | None = Field(default=None, max_length=50)
    delivery_phone_secondary: str | None = Field(default=None, max_length=50)
    delivery_address_line_1: str | None = Field(default=None, max_length=255)
    delivery_address_line_2: str | None = Field(default=None, max_length=255)
    delivery_city: str | None = Field(default=None, max_length=100)
    delivery_postal_code: str | None = Field(default=None, max_length=20)
    delivery_landmark: str | None = Field(default=None, max_length=255)
    delivery_notes: str | None = Field(default=None, max_length=5000)
    delivery_latitude: Decimal | None = None
    delivery_longitude: Decimal | None = None


class OrderCreate(OrderDeliveryFields):
    """Create order request."""

    customer_id: UUID
    delivery_area_id: UUID | None = None
    source: OrderSource
    payment_method: PaymentMethod
    payment_status: PaymentStatus = PaymentStatus.PENDING
    status: OrderStatus = OrderStatus.PENDING
    customer_notes: str | None = Field(default=None, max_length=5000)
    internal_notes: str | None = Field(default=None, max_length=5000)
    requested_delivery_date: date
    product_lines: list[OrderProductLineInput] = Field(default_factory=list)
    collection_lines: list[OrderCollectionLineInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_at_least_one_line(self) -> "OrderCreate":
        if not self.product_lines and not self.collection_lines:
            raise ValueError("At least one product or collection line is required")
        return self


class OrderUpdate(OrderDeliveryFields):
    """Update order request."""

    delivery_area_id: UUID | None = None
    source: OrderSource | None = None
    payment_method: PaymentMethod | None = None
    payment_status: PaymentStatus | None = None
    status: OrderStatus | None = None
    customer_notes: str | None = Field(default=None, max_length=5000)
    internal_notes: str | None = Field(default=None, max_length=5000)
    requested_delivery_date: date | None = None
    scheduled_delivery_date: date | None = None
    product_lines: list[OrderProductLineInput] | None = None
    collection_lines: list[OrderCollectionLineInput] | None = None


class OrderProductLineResponse(BaseModel):
    """Product line with immutable snapshots (quantities applied for line totals)."""

    id: UUID
    product_id: UUID
    quantity: Decimal
    product_name_snapshot: str
    product_selling_price_snapshot: Decimal
    product_cost_snapshot: Decimal
    product_profit_snapshot: Decimal
    line_revenue_snapshot: Decimal
    line_cost_snapshot: Decimal
    line_profit_snapshot: Decimal
    margin_percentage_snapshot: Decimal

    model_config = {"from_attributes": True}


class OrderCollectionLineSelectionResponse(BaseModel):
    """Per-cookie selection snapshot on a collection line."""

    id: UUID
    product_id: UUID
    quantity: Decimal
    product_name_snapshot: str
    is_premium_snapshot: bool
    product_selling_price_snapshot: Decimal | None = None
    product_cost_snapshot: Decimal | None = None
    product_profit_snapshot: Decimal | None = None
    line_revenue_snapshot: Decimal | None = None
    line_cost_snapshot: Decimal | None = None
    line_profit_snapshot: Decimal | None = None
    margin_percentage_snapshot: Decimal | None = None
    profit_contribution_percentage_snapshot: Decimal | None = None

    model_config = {"from_attributes": True}


class OrderCollectionLineResponse(BaseModel):
    """Collection line with immutable snapshots (quantities applied for line totals)."""

    id: UUID
    collection_id: UUID
    quantity: Decimal
    collection_name_snapshot: str
    collection_selling_price_snapshot: Decimal
    collection_cost_snapshot: Decimal
    collection_profit_snapshot: Decimal
    package_fee_snapshot: Decimal | None = None
    cookies_subtotal_snapshot: Decimal | None = None
    total_cookies_per_pack: Decimal | None = None
    line_revenue_snapshot: Decimal
    line_cost_snapshot: Decimal
    line_profit_snapshot: Decimal
    margin_percentage_snapshot: Decimal
    selections: list[OrderCollectionLineSelectionResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class OrderStatusEventResponse(BaseModel):
    """Status timeline entry."""

    id: UUID
    status: OrderStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderCustomerSummary(BaseModel):
    """Customer summary embedded in order responses."""

    id: UUID
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    postal_code: str | None = None
    landmark: str | None = None

    model_config = {"from_attributes": True}


class OrderFinancialPerformance(BaseModel):
    """Historical financial snapshot for display — values never recalculated on read."""

    snapshot: OrderFinancialSnapshot
    is_historical_snapshot: bool = True


class OrderLifecycleTimestamps(BaseModel):
    """Status lifecycle timestamps."""

    confirmed_at: datetime | None
    preparing_at: datetime | None
    ready_at: datetime | None
    delivered_at: datetime | None
    cancelled_at: datetime | None


class OrderInventoryConsumptionSummary(BaseModel):
    """Inventory consumption state for an order."""

    consumed_at: datetime | None
    applied_proposal_id: UUID | None
    pending_proposal_id: UUID | None


class OrderSummaryResponse(BaseModel):
    """Order list item."""

    id: UUID
    order_number: str
    customer_id: UUID
    customer_name: str
    order_type: OrderType
    source: OrderSource
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    status: OrderStatus
    requested_delivery_date: date
    scheduled_delivery_date: date
    delivery_area: DeliveryAreaSummary | None = None
    total_revenue_snapshot: Decimal
    total_profit_snapshot: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailResponse(OrderDeliveryFields, OrderBillingFields):
    """Full order detail."""

    id: UUID
    order_number: str
    customer: OrderCustomerSummary
    delivery_area: DeliveryAreaSummary | None
    order_type: OrderType
    event_name: str | None = None
    source: OrderSource
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    status: OrderStatus
    customer_notes: str | None
    internal_notes: str | None
    requested_delivery_date: date
    scheduled_delivery_date: date
    delivery_fee_snapshot: Decimal
    delivery_cost_snapshot: Decimal
    package_fee_revenue_snapshot: Decimal
    packaging_cost_snapshot: Decimal
    total_tax_snapshot: Decimal
    tax_lines_snapshot: list
    total_revenue_snapshot: Decimal
    financial_performance: OrderFinancialPerformance | None = None
    product_lines: list[OrderProductLineResponse]
    collection_lines: list[OrderCollectionLineResponse]
    status_timeline: list[OrderStatusEventResponse]
    lifecycle: OrderLifecycleTimestamps
    inventory_consumption: OrderInventoryConsumptionSummary
    customer_review: OrderReviewSummaryEmbed | None = None
    created_at: datetime
    updated_at: datetime


class OrderPreviewRequest(BaseModel):
    """Preview order financials without persisting (live calculation)."""

    delivery_area_id: UUID | None = None
    product_lines: list[OrderProductLineInput] = Field(default_factory=list)
    collection_lines: list[OrderCollectionLineInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_at_least_one_line(self) -> "OrderPreviewRequest":
        if not self.product_lines and not self.collection_lines:
            raise ValueError("At least one product or collection line is required")
        return self


class OrderPreviewResponse(BaseModel):
    """Preview totals and line breakdown (not persisted)."""

    products_subtotal_snapshot: Decimal
    collections_subtotal_snapshot: Decimal
    delivery_fee_snapshot: Decimal
    delivery_cost_snapshot: Decimal
    package_fee_revenue_snapshot: Decimal
    packaging_cost_snapshot: Decimal
    products_cost_snapshot: Decimal
    collections_cost_snapshot: Decimal
    total_tax_snapshot: Decimal
    tax_lines_snapshot: list
    total_revenue_snapshot: Decimal
    total_cost_snapshot: Decimal
    total_profit_snapshot: Decimal
    margin_percentage_snapshot: Decimal
    product_lines: list[OrderProductLineResponse]
    collection_lines: list[OrderCollectionLineResponse]
