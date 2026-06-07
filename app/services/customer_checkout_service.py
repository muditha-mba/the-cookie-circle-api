"""Website checkout orchestration (guest + optional account)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import (
    CustomerSource,
    OrderSource,
    OrderStatus,
    OrderType,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.customer import Customer
from app.models.order import Order
from app.services.order_selection_snapshot import build_order_collection_line_selection
from app.models.order_status_event import OrderStatusEvent
from app.models.product import Product
from app.repositories.collection_repository import CollectionRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.delivery_area_repository import DeliveryAreaRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.schemas.business_settings import BusinessSettingsResponse
from app.schemas.client_ordering import (
    ClientCheckoutRequest,
    ClientCheckoutResponse,
    ClientOrderPreviewRequest,
    ClientOrderPreviewResponse,
    EmailAvailabilityResponse,
)
from app.schemas.order import OrderCollectionLineInput, OrderProductLineInput
from app.services.auth_service import AuthService
from app.services.business_setting_service import BusinessSettingService
from app.services.collection_selection_validator import CollectionSelectionValidator
from app.services.customer_delivery_date_service import (
    CATERING_MIN_COOKIE_QUANTITY,
    CustomerDeliveryDateService,
    WEEKLY_DELIVERY_EXPLANATION,
)
from app.services.delivery_fee_service import resolve_delivery_fee
from app.services.order_profitability_service import OrderProfitabilityService
from app.services.whatsapp_order_message_service import WhatsAppOrderMessageService
from app.utils.email import normalize_email


@dataclass(frozen=True)
class ValidatedCollectionLine:
    collection_id: uuid.UUID
    quantity: Decimal
    selection_rows: list[tuple[Product, Decimal]]


@dataclass(frozen=True)
class ValidatedProductLine:
    product_id: uuid.UUID
    quantity: Decimal
    product: Product


@dataclass(frozen=True)
class ValidatedOrderRequest:
    order_type: OrderType
    scheduled_date: date
    collection_lines: list[ValidatedCollectionLine]
    product_lines: list[ValidatedProductLine]


class CustomerCheckoutService:
    """Public checkout without payment gateway integration."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.collections = CollectionRepository(db)
        self.products = ProductRepository(db)
        self.customers = CustomerRepository(db)
        self.delivery_areas = DeliveryAreaRepository(db)
        self.orders = OrderRepository(db)
        self.users = UserRepository(db)
        self.settings = BusinessSettingService(db)
        self.profitability = OrderProfitabilityService(db)
        self.selection_validator = CollectionSelectionValidator(db)
        self.auth = AuthService(db)

    def check_email(self, email: str) -> EmailAvailabilityResponse:
        normalized = normalize_email(email)
        user = self.users.get_by_email(normalized)
        if user:
            return EmailAvailabilityResponse(
                email=normalized,
                exists=True,
                has_account=True,
                message="This email already has an account. Sign in, reset your password, or continue as guest.",
            )
        return EmailAvailabilityResponse(
            email=normalized,
            exists=False,
            has_account=False,
            message="Email is available.",
        )

    def preview(self, payload: ClientOrderPreviewRequest) -> ClientOrderPreviewResponse:
        validated = self._validate_request(payload)
        settings = self.settings.get_settings()
        delivery_area = self._get_delivery_area(payload.delivery_area_id)
        delivery_fee = resolve_delivery_fee(settings, delivery_area)
        snapshot_result = self._build_snapshots(payload, validated, delivery_fee)

        explanation = (
            WEEKLY_DELIVERY_EXPLANATION
            if payload.order_type == OrderType.WEEKLY_DELIVERY
            else None
        )
        return ClientOrderPreviewResponse(
            order_type=payload.order_type,
            scheduled_delivery_date=validated.scheduled_date,
            delivery_explanation=explanation,
            financials=snapshot_result.financials,
            collection_lines=[
                {
                    "collection_id": str(line.collection_id),
                    "quantity": str(line.quantity),
                    "cookies": [
                        {"product_id": str(product.id), "product_name": product.name, "quantity": str(qty)}
                        for product, qty in line.selection_rows
                    ],
                }
                for line in validated.collection_lines
            ],
            product_lines=[
                {
                    "product_id": str(snapshot.product_id),
                    "product_name": snapshot.product_name_snapshot,
                    "quantity": str(snapshot.quantity),
                    "unit_price": str(snapshot.product_selling_price_snapshot),
                    "line_total": str(
                        snapshot.product_selling_price_snapshot * snapshot.quantity
                    ),
                }
                for snapshot in snapshot_result.product_lines
            ],
        )

    def checkout(self, payload: ClientCheckoutRequest) -> ClientCheckoutResponse:
        if payload.create_account:
            if not payload.customer.email:
                raise ValidationError("Email is required to create an account.")
            if self.users.get_by_email(normalize_email(payload.customer.email)):
                raise ConflictError("An account with this email already exists.")

        validated = self._validate_request(payload)
        settings = self.settings.get_settings()
        self._validate_payment_method(settings, payload.payment_method)
        delivery_area = self._get_delivery_area(payload.delivery_area_id)
        delivery_fee = resolve_delivery_fee(settings, delivery_area)
        snapshot_result = self._build_snapshots(payload, validated, delivery_fee)

        customer = self._resolve_customer(payload)
        order = Order(
            order_number=self._generate_order_number(),
            customer_id=customer.id,
            delivery_area_id=delivery_area.id if delivery_area else None,
            source=OrderSource.WEBSITE,
            order_type=payload.order_type,
            event_name=payload.customer.event_name,
            payment_method=payload.payment_method,
            payment_status=PaymentStatus.PENDING,
            status=OrderStatus.PENDING,
            customer_notes=payload.customer.order_notes,
            requested_delivery_date=validated.scheduled_date,
            scheduled_delivery_date=validated.scheduled_date,
            delivery_contact_name=f"{payload.customer.first_name} {payload.customer.last_name}".strip(),
            delivery_phone_primary=payload.customer.phone,
            delivery_phone_secondary=payload.customer.phone_secondary,
            delivery_address_line_1=payload.customer.address_line_1,
            delivery_address_line_2=payload.customer.address_line_2,
            delivery_city=payload.customer.city,
            delivery_postal_code=payload.customer.postal_code,
            delivery_landmark=payload.customer.landmark,
            delivery_latitude=payload.customer.delivery_latitude,
            delivery_longitude=payload.customer.delivery_longitude,
        )
        self.profitability.apply_snapshots_to_order(order, snapshot_result)
        order.collection_lines = snapshot_result.collection_lines
        order.product_lines = snapshot_result.product_lines
        order.status_events = [OrderStatusEvent(status=OrderStatus.PENDING)]
        if validated.collection_lines:
            self._attach_selection_snapshots(order, validated.collection_lines)

        self.orders.create(order)
        self.db.flush()

        account_created = False
        verification_sent = False
        if payload.create_account and payload.customer.email and payload.account_password:
            user = self.users.create(
                email=normalize_email(payload.customer.email),
                password_hash=hash_password(payload.account_password),
                role=UserRole.CUSTOMER,
                first_name=payload.customer.first_name,
                last_name=payload.customer.last_name,
                email_verified=False,
            )
            customer.user_id = user.id
            customer.source = CustomerSource.REGISTERED
            customer.email = user.email
            self.auth.send_account_verification(user)
            account_created = True
            verification_sent = True

        self.db.commit()
        loaded = self.orders.get_by_id(order.id)
        assert loaded is not None

        whatsapp_url = WhatsAppOrderMessageService.build_whatsapp_url(loaded)
        return ClientCheckoutResponse(
            order_id=loaded.id,
            order_number=loaded.order_number,
            order_type=loaded.order_type,
            scheduled_delivery_date=loaded.scheduled_delivery_date,
            total_revenue_snapshot=loaded.total_revenue_snapshot,
            whatsapp_url=whatsapp_url,
            account_created=account_created,
            verification_email_sent=verification_sent,
            message="Order placed successfully. Complete your order on WhatsApp when ready.",
        )

    def _validate_request(self, payload: ClientOrderPreviewRequest) -> ValidatedOrderRequest:
        scheduled_date = CustomerDeliveryDateService.resolve_delivery_date(
            order_type=payload.order_type,
            requested_date=payload.requested_delivery_date,
        )
        if payload.order_type == OrderType.CATERING:
            product_lines = self._validate_catering_product_lines(payload.product_lines)
            return ValidatedOrderRequest(
                order_type=payload.order_type,
                scheduled_date=scheduled_date,
                collection_lines=[],
                product_lines=product_lines,
            )

        collection_lines = self._validate_weekly_collection_lines(payload.collection_lines)
        return ValidatedOrderRequest(
            order_type=payload.order_type,
            scheduled_date=scheduled_date,
            collection_lines=collection_lines,
            product_lines=[],
        )

    def _validate_weekly_collection_lines(
        self,
        lines: list,
    ) -> list[ValidatedCollectionLine]:
        validated: list[ValidatedCollectionLine] = []
        for line in lines:
            collection = self.collections.get_by_id(line.collection_id)
            if not collection or not collection.is_active or not collection.is_public:
                raise NotFoundError("Collection is not available for ordering.")
            selection_rows = self.selection_validator.validate(
                collection,
                selections=line.selections,
                line_quantity=line.quantity,
            )
            validated.append(
                ValidatedCollectionLine(
                    collection_id=line.collection_id,
                    quantity=line.quantity,
                    selection_rows=selection_rows,
                ),
            )
        return validated

    def _validate_catering_product_lines(self, lines: list) -> list[ValidatedProductLine]:
        validated: list[ValidatedProductLine] = []
        total_cookies = Decimal("0")
        seen_product_ids: set[uuid.UUID] = set()

        for line in lines:
            if line.product_id in seen_product_ids:
                raise ValidationError("Duplicate cookies are not allowed in catering orders.")
            seen_product_ids.add(line.product_id)

            product = self.products.get_by_id(line.product_id)
            if not product or not product.is_active or not product.is_public:
                raise NotFoundError("One or more selected cookies are not available for ordering.")

            total_cookies += line.quantity
            validated.append(
                ValidatedProductLine(
                    product_id=line.product_id,
                    quantity=line.quantity,
                    product=product,
                ),
            )

        if total_cookies < Decimal(CATERING_MIN_COOKIE_QUANTITY):
            raise ValidationError(
                f"Catering orders require at least {CATERING_MIN_COOKIE_QUANTITY} cookies.",
            )
        return validated

    def _build_snapshots(
        self,
        payload: ClientOrderPreviewRequest,
        validated: ValidatedOrderRequest,
        delivery_fee: Decimal,
    ):
        return self.profitability.build_order_snapshots(
            product_lines=[
                OrderProductLineInput(product_id=line.product_id, quantity=line.quantity)
                for line in validated.product_lines
            ],
            collection_lines=[
                OrderCollectionLineInput(
                    collection_id=line.collection_id,
                    quantity=line.quantity,
                    selections=next(
                        (
                            payload_line.selections
                            for payload_line in payload.collection_lines
                            if payload_line.collection_id == line.collection_id
                        ),
                        None,
                    ),
                )
                for line in validated.collection_lines
            ],
            delivery_fee=delivery_fee,
        )

    @staticmethod
    def _validate_payment_method(
        settings: BusinessSettingsResponse,
        payment_method: PaymentMethod,
    ) -> None:
        allowed: set[PaymentMethod] = set()
        if settings.cod_enabled:
            allowed.add(PaymentMethod.CASH_ON_DELIVERY)
        if settings.bank_transfer_enabled:
            allowed.add(PaymentMethod.BANK_TRANSFER)
        if settings.stripe_enabled:
            allowed.add(PaymentMethod.STRIPE)

        if not allowed:
            raise ValidationError("No payment methods are currently available.")
        if payment_method not in allowed:
            raise ValidationError("Selected payment method is not available.")

    def _resolve_customer(self, payload: ClientCheckoutRequest) -> Customer:
        email = normalize_email(payload.customer.email) if payload.customer.email else None
        customer = Customer(
            first_name=payload.customer.first_name,
            last_name=payload.customer.last_name,
            email=email,
            phone=payload.customer.phone,
            address_line_1=payload.customer.address_line_1,
            address_line_2=payload.customer.address_line_2,
            city=payload.customer.city,
            postal_code=payload.customer.postal_code,
            landmark=payload.customer.landmark,
            source=CustomerSource.GUEST,
            is_active=True,
        )
        self.customers.create(customer)
        self.db.flush()
        return customer

    @staticmethod
    def _attach_selection_snapshots(
        order: Order,
        validated_lines: list[ValidatedCollectionLine],
    ) -> None:
        line_by_collection = {line.collection_id: line for line in order.collection_lines}
        for validated in validated_lines:
            order_line = line_by_collection.get(validated.collection_id)
            if order_line is None:
                continue
            order_line.selections = [
                build_order_collection_line_selection(product=product, quantity=qty)
                for product, qty in validated.selection_rows
            ]

    def _get_delivery_area(self, area_id: uuid.UUID | None):
        if area_id is None:
            return None
        area = self.delivery_areas.get_by_id(area_id)
        if not area or not area.is_active:
            raise NotFoundError("Delivery area not found")
        return area

    def _generate_order_number(self) -> str:
        today = datetime.now(UTC).date().strftime("%Y%m%d")
        prefix = f"WEB-{today}-"
        count = self.orders.count_orders_for_prefix(prefix) + 1
        return f"{prefix}{count:04d}"
