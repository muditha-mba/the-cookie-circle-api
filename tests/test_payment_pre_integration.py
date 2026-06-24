"""Payments pre-integration validation tests."""

from decimal import Decimal
from unittest.mock import patch

import pytest

from app.core.enums import OrderType, PaymentMethod
from app.core.exceptions import ValidationError
from app.schemas.business_settings import BankTransferDetailsResponse, BusinessSettingsResponse
from app.core.enums import Weekday
from app.services.checkout_follow_up import assert_online_payment_enabled
from app.services.client_payment_options import (
    get_client_payment_method_options,
    validate_client_payment_method,
)


def _settings(**overrides: object) -> BusinessSettingsResponse:
    base = {
        "delivery_fee": Decimal("0"),
        "use_fixed_delivery_fee": False,
        "order_cutoff_day": Weekday.THURSDAY,
        "delivery_day": Weekday.SATURDAY,
        "business_phone": "",
        "business_email": "",
        "online_card_enabled": False,
        "online_bank_debit_enabled": False,
        "bank_transfer_enabled": True,
        "cod_enabled": True,
        "discounts_enabled": False,
        "bank_transfer_details": BankTransferDetailsResponse(
            bank_name="Test Bank",
            account_name="Cookie Circle",
            account_number="123456",
            branch="Colombo",
            instructions="Use order number as reference.",
        ),
    }
    base.update(overrides)
    return BusinessSettingsResponse(**base)


def test_catering_rejects_non_bank_transfer() -> None:
    settings = _settings()
    with pytest.raises(ValidationError, match="Catering orders can only"):
        validate_client_payment_method(
            settings,
            PaymentMethod.CASH_ON_DELIVERY,
            OrderType.CATERING,
        )


def test_catering_allows_bank_transfer_when_enabled() -> None:
    settings = _settings()
    validate_client_payment_method(
        settings,
        PaymentMethod.BANK_TRANSFER,
        OrderType.CATERING,
    )


def test_weekly_delivery_respects_enabled_toggles() -> None:
    settings = _settings(online_card_enabled=True)
    # Patch webxpay_enabled=True so the online method is surfaced
    with patch("app.services.client_payment_options.app_settings") as mock_settings:
        mock_settings.webxpay_enabled = True
        methods = get_client_payment_method_options(settings, OrderType.WEEKLY_DELIVERY)
    codes = {method.code for method in methods}
    assert PaymentMethod.ONLINE_CARD in codes
    assert PaymentMethod.BANK_TRANSFER in codes
    assert PaymentMethod.CASH_ON_DELIVERY in codes


def test_catering_checkout_options_only_bank_transfer() -> None:
    settings = _settings()
    methods = get_client_payment_method_options(settings, OrderType.CATERING)
    assert len(methods) == 1
    assert methods[0].code == PaymentMethod.BANK_TRANSFER


def test_online_payment_disabled_guard() -> None:
    # When WEBXPAY_ENABLED=false, assert_online_payment_enabled must raise
    with patch("app.services.checkout_follow_up.settings") as mock_settings:
        mock_settings.webxpay_enabled = False
        with pytest.raises(ValidationError, match="not available yet"):
            assert_online_payment_enabled(PaymentMethod.ONLINE_CARD)


def test_online_payment_enabled_guard_passes() -> None:
    # When WEBXPAY_ENABLED=true, assert_online_payment_enabled must not raise
    with patch("app.services.checkout_follow_up.settings") as mock_settings:
        mock_settings.webxpay_enabled = True
        assert_online_payment_enabled(PaymentMethod.ONLINE_CARD)  # should not raise


def test_online_payment_non_online_method_not_blocked() -> None:
    # COD and bank transfer are never blocked by the WebXPay guard
    assert_online_payment_enabled(PaymentMethod.CASH_ON_DELIVERY)
    assert_online_payment_enabled(PaymentMethod.BANK_TRANSFER)


def test_weekly_rejects_disabled_payment_method() -> None:
    settings = _settings(cod_enabled=False)
    with pytest.raises(ValidationError, match="not available"):
        validate_client_payment_method(
            settings,
            PaymentMethod.CASH_ON_DELIVERY,
            OrderType.WEEKLY_DELIVERY,
        )
