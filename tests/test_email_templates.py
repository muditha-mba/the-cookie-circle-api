"""Transactional email template tests."""

from datetime import date
from decimal import Decimal

from app.services.email.templates import (
    build_internal_order_notification_email,
    build_order_confirmation_email,
    build_verification_email,
    build_welcome_email,
)


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


def test_order_confirmation_template_includes_order_details() -> None:
    content = build_order_confirmation_email(
        first_name="Sam",
        order_number="TCC-2026-00042",
        order_type_label="Weekly Delivery",
        scheduled_delivery_date=date(2026, 6, 6),
        total_amount=Decimal("4500.00"),
        whatsapp_url="https://wa.me/94713259795",
    )
    assert "TCC-2026-00042" in content.subject
    assert "Weekly Delivery" in content.html
    assert "LKR 4,500.00" in content.html
    assert "wa.me" in content.html


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
