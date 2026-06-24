"""Client-facing payment method options and validation."""

from __future__ import annotations

from app.core.config import settings as app_settings
from app.core.enums import OrderType, PaymentMethod
from app.core.exceptions import ValidationError
from app.schemas.business_settings import BusinessSettingsResponse
from app.schemas.client_ordering import ClientPaymentMethodOption

_PAYMENT_METHOD_LABELS: dict[PaymentMethod, str] = {
    PaymentMethod.CASH_ON_DELIVERY: "Cash on delivery",
    PaymentMethod.BANK_TRANSFER: "Bank transfer (pay to our account)",
    PaymentMethod.ONLINE_CARD: "Pay by card (Visa/Mastercard)",
    PaymentMethod.ONLINE_BANK_DEBIT: "Pay from my bank account (OTP)",
    PaymentMethod.MANUAL: "Manual",
}

_ONLINE_PAYMENT_METHODS: frozenset[PaymentMethod] = frozenset(
    {PaymentMethod.ONLINE_CARD, PaymentMethod.ONLINE_BANK_DEBIT}
)

_CLIENT_PAYMENT_METHOD_ORDER: tuple[PaymentMethod, ...] = (
    PaymentMethod.ONLINE_CARD,
    PaymentMethod.ONLINE_BANK_DEBIT,
    PaymentMethod.BANK_TRANSFER,
    PaymentMethod.CASH_ON_DELIVERY,
)


def payment_method_label(method: PaymentMethod) -> str:
    return _PAYMENT_METHOD_LABELS.get(
        method,
        str(method.value).replace("_", " ").title(),
    )


def get_enabled_payment_methods(settings: BusinessSettingsResponse) -> set[PaymentMethod]:
    allowed: set[PaymentMethod] = set()
    if settings.cod_enabled:
        allowed.add(PaymentMethod.CASH_ON_DELIVERY)
    if settings.bank_transfer_enabled:
        allowed.add(PaymentMethod.BANK_TRANSFER)
    # Online methods are only surfaced when the WebXPay gateway is enabled globally.
    # This prevents customers from seeing unavailable options before go-live.
    if app_settings.webxpay_enabled:
        if settings.online_card_enabled:
            allowed.add(PaymentMethod.ONLINE_CARD)
        if settings.online_bank_debit_enabled:
            allowed.add(PaymentMethod.ONLINE_BANK_DEBIT)
    return allowed


def get_client_payment_method_options(
    settings: BusinessSettingsResponse,
    order_type: OrderType | None = None,
) -> list[ClientPaymentMethodOption]:
    allowed = get_enabled_payment_methods(settings)
    if order_type == OrderType.CATERING:
        allowed = {PaymentMethod.BANK_TRANSFER} if PaymentMethod.BANK_TRANSFER in allowed else set()

    return [
        ClientPaymentMethodOption(code=method, label=payment_method_label(method))
        for method in _CLIENT_PAYMENT_METHOD_ORDER
        if method in allowed
    ]


def validate_client_payment_method(
    settings: BusinessSettingsResponse,
    payment_method: PaymentMethod,
    order_type: OrderType,
) -> None:
    allowed = get_enabled_payment_methods(settings)
    if order_type == OrderType.CATERING:
        if payment_method != PaymentMethod.BANK_TRANSFER:
            raise ValidationError(
                "Catering orders can only be paid by manual bank transfer after we confirm your order.",
            )
        if PaymentMethod.BANK_TRANSFER not in allowed:
            raise ValidationError("Bank transfer is not currently available.")
        return

    if not allowed:
        raise ValidationError("No payment methods are currently available.")
    if payment_method not in allowed:
        raise ValidationError("Selected payment method is not available.")
