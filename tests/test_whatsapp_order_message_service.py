"""Tests for WhatsApp / clipboard order detail messages."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from app.core.enums import OrderType, PaymentMethod
from app.schemas.business_settings import BankTransferDetailsResponse
from app.services.whatsapp_order_message_service import WhatsAppOrderMessageService


def _order(**overrides):
    base = {
        "order_number": "CC-1001",
        "order_type": OrderType.WEEKLY_DELIVERY,
        "event_name": None,
        "collection_lines": [],
        "product_lines": [],
        "scheduled_delivery_date": date(2026, 6, 27),
        "delivery_contact_name": "Ada Lovelace",
        "delivery_phone_primary": "+94771234567",
        "delivery_phone_secondary": None,
        "delivery_address_line_1": "12 Temple Road",
        "delivery_address_line_2": None,
        "delivery_city": "Kandy",
        "delivery_postal_code": "20000",
        "delivery_landmark": None,
        "delivery_latitude": None,
        "delivery_longitude": None,
        "customer_notes": None,
        "products_subtotal_snapshot": Decimal("0"),
        "collections_subtotal_snapshot": Decimal("4500"),
        "delivery_fee_snapshot": Decimal("350"),
        "discount_amount_snapshot": None,
        "discount_type_snapshot": None,
        "discount_value_snapshot": None,
        "tax_lines_snapshot": [],
        "total_revenue_snapshot": Decimal("4850"),
        "payment_method": PaymentMethod.CASH_ON_DELIVERY,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_cod_message_includes_whatsapp_follow_up() -> None:
    message = WhatsAppOrderMessageService.build_order_details_message(_order())

    assert "*The Cookie Circle — New Order*" in message
    assert "*Order Ref:* CC-1001" in message
    assert "*Next Step — WhatsApp*" in message
    assert "cash on delivery" in message


def test_bank_transfer_weekly_includes_bank_details_and_receipt_prompt() -> None:
    bank = BankTransferDetailsResponse(
        bank_name="Commercial Bank",
        account_name="The Cookie Circle",
        account_number="1234567890",
        branch="Kandy",
        instructions="Include your order number as the reference.",
    )
    message = WhatsAppOrderMessageService.build_order_details_message(
        _order(payment_method=PaymentMethod.BANK_TRANSFER),
        bank_details=bank,
    )

    assert "*Payment — Bank Transfer*" in message
    assert "Please transfer *LKR 4,850* to:" in message
    assert "*Account No:* 1234567890" in message
    assert "transfer receipt in WhatsApp" in message
    assert "Include your order number as the reference." in message


def test_bank_transfer_catering_waits_for_confirmation() -> None:
    bank = BankTransferDetailsResponse(
        bank_name="Commercial Bank",
        account_name="The Cookie Circle",
        account_number="1234567890",
        branch="Kandy",
        instructions="",
    )
    message = WhatsAppOrderMessageService.build_order_details_message(
        _order(
            order_type=OrderType.CATERING,
            event_name="Birthday",
            payment_method=PaymentMethod.BANK_TRANSFER,
        ),
        bank_details=bank,
    )

    assert "Please transfer only after we confirm." in message
    assert "When ready, transfer to:" in message
    assert "Please transfer *LKR" not in message


@patch("app.services.whatsapp_order_message_service.settings")
def test_build_whatsapp_open_url(mock_settings) -> None:
    mock_settings.whatsapp_business_phone = "+94 77 123 4567"

    assert WhatsAppOrderMessageService.build_whatsapp_open_url() == "https://wa.me/94771234567"
