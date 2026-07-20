"""Client-facing ordering API schemas."""

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.enums import OrderType, PaymentMethod, Weekday
from app.schemas.attribution import MarketingAttributionInput
from app.schemas.order_profitability import OrderFinancialSnapshot


class CollectionCookieSelectionInput(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0)


class ClientCollectionLineInput(BaseModel):
    collection_id: UUID
    quantity: Decimal = Field(gt=0, default=Decimal("1"))
    selections: list[CollectionCookieSelectionInput] | None = None


class ClientProductLineInput(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0)


class DeliveryScheduleCopyResponse(BaseModel):
    """Public delivery schedule messaging from business settings."""

    order_cutoff_day: Weekday
    delivery_day: Weekday
    order_cutoff_day_label: str
    delivery_day_label: str
    explanation: str
    reserve_before_message: str
    preorder_note: str
    order_before_message: str
    cutoff_period_label: str
    cutoff_timing_note: str
    fresh_delivery_message: str


class WeeklyDeliveryInfoResponse(DeliveryScheduleCopyResponse):
    order_type: OrderType = OrderType.WEEKLY_DELIVERY
    calculated_delivery_date: date
    is_before_cutoff: bool
    explanation: str


class CateringConstraintsResponse(BaseModel):
    order_type: OrderType = OrderType.CATERING
    minimum_cookie_quantity: int
    minimum_days_ahead: int
    earliest_delivery_date: date
    packaging_fee_mode: Literal["flat", "per_cookie"] = "flat"
    packaging_fee_amount: Decimal = Decimal("0")
    packaging_fee_included: bool = False

class ClientCatalogProductCategory(BaseModel):
    id: UUID
    code: str
    name: str


class ClientCatalogProduct(BaseModel):
    id: UUID
    name: str
    description: str | None
    category_id: UUID
    category_code: str
    category_name: str
    selling_price_per_unit: Decimal


class ClientCatalogCollection(BaseModel):
    id: UUID
    name: str
    description: str | None
    package_code: str
    package_name: str
    package_size: int
    min_quantity: int
    max_quantity: int
    packaging_fee_mode: Literal["flat", "per_cookie"]
    packaging_fee_amount: Decimal
    allowed_category_ids: list[UUID]
    premium_packaging_included: bool = Field(
        description=(
            "Whether this collection's price includes a packaging fee "
            "(amount may be shown in quote/checkout)."
        ),
    )


class ClientCollectionQuoteRequest(BaseModel):
    collection_id: UUID
    selections: list[CollectionCookieSelectionInput]


class ClientCollectionQuoteResponse(BaseModel):
    unit_price: Decimal
    cookie_subtotal: Decimal
    packaging_fee: Decimal
    packaging_fee_mode: Literal["flat", "per_cookie"]


class ClientCatalogPackage(BaseModel):
    code: str
    name: str
    description: str | None
    badge_tone: str
    min_quantity: int
    max_quantity: int
    packaging_fee_mode: Literal["flat", "per_cookie"]
    packaging_fee_amount: Decimal
    collections: list[ClientCatalogCollection]


class ClientCatalogResponse(BaseModel):
    packages: list[ClientCatalogPackage]
    selectable_products: list[ClientCatalogProduct]


class ClientPaymentMethodOption(BaseModel):
    code: PaymentMethod
    label: str


class ClientCheckoutOptionsResponse(BaseModel):
    use_fixed_delivery_fee: bool
    fixed_delivery_fee: str
    payment_methods: list[ClientPaymentMethodOption]


class ClientDeliveryAreaOption(BaseModel):
    id: UUID
    name: str
    delivery_fee: str
    pickup_only: bool


