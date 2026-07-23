"""Structured order summary data for customer confirmation emails."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.models.order import Order
from app.services.client_payment_options import payment_method_label
from app.utils.collection_display_name import format_collection_display_name
from app.utils.premium_packaging_copy import (
    premium_packaging_notice_from_collection_lines,
    premium_packaging_notice_from_order_financials,
)


@dataclass(frozen=True, slots=True)
class OrderEmailCookieLine:
    name: str
    quantity_label: str


@dataclass(frozen=True, slots=True)
class OrderEmailCollectionBlock:
    title: str
    cookies: tuple[OrderEmailCookieLine, ...]


@dataclass(frozen=True, slots=True)
class OrderEmailProductLine:
    name: str
    quantity_label: str


@dataclass(frozen=True, slots=True)
class OrderEmailSummary:
    """Itemized receipt content for the order confirmation email."""

    order_type_label: str
    collection_blocks: tuple[OrderEmailCollectionBlock, ...]
    product_lines: tuple[OrderEmailProductLine, ...]
    packages_subtotal: Decimal | None
    cookies_subtotal: Decimal | None
    delivery_fee: Decimal | None
    discount_amount: Decimal | None
    discount_label: str | None
    tax_lines: tuple[tuple[str, Decimal], ...]
    total: Decimal
    premium_packaging_notice: str | None
    payment_method_label: str


def _format_quantity(quantity: Decimal) -> str:
    normalized = quantity.normalize()
    if normalized == normalized.to_integral():
        return str(int(normalized))
    return format(normalized, "f").rstrip("0").rstrip(".")


def build_order_email_summary(
    order: Order,
    *,
    order_type_label: str,
    discount_label: str | None = None,
    tax_lines: list[tuple[str, Decimal]] | None = None,
) -> OrderEmailSummary:
    collection_blocks: list[OrderEmailCollectionBlock] = []
    for line in order.collection_lines or []:
        pack_qty = _format_quantity(line.quantity)
        title = format_collection_display_name(line.collection_name_snapshot)
        if line.quantity != Decimal("1"):
            title = f"{title} × {pack_qty}"
        cookies = tuple(
            OrderEmailCookieLine(
                name=selection.product_name_snapshot,
                quantity_label=_format_quantity(selection.quantity),
            )
            for selection in (line.selections or [])
        )
        collection_blocks.append(
            OrderEmailCollectionBlock(title=title, cookies=cookies),
        )

    product_lines = tuple(
        OrderEmailProductLine(
            name=line.product_name_snapshot,
            quantity_label=_format_quantity(line.quantity),
        )
        for line in (order.product_lines or [])
    )

    packages = order.collections_subtotal_snapshot
    cookies = order.products_subtotal_snapshot
    delivery = order.delivery_fee_snapshot
    discount = getattr(order, "discount_amount_snapshot", None)

    packaging_notice = premium_packaging_notice_from_collection_lines(
        order.collection_lines,
    ) or premium_packaging_notice_from_order_financials(
        package_fee_revenue=order.package_fee_revenue_snapshot or Decimal("0"),
        has_collection_lines=bool(order.collection_lines),
        has_product_lines=bool(order.product_lines),
    )

    return OrderEmailSummary(
        order_type_label=order_type_label,
        collection_blocks=tuple(collection_blocks),
        product_lines=product_lines,
        packages_subtotal=packages if packages and packages > 0 else None,
        cookies_subtotal=cookies if cookies and cookies > 0 else None,
        delivery_fee=delivery if delivery is not None else None,
        discount_amount=discount if discount and discount > 0 else None,
        discount_label=discount_label,
        tax_lines=tuple(tax_lines or ()),
        total=order.total_revenue_snapshot,
        premium_packaging_notice=packaging_notice,
        payment_method_label=payment_method_label(order.payment_method),
    )
