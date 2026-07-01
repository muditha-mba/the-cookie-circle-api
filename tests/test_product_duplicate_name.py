"""Tests for duplicate product name generation."""

from __future__ import annotations

import pytest

from app.core.exceptions import ConflictError, ValidationError
from app.utils.product_duplicate_name import (
    MAX_PRODUCT_NAME_LENGTH,
    generate_duplicate_product_name,
)


def test_generate_duplicate_product_name_uses_copy_prefix() -> None:
    name = generate_duplicate_product_name(
        "Chocolate Chip",
        name_exists=lambda _candidate: False,
    )
    assert name == "Copy of Chocolate Chip"


def test_generate_duplicate_product_name_adds_number_when_taken() -> None:
    taken = {"Copy of Chocolate Chip", "Copy of Chocolate Chip (2)"}

    name = generate_duplicate_product_name(
        "Chocolate Chip",
        name_exists=lambda candidate: candidate in taken,
    )
    assert name == "Copy of Chocolate Chip (3)"


def test_generate_duplicate_product_name_strips_source_whitespace() -> None:
    name = generate_duplicate_product_name(
        "  Vanilla Cookie  ",
        name_exists=lambda _candidate: False,
    )
    assert name == "Copy of Vanilla Cookie"


def test_generate_duplicate_product_name_rejects_empty_source() -> None:
    with pytest.raises(ValidationError, match="without a name"):
        generate_duplicate_product_name("   ", name_exists=lambda _candidate: False)


def test_generate_duplicate_product_name_truncates_long_source_names() -> None:
    long_source = "x" * MAX_PRODUCT_NAME_LENGTH
    name = generate_duplicate_product_name(
        long_source,
        name_exists=lambda _candidate: False,
    )
    assert len(name) == MAX_PRODUCT_NAME_LENGTH
    assert name.startswith("Copy of ")


def test_generate_duplicate_product_name_truncates_with_numbered_suffix() -> None:
    source = "y" * MAX_PRODUCT_NAME_LENGTH

    def name_exists(candidate: str) -> bool:
        return not candidate.endswith("(2)")

    name = generate_duplicate_product_name(source, name_exists=name_exists)
    assert len(name) == MAX_PRODUCT_NAME_LENGTH
    assert name.endswith("(2)")


def test_generate_duplicate_product_name_raises_when_exhausted() -> None:
    with pytest.raises(ConflictError, match="unique name"):
        generate_duplicate_product_name(
            "Cookie",
            name_exists=lambda _candidate: True,
        )