class ClientOrderPreviewRequest(BaseModel):
    order_type: OrderType
    delivery_area_id: UUID | None = None
    requested_delivery_date: date | None = None
    collection_lines: list[ClientCollectionLineInput] = Field(default_factory=list)
    product_lines: list[ClientProductLineInput] = Field(default_factory=list)
    customer_id: UUID | None = None  # Optional: authenticated customer for discount resolution

    @model_validator(mode="after")
    def validate_order_type_rules(self) -> "ClientOrderPreviewRequest":
        if self.order_type == OrderType.CATERING and self.requested_delivery_date is None:
            raise ValueError("Catering orders require a delivery date.")
        if self.order_type == OrderType.WEEKLY_DELIVERY and self.requested_delivery_date is not None:
            raise ValueError("Weekly delivery date is assigned automatically.")
        if self.order_type == OrderType.CATERING:
            if not self.product_lines:
                raise ValueError("At least one cookie is required for catering orders.")
            if self.collection_lines:
                raise ValueError("Catering orders cannot include collection lines.")
        if self.order_type == OrderType.WEEKLY_DELIVERY:
            if not self.collection_lines:
                raise ValueError("At least one collection is required.")
            if self.product_lines:
                raise ValueError("Weekly delivery orders cannot include product lines.")
        return self


class ClientOrderPreviewResponse(BaseModel):
    order_type: OrderType
    scheduled_delivery_date: date
    delivery_explanation: str | None = None
    financials: OrderFinancialSnapshot
    collection_lines: list[dict[str, object]] = Field(default_factory=list)
    product_lines: list[dict[str, object]] = Field(default_factory=list)


class EmailAvailabilityResponse(BaseModel):
    email: EmailStr
    exists: bool
    has_account: bool
    message: str


class ClientCheckoutAddress(BaseModel):
    address_line_1: str = Field(min_length=1, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    landmark: str | None = Field(default=None, max_length=255)


class ClientCheckoutCustomer(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=5, max_length=50)
    phone_secondary: str | None = Field(default=None, max_length=50)
    shipping_address: ClientCheckoutAddress
    billing_same_as_shipping: bool = True
    billing_address: ClientCheckoutAddress | None = None
    delivery_latitude: Decimal | None = None
    delivery_longitude: Decimal | None = None
    order_notes: str | None = Field(default=None, max_length=5000)
    event_name: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_billing_address(self) -> "ClientCheckoutCustomer":
        if self.billing_same_as_shipping:
            return self
        if self.billing_address is None:
            raise ValueError("Billing address is required when it differs from shipping.")
        return self

    @field_validator("delivery_latitude", mode="before")
    @classmethod
    def normalize_latitude(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        try:
            dec = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Map pin latitude must be a valid number.") from exc
        if dec < Decimal("-90") or dec > Decimal("90"):
            raise ValueError("Map pin latitude must be between -90 and 90.")
        return dec.quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP)

    @field_validator("delivery_longitude", mode="before")
    @classmethod
    def normalize_longitude(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        try:
            dec = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Map pin longitude must be a valid number.") from exc
        if dec < Decimal("-180") or dec > Decimal("180"):
            raise ValueError("Map pin longitude must be between -180 and 180.")
        return dec.quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP)


class ClientCheckoutRequest(ClientOrderPreviewRequest):
    customer: ClientCheckoutCustomer
    delivery_area_id: UUID
    payment_method: PaymentMethod = PaymentMethod.CASH_ON_DELIVERY
    create_account: bool = False
    account_password: str | None = Field(default=None, min_length=8, max_length=128)
    captcha_token: str | None = Field(default=None, max_length=4096)
    attribution: MarketingAttributionInput | None = None

    @model_validator(mode="after")
    def account_password_required(self) -> "ClientCheckoutRequest":
        if self.create_account and not self.account_password:
            raise ValueError("Password is required when creating an account.")
        if self.order_type == OrderType.CATERING and not self.customer.event_name:
            raise ValueError("Event name is required for catering orders.")
        return self


class ClientBankTransferInstructions(BaseModel):
    bank_name: str
    account_name: str
    account_number: str
    branch: str
    instructions: str
    amount: str
    order_number: str


class ClientCheckoutResponse(BaseModel):
    order_id: UUID
    order_number: str
    order_type: OrderType
    scheduled_delivery_date: date
    total_revenue_snapshot: Decimal
    order_details_message: str | None = None
    whatsapp_open_url: str | None = None
    account_order_url: str | None = None
    bank_transfer_instructions: ClientBankTransferInstructions | None = None
    redirect_to: Literal["order_success", "online_payment"]
    # Present only when redirect_to == "online_payment".
    # The client navigates the browser to this URL; the API endpoint at this URL
    # serves an HTML page with an auto-submitting form directed to WebXPay.
    payment_initiate_url: str | None = None
    account_created: bool = False
    verification_email_sent: bool = False
    message: str
