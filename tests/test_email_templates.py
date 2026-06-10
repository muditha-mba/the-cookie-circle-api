"""Transactional email template tests."""

from datetime import date
from decimal import Decimal

from app.services.email.templates import (
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
