"""Post-checkout redirect and payment instruction helpers."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from app.core.config import settings
from app.core.enums import OrderType, PaymentMethod
from app.models.order import Order
from app.schemas.business_settings import BankTransferDetailsResponse, BusinessSettingsResponse
from app.schemas.client_ordering import ClientBankTransferInstructions, ClientCheckoutResponse
from app.services.whatsapp_order_message_service import WhatsAppOrderMessageService

CheckoutRedirectTo = Literal["order_success", "online_payment"]

_ONLINE_PAYMENT_METHODS = frozenset(
    {
        PaymentMethod.ONLINE_CARD,
        PaymentMethod.ONLINE_BANK_DEBIT,
    },
)


def assert_online_payment_enabled(payment_method: PaymentMethod) -> None:
    """Raise ValidationError if online payment is selected but WebXPay is not enabled."""
    if payment_method in _ONLINE_PAYMENT_METHODS and not settings.webxpay_enabled:
        from app.core.exceptions import ValidationError

        raise ValidationError(
            "Online payment is not available yet. Please choose another payment method.",
        )


def build_bank_transfer_instructions(
    *,
    bank_details: BankTransferDetailsResponse,
    order_number: str,
    amount: Decimal,
) -> ClientBankTransferInstructions:
    return ClientBankTransferInstructions(
        bank_name=bank_details.bank_name,
        account_name=bank_details.account_name,
        account_number=bank_details.account_number,
        branch=bank_details.branch,
        instructions=bank_details.instructions,
        amount=f"{amount:.2f}",
        order_number=order_number,
    )


def _build_order_details_message(
    order: Order,
    *,
    business_settings: BusinessSettingsResponse,
) -> str:
    bank_details = (
        business_settings.bank_transfer_details
        if order.payment_method == PaymentMethod.BANK_TRANSFER
        else None
    )
    return WhatsAppOrderMessageService.build_order_details_message(
        order,
        bank_details=bank_details,
    )


def build_checkout_response(
    order: Order,
    *,
    business_settings: BusinessSettingsResponse,
    account_created: bool,
    verification_sent: bool,
    payment_session_id: uuid.UUID | None = None,
) -> ClientCheckoutResponse:
    client_base = settings.frontend_client_url.rstrip("/")
    api_base = settings.api_public_url.rstrip("/")
    account_order_url = f"{client_base}/account/orders/{order.id}"
    payment_method = order.payment_method

    if payment_method == PaymentMethod.BANK_TRANSFER:
        bank_details = business_settings.bank_transfer_details
        instructions = build_bank_transfer_instructions(
            bank_details=bank_details,
            order_number=order.order_number,
            amount=order.total_revenue_snapshot,
        )
        if order.order_type == OrderType.CATERING:
            message = (
                "Your catering request has been received. We will call you to confirm "
                "details and the final total. Pay by bank transfer only after we confirm."
            )
        else:
            message = (
                "Your order has been placed. Please transfer the amount using the bank "
                "details shown in your confirmation."
            )
        return ClientCheckoutResponse(
            order_id=order.id,
            order_number=order.order_number,
            order_type=order.order_type,
            scheduled_delivery_date=order.scheduled_delivery_date,
            total_revenue_snapshot=order.total_revenue_snapshot,
            order_details_message=_build_order_details_message(
                order,
                business_settings=business_settings,
            ),
            whatsapp_open_url=WhatsAppOrderMessageService.build_whatsapp_open_url(),
            account_order_url=account_order_url,
            bank_transfer_instructions=instructions,
            redirect_to="order_success",
            account_created=account_created,
            verification_email_sent=verification_sent,
            message=message,
        )

    if payment_method == PaymentMethod.CASH_ON_DELIVERY:
        return ClientCheckoutResponse(
            order_id=order.id,
            order_number=order.order_number,
            order_type=order.order_type,
            scheduled_delivery_date=order.scheduled_delivery_date,
            total_revenue_snapshot=order.total_revenue_snapshot,
            order_details_message=_build_order_details_message(
                order,
                business_settings=business_settings,
            ),
            whatsapp_open_url=WhatsAppOrderMessageService.build_whatsapp_open_url(),
            account_order_url=account_order_url,
            redirect_to="order_success",
            account_created=account_created,
            verification_email_sent=verification_sent,
            message="Order placed successfully. Copy your order details and send them on WhatsApp.",
        )

    # Online payment path (ONLINE_CARD or ONLINE_BANK_DEBIT)
    payment_initiate_url: str | None = None
    if payment_session_id is not None:
        payment_initiate_url = (
            f"{api_base}/api/v1/payments/webxpay/initiate/{payment_session_id}"
        )

    return ClientCheckoutResponse(
        order_id=order.id,
        order_number=order.order_number,
        order_type=order.order_type,
        scheduled_delivery_date=order.scheduled_delivery_date,
        total_revenue_snapshot=order.total_revenue_snapshot,
        account_order_url=account_order_url,
        redirect_to="online_payment",
        payment_initiate_url=payment_initiate_url,
        account_created=account_created,
        verification_email_sent=verification_sent,
        message="Redirecting you to secure payment…",
    )


def order_confirmation_intro(
    *,
    order_type: OrderType,
    payment_method: PaymentMethod,
) -> str:
    if order_type == OrderType.CATERING:
        return (
            "Thank you for your catering request. Our team will call you to confirm your "
            "event details and final total. Please pay by bank transfer only after we confirm."
        )
    if payment_method == PaymentMethod.BANK_TRANSFER:
        return (
            "Thank you for your order. Please transfer the total below using your order "
            "number as the payment reference."
        )
    return (
        "Thank you for your order. We have received your request and our team will prepare "
        "your handcrafted batch with care."
    )


def order_confirmation_include_order_details_message(payment_method: PaymentMethod) -> bool:
    return payment_method in {
        PaymentMethod.CASH_ON_DELIVERY,
        PaymentMethod.BANK_TRANSFER,
    }
