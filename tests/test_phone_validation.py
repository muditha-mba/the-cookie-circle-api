"""Tests for shared phone-number validation."""

import pytest
from pydantic import ValidationError

from app.schemas.client_account import (
    ClientAccountAddressCreate,
    ClientAccountProfileUpdate,
)
from app.schemas.client_ordering import ClientCheckoutCustomer
from app.utils.phone import validate_optional_phone, validate_phone_number


@pytest.mark.parametrize(
    "value",
    [
        "0771234567",
        "+94771234567",
        "94 77 123 4567",
        "(077) 123-4567",
    ],
)
def test_validate_phone_number_accepts_valid_formats(value: str) -> None:
    assert validate_phone_number(value) == value.strip()


@pytest.mark.parametrize(
    "value",
    [
        "9098712019fvfvfs",
        "abc",
        "07712",
        "++94771234567",
        "123",
        "4334343432423423423423234234234",
    ],
)
def test_validate_phone_number_rejects_invalid_formats(value: str) -> None:
    with pytest.raises(ValueError):
        validate_phone_number(value)


def test_validate_phone_number_rejects_more_than_15_digits() -> None:
    with pytest.raises(ValueError, match="15 digits"):
        validate_phone_number("1234567890123456")


def test_validate_optional_phone_blank_becomes_none() -> None:
    assert validate_optional_phone(None) is None
    assert validate_optional_phone("") is None
    assert validate_optional_phone("   ") is None


def test_checkout_customer_rejects_letters_in_phone() -> None:
    with pytest.raises(ValidationError):
        ClientCheckoutCustomer(
            first_name="Kate",
            last_name="Lilly",
            email="kate@example.com",
            phone="9098712019fvfvfs",
            shipping_address={
                "address_line_1": "12/5",
                "city": "Kandy",
            },
        )


def test_profile_update_rejects_letters_in_phone() -> None:
    with pytest.raises(ValidationError):
        ClientAccountProfileUpdate(
            first_name="Kate",
            last_name="Lilly",
            phone="notaphone",
        )


def test_address_create_accepts_sri_lankan_mobile() -> None:
    address = ClientAccountAddressCreate(
        label="Home",
        recipient_name="Kate Lilly",
        phone="+94771234567",
        address_line_1="12/5",
        city="Kandy",
    )
    assert address.phone == "+94771234567"
