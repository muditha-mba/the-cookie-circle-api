"""Customer-facing premium packaging copy (no fee amounts)."""

from collections.abc import Sequence
from decimal import Decimal

from app.models.order_collection_line import OrderCollectionLine

SPECIAL_EDITION_PACKAGE_CODE = "SPECIAL_EDITION"

NOTICE_ONLY_SPECIAL_EDITION = "Premium packaging fee included"
NOTICE_MIXED_SINGULAR = "Premium packaging fee included for special edition collection"
NOTICE_MIXED_PLURAL = "Premium packaging fee included for special edition collections"


def premium_packaging_included_for_collection(
    *,
    package_code: str,
    package_fee: Decimal,
) -> bool:
    """Whether a catalog collection includes premium packaging in its price."""
    return package_code == SPECIAL_EDITION_PACKAGE_CODE and package_fee > 0


def _is_premium_packaging_line(line: OrderCollectionLine) -> bool:
    fee = line.package_fee_snapshot
    return fee is not None and fee > 0


def premium_packaging_notice_from_collection_lines(
    lines: Sequence[OrderCollectionLine],
) -> str | None:
    """Build customer-facing premium packaging copy from persisted order lines."""
    if not lines:
        return None

    premium_lines = [line for line in lines if _is_premium_packaging_line(line)]
    if not premium_lines:
        return None

    has_other_packages = any(
        not _is_premium_packaging_line(line) for line in lines
    )
    if not has_other_packages:
        return NOTICE_ONLY_SPECIAL_EDITION
    if len(premium_lines) == 1:
        return NOTICE_MIXED_SINGULAR
    return NOTICE_MIXED_PLURAL
