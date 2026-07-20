"""Customer-facing packaging copy."""

from collections.abc import Sequence
from decimal import Decimal

from app.models.order_collection_line import OrderCollectionLine

NOTICE_WITH_FEE = "Packaging fee included"
NOTICE_MIXED_SINGULAR = "Packaging fee included for one collection"
NOTICE_MIXED_PLURAL = "Packaging fee included for selected collections"


def premium_packaging_included_for_collection(
    *,
    package_code: str,
    package_fee: Decimal,
) -> bool:
    """Whether a catalog collection includes packaging in its price."""
    del package_code
    return package_fee > 0


def _is_premium_packaging_line(line: OrderCollectionLine) -> bool:
    fee = line.package_fee_snapshot
    return fee is not None and fee > 0


def premium_packaging_notice_from_order_financials(
    *,
    package_fee_revenue: Decimal,
    has_collection_lines: bool,
    has_product_lines: bool,
) -> str | None:
    """Customer notice when packaging fee is embedded in the order total."""
    if package_fee_revenue <= 0:
        return None
    return NOTICE_WITH_FEE


def premium_packaging_notice_from_collection_lines(
    lines: Sequence[OrderCollectionLine],
) -> str | None:
    """Build customer-facing packaging copy from persisted order lines."""
    if not lines:
        return None

    premium_lines = [line for line in lines if _is_premium_packaging_line(line)]
    if not premium_lines:
        return None

    has_other_packages = any(
        not _is_premium_packaging_line(line) for line in lines
    )
    if not has_other_packages:
        return NOTICE_WITH_FEE
    if len(premium_lines) == 1:
        return NOTICE_MIXED_SINGULAR
    return NOTICE_MIXED_PLURAL
