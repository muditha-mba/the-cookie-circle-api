"""Tests for packaging notice helpers."""

from decimal import Decimal
from types import SimpleNamespace

from app.utils.premium_packaging_copy import (
    NOTICE_MIXED_PLURAL,
    NOTICE_MIXED_SINGULAR,
    NOTICE_WITH_FEE,
    premium_packaging_included_for_collection,
    premium_packaging_notice_from_collection_lines,
)


def test_premium_packaging_included_when_fee_positive() -> None:
    assert premium_packaging_included_for_collection(
        package_code="SPECIAL_EDITION",
        package_fee=Decimal("350"),
    )
    assert not premium_packaging_included_for_collection(
        package_code="MIX_AND_MATCH",
        package_fee=Decimal("0"),
    )
    assert premium_packaging_included_for_collection(
        package_code="MIX_AND_MATCH",
        package_fee=Decimal("50"),
    )


def test_notice_all_lines_with_fee() -> None:
    lines = [
        SimpleNamespace(package_fee_snapshot=Decimal("350")),
        SimpleNamespace(package_fee_snapshot=Decimal("100")),
    ]
    assert premium_packaging_notice_from_collection_lines(lines) == NOTICE_WITH_FEE


def test_notice_mixed_singular() -> None:
    lines = [
        SimpleNamespace(package_fee_snapshot=Decimal("350")),
        SimpleNamespace(package_fee_snapshot=Decimal("0")),
    ]
    assert premium_packaging_notice_from_collection_lines(lines) == NOTICE_MIXED_SINGULAR


def test_notice_mixed_plural() -> None:
    lines = [
        SimpleNamespace(package_fee_snapshot=Decimal("350")),
        SimpleNamespace(package_fee_snapshot=Decimal("100")),
        SimpleNamespace(package_fee_snapshot=Decimal("0")),
    ]
    assert premium_packaging_notice_from_collection_lines(lines) == NOTICE_MIXED_PLURAL
