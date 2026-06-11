"""Premium packaging customer copy tests."""

from decimal import Decimal

from app.models.order_collection_line import OrderCollectionLine
from app.utils.premium_packaging_copy import (
    NOTICE_MIXED_PLURAL,
    NOTICE_MIXED_SINGULAR,
    NOTICE_ONLY_SPECIAL_EDITION,
    premium_packaging_included_for_collection,
    premium_packaging_notice_from_collection_lines,
)


def _line(fee: str | None) -> OrderCollectionLine:
    return OrderCollectionLine(package_fee_snapshot=Decimal(fee) if fee else None)


def test_premium_packaging_included_for_special_edition_only() -> None:
    assert premium_packaging_included_for_collection(
        package_code="SPECIAL_EDITION",
        package_fee=Decimal("350"),
    )
    assert not premium_packaging_included_for_collection(
        package_code="MIX_AND_MATCH",
        package_fee=Decimal("350"),
    )
    assert not premium_packaging_included_for_collection(
        package_code="SPECIAL_EDITION",
        package_fee=Decimal("0"),
    )


def test_notice_only_special_edition_packages() -> None:
    lines = [_line("350"), _line("350")]
    assert premium_packaging_notice_from_collection_lines(lines) == NOTICE_ONLY_SPECIAL_EDITION


def test_notice_mixed_cart_singular() -> None:
    lines = [_line("350"), _line(None)]
    assert premium_packaging_notice_from_collection_lines(lines) == NOTICE_MIXED_SINGULAR


def test_notice_mixed_cart_plural() -> None:
    lines = [_line("350"), _line("350"), _line(None)]
    assert premium_packaging_notice_from_collection_lines(lines) == NOTICE_MIXED_PLURAL


def test_notice_absent_without_premium_lines() -> None:
    lines = [_line(None), _line("0")]
    assert premium_packaging_notice_from_collection_lines(lines) is None
