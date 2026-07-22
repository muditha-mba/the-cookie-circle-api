"""Transactional email template tests."""

from datetime import date
from decimal import Decimal

from app.core.enums import PaymentMethod
from app.services.email.order_summary import (
    OrderEmailCollectionBlock,
    OrderEmailCookieLine,
    OrderEmailProductLine,
    OrderEmailSummary,
)
from app.services.email.templates import (
    build_internal_order_notification_email,
    build_order_confirmation_email,
    build_verification_email,
    build_welcome_email,
)
from app.services.client_payment_options import payment_method_label


def test_verification_template_contains_brand_and_cta() -> None:
    content = build_verification_email(
        to_email="guest@example.com",
        verification_url="https://thecookiecircle.lk/verify-email?token=abc",
    )
    assert "Verify your Cookie Circle account" in content.subject
    assert "The Cookie Circle" in content.html
    assert "verify-email?token=abc" in content.html
    assert "FAF6F0" in content.html
    assert "repeating-linear-gradient" in content.html
    assert content.text


def test_welcome_template_is_responsive_table_layout() -> None:
    content = build_welcome_email(first_name="Muditha")
    assert "Muditha" in content.html
    assert 'role="presentation"' in content.html
    assert "@media only screen and (max-width: 620px)" in content.html


def test_order_confirmation_template_has_summary_without_whatsapp() -> None:
    summary = OrderEmailSummary(
        order_type_label="Catering",
        collection_blocks=(),
        product_lines=(
            OrderEmailProductLine(name="Smarties Cookie", quantity_label="5"),
            OrderEmailProductLine(name="Unicorn Cookie", quantity_label="7"),
        ),
        packages_subtotal=None,
        cookies_subtotal=Decimal("8166.00"),
        delivery_fee=Decimal("350.00"),
        discount_amount=None,
        discount_label=None,
        tax_lines=(),
        total=Decimal("8516.00"),
        premium_packaging_notice=None,
        payment_method_label=payment_method_label(PaymentMethod.BANK_TRANSFER),
    )
    content = build_order_confirmation_email(
        first_name="Sam",
        order_number="WEB-20260722-0002",
        order_type_label="Catering",
        scheduled_delivery_date=date(2026, 8, 1),
        total_amount=Decimal("8516.00"),
        order_summary=summary,
        products_subtotal=Decimal("8166.00"),
        delivery_fee=Decimal("350.00"),
    )
    assert "WEB-20260722-0002" in content.subject
    assert "Order summary" in content.html
    assert "Smarties Cookie" in content.html
    assert "×5" in content.html
    assert "Cookies subtotal" in content.html
    assert "LKR 8,516.00" in content.html
    assert "Payment method" in content.html
    assert "Bank transfer" in content.html
    assert "View our collections" in content.html
    assert "Open WhatsApp" not in content.html
    assert "wa.me" not in content.html
    assert "Copy the order details" not in content.html
    assert "message us on WhatsApp" not in content.html
    assert "Smarties Cookie ×5" in content.text


def test_order_confirmation_template_includes_collection_blocks() -> None:
    summary = OrderEmailSummary(
        order_type_label="Weekly Delivery",
        collection_blocks=(
            OrderEmailCollectionBlock(
                title="Chocolate Chip Cookie Collection",
                cookies=(
                    OrderEmailCookieLine(
                        name="Classic Chocolate Chip Cookie",
                        quantity_label="3",
                    ),
                ),
            ),
        ),
        product_lines=(),
        packages_subtotal=Decimal("4903.00"),
        cookies_subtotal=None,
        delivery_fee=Decimal("350.00"),
        discount_amount=None,
        discount_label=None,
        tax_lines=(),
        total=Decimal("5253.00"),
        premium_packaging_notice="Packaging fee included",
        payment_method_label=payment_method_label(PaymentMethod.BANK_TRANSFER),
    )
    content = build_order_confirmation_email(
        first_name="Sam",
        order_number="TCC-2026-00042",
        order_type_label="Weekly Delivery",
        scheduled_delivery_date=date(2026, 6, 6),
        total_amount=Decimal("5253.00"),
        order_summary=summary,
        premium_packaging_notice="Packaging fee included",
    )
    assert "Chocolate Chip Cookie Collection" in content.html
    assert "Classic Chocolate Chip Cookie" in content.html
    assert "Packages subtotal" in content.html
    assert "Packaging fee included" in content.html
    assert "Packaging fee included" in content.text


def test_order_confirmation_template_includes_premium_packaging_notice() -> None:
    notice = "Premium packaging fee included for special edition collection"
    content = build_order_confirmation_email(
        first_name="Sam",
        order_number="TCC-2026-00042",
        order_type_label="Weekly Delivery",
        scheduled_delivery_date=date(2026, 6, 6),
        total_amount=Decimal("4500.00"),
        premium_packaging_notice=notice,
    )
    assert notice in content.html
    assert notice in content.text


def test_internal_order_notification_template_targets_team_inbox() -> None:
    content = build_internal_order_notification_email(
        order_number="TCC-2026-00099",
        order_source_label="Website",
        order_type_label="Weekly Delivery",
        customer_name="Jane Doe",
        customer_email="jane@example.com",
        customer_phone="+94771234567",
        scheduled_delivery_date=date(2026, 6, 6),
        total_amount=Decimal("5200.00"),
        admin_order_url="http://localhost:3001/orders/abc-123",
        collections_subtotal=Decimal("4500.00"),
        package_fee_revenue=Decimal("350.00"),
        delivery_fee=Decimal("350.00"),
    )
    assert "New order TCC-2026-00099" in content.subject
    assert "Team alert" in content.html
    assert "Jane Doe" in content.html
    assert "Package fee revenue" in content.html
    assert "LKR 350.00" in content.html
    assert "/orders/abc-123" in content.html
