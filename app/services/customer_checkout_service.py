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
from app.models.delivery_area import DeliveryArea
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
from app.services.client_payment_options import validate_client_payment_method
from app.schemas.client_ordering import (
    ClientCheckoutRequest,
    ClientCheckoutResponse,
    ClientCollectionQuoteRequest,
    ClientCollectionQuoteResponse,
    ClientOrderPreviewRequest,
    ClientOrderPreviewResponse,
    EmailAvailabilityResponse,
)
from app.services.package_pricing_service import calculate_package_selling_price
from app.schemas.order import OrderCollectionLineInput, OrderProductLineInput
from app.services.auth_service import AuthService
from app.services.customer_attribution_service import CustomerAttributionService
from app.services.email import get_email_service
from app.services.email.delivery import send_email_safely
from app.services.delivery_schedule_copy_service import (
    get_delivery_schedule_config,
    get_delivery_schedule_copy,
)
from app.services.order_notification_service import notify_team_new_order
from app.services.customer_identity_service import CustomerIdentityService
from app.services.business_setting_service import BusinessSettingService
from app.services.checkout_follow_up import (
    assert_online_payment_not_implemented,
    build_checkout_response,
    order_confirmation_include_whatsapp_cta,
    order_confirmation_intro,
)
from app.services.collection_selection_validator import CollectionSelectionValidator
from app.services.customer_delivery_date_service import (
    CATERING_MIN_COOKIE_QUANTITY,
    CustomerDeliveryDateService,
)
from app.services.delivery_fee_service import is_pickup_delivery_area, resolve_delivery_fee
from app.services.order_profitability_service import OrderProfitabilityService
from app.services.whatsapp_order_message_service import WhatsAppOrderMessageService
from app.services.discount_application_service import DiscountApplicationService
from app.services.discount_rule_evaluator import DiscountRuleEvaluator
from app.utils.discount_format import format_discount_label
from app.utils.email import normalize_email
from app.utils.premium_packaging_copy import premium_packaging_notice_from_collection_lines


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
    """Public checkout; online gateway redirect is added in the WebXPay integration phase."""

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

    def quote_collection(
        self,
        payload: ClientCollectionQuoteRequest,
    ) -> ClientCollectionQuoteResponse:
        """Server-authoritative collection pack price (cookies + embedded package fee)."""
        collection = self.collections.get_by_id(payload.collection_id)
        if not collection or not collection.is_active or not collection.is_public:
            raise NotFoundError("Collection is not available for ordering.")

        per_pack = self.selection_validator.validate_per_pack(
            collection,
            selections=payload.selections,
        )
        unit_price = calculate_package_selling_price(collection, per_pack)
        return ClientCollectionQuoteResponse(unit_price=unit_price)

    def preview(
        self,
        payload: ClientOrderPreviewRequest,
        *,
        customer_id: uuid.UUID | None = None,
    ) -> ClientOrderPreviewResponse:
        validated = self._validate_request(payload)
        settings = self.settings.get_settings()
        delivery_area = self._get_delivery_area(payload.delivery_area_id)
        delivery_fee = resolve_delivery_fee(settings, delivery_area)

        # Resolve discount for authenticated customers on preview (server-side only).
        discount_grant = None
        if customer_id is not None:
            discount_app = DiscountApplicationService(self.db)
            discount_grant = discount_app.resolve_grant_for_customer(customer_id)

        snapshot_result = self._build_snapshots(
            payload,
            validated,
            delivery_fee,
            is_pickup=is_pickup_delivery_area(delivery_area),
            discount_grant=discount_grant,
        )

        explanation = (
            get_delivery_schedule_copy(self.db).explanation
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
            if self.users.get_by_email(normalize_email(payload.customer.email)):
                raise ConflictError("An account with this email already exists.")

        validated = self._validate_request(payload)
        settings = self.settings.get_settings()
        validate_client_payment_method(settings, payload.payment_method, payload.order_type)
        assert_online_payment_not_implemented(payload.payment_method)
        delivery_area = self._get_delivery_area(payload.delivery_area_id)
        delivery_fee = resolve_delivery_fee(settings, delivery_area)

        # Resolve and lock the discount grant server-side (never trust client data)
        customer = self._resolve_customer(payload)
        discount_app = DiscountApplicationService(self.db)
        discount_grant = discount_app.resolve_grant_for_customer(customer.id)

        snapshot_result = self._build_snapshots(
            payload,
            validated,
            delivery_fee,
            is_pickup=is_pickup_delivery_area(delivery_area),
            discount_grant=discount_grant,
        )

        CustomerAttributionService.apply_first_touch(customer, payload.attribution)
        shipping = payload.customer.shipping_address
        billing = (
            shipping
            if payload.customer.billing_same_as_shipping
            else payload.customer.billing_address
        )
        assert billing is not None

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
            delivery_address_line_1=shipping.address_line_1,
            delivery_address_line_2=shipping.address_line_2,
            delivery_city=shipping.city,
            delivery_postal_code=shipping.postal_code,
            delivery_landmark=shipping.landmark,
            delivery_latitude=payload.customer.delivery_latitude,
            delivery_longitude=payload.customer.delivery_longitude,
            billing_same_as_shipping=payload.customer.billing_same_as_shipping,
            billing_address_line_1=billing.address_line_1,
            billing_address_line_2=billing.address_line_2,
            billing_city=billing.city,
            billing_postal_code=billing.postal_code,
            billing_landmark=billing.landmark,
        )
        self.profitability.apply_snapshots_to_order(order, snapshot_result)

        # Link the grant on the order snapshot
        if discount_grant is not None:
            order.customer_discount_grant_id_snapshot = discount_grant.id
            order.discount_rule_id_snapshot = discount_grant.discount_rule_id

        order.collection_lines = snapshot_result.collection_lines
        order.product_lines = snapshot_result.product_lines
        order.status_events = [OrderStatusEvent(status=OrderStatus.PENDING)]
        if validated.collection_lines:
            self._attach_selection_snapshots(order, validated.collection_lines)

        self.orders.create(order)
        self.db.flush()

        # Mark grant used atomically within the same transaction
        if discount_grant is not None:
            discount_app.mark_grant_used(discount_grant, order.id)

        account_created = False
        verification_sent = False
        if payload.create_account and payload.account_password:
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

        # Evaluate rules after commit — may issue a grant for the NEXT order
        try:
            DiscountRuleEvaluator(self.db).evaluate_after_order_placed(
                customer.id, loaded.id
            )
            self.db.commit()
        except Exception:  # noqa: BLE001
            pass  # Rule evaluation failure must never block checkout

        whatsapp_url = (
            WhatsAppOrderMessageService.build_whatsapp_url(loaded)
            if order_confirmation_include_whatsapp_cta(loaded.payment_method)
            else None
        )
        customer_email = normalize_email(payload.customer.email)
        order_type_label = (
            "Catering"
            if loaded.order_type == OrderType.CATERING
            else "Weekly Delivery"
        )
        premium_packaging_notice = premium_packaging_notice_from_collection_lines(
            loaded.collection_lines,
        )
        bank_details = (
            settings.bank_transfer_details
            if loaded.payment_method == PaymentMethod.BANK_TRANSFER
            else None
        )
        send_email_safely(
            lambda: get_email_service().send_order_confirmation_email(
                to_email=customer_email,
                first_name=payload.customer.first_name,
                order_number=loaded.order_number,
                order_type_label=order_type_label,
                scheduled_delivery_date=loaded.scheduled_delivery_date,
                total_amount=loaded.total_revenue_snapshot,
                whatsapp_url=whatsapp_url,
                premium_packaging_notice=premium_packaging_notice,
                products_subtotal=loaded.products_subtotal_snapshot,
                collections_subtotal=loaded.collections_subtotal_snapshot,
                delivery_fee=loaded.delivery_fee_snapshot,
                discount_amount=loaded.discount_amount_snapshot,
                discount_label=_build_discount_label(loaded),
                tax_lines=_build_tax_lines_for_email(loaded),
                confirmation_intro=order_confirmation_intro(
                    order_type=loaded.order_type,
                    payment_method=loaded.payment_method,
                ),
                bank_name=bank_details.bank_name if bank_details else None,
                bank_account_name=bank_details.account_name if bank_details else None,
                bank_account_number=bank_details.account_number if bank_details else None,
                bank_branch=bank_details.branch if bank_details else None,
                bank_transfer_instructions=bank_details.instructions if bank_details else None,
            ),
            context=f"order_confirmation:{loaded.order_number}",
        )
        notify_team_new_order(loaded)
        return build_checkout_response(
            loaded,
            business_settings=settings,
            account_created=account_created,
            verification_sent=verification_sent,
        )

    def _validate_request(self, payload: ClientOrderPreviewRequest) -> ValidatedOrderRequest:
        schedule_config = get_delivery_schedule_config(self.db)
        scheduled_date = CustomerDeliveryDateService.resolve_delivery_date(
            order_type=payload.order_type,
            requested_date=payload.requested_delivery_date,
            config=schedule_config,
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
        *,
        is_pickup: bool,
        discount_grant=None,
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
            is_pickup=is_pickup,
            discount_grant=discount_grant,
        )

    def _resolve_customer(self, payload: ClientCheckoutRequest) -> Customer:
        billing = (
            payload.customer.shipping_address
            if payload.customer.billing_same_as_shipping
            else payload.customer.billing_address
        )
        assert billing is not None

        email = normalize_email(payload.customer.email)
        identity = CustomerIdentityService(self.db)
        existing_user = self.users.get_by_email(email)
        if existing_user and existing_user.role == UserRole.CUSTOMER:
            customer = identity.ensure_customer_for_user(existing_user, commit=False)
            self._sync_checkout_customer_profile(customer, payload, billing)
            return customer

        existing_customer = identity.resolve_customer_for_checkout_email(email)
        if existing_customer is not None:
            self._sync_checkout_customer_profile(existing_customer, payload, billing)
            return existing_customer

        customer = Customer(
            first_name=payload.customer.first_name,
            last_name=payload.customer.last_name,
            email=email,
            phone=payload.customer.phone,
            address_line_1=billing.address_line_1,
            address_line_2=billing.address_line_2,
            city=billing.city,
            postal_code=billing.postal_code,
            landmark=billing.landmark,
            source=CustomerSource.GUEST,
            is_active=True,
        )
        self.customers.create(customer)
        self.db.flush()
        return customer

    @staticmethod
    def _sync_checkout_customer_profile(
        customer: Customer,
        payload: ClientCheckoutRequest,
        billing,
    ) -> None:
        customer.first_name = payload.customer.first_name
        customer.last_name = payload.customer.last_name
        customer.phone = payload.customer.phone
        customer.address_line_1 = billing.address_line_1
        customer.address_line_2 = billing.address_line_2
        customer.city = billing.city
        customer.postal_code = billing.postal_code
        customer.landmark = billing.landmark

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


def _build_discount_label(order: "Order") -> str | None:
    if not order.discount_amount_snapshot or order.discount_amount_snapshot <= 0:
        return None
    return format_discount_label(
        order.discount_type_snapshot,
        order.discount_value_snapshot,
    )


def _build_tax_lines_for_email(order: "Order") -> list[tuple[str, "Decimal"]] | None:
    from decimal import Decimal as _D
    tax_lines_raw = order.tax_lines_snapshot or []
    if not tax_lines_raw:
        return None
    result = []
    for t in tax_lines_raw:
        label = t.get("name", "Tax")
        if t.get("charge_type") == "percentage":
            label = f"{label} ({t.get('configured_amount', '')}%)"
        result.append((label, _D(str(t.get("applied_amount", "0")))))
    return result or None
