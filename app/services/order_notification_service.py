"""Internal team notifications for new orders."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.enums import OrderSource, OrderType
from app.models.order import Order
from app.services.email import get_email_service
from app.services.email.delivery import send_email_safely
from app.utils.order_package_fee import package_fee_revenue_from_order

logger = logging.getLogger(__name__)

_ORDER_SOURCE_LABELS: dict[OrderSource, str] = {
    OrderSource.WEBSITE: "Website",
    OrderSource.ADMIN: "Admin panel",
    OrderSource.WHATSAPP: "WhatsApp",
    OrderSource.INSTAGRAM: "Instagram",
    OrderSource.FACEBOOK: "Facebook",
    OrderSource.MANUAL: "Manual",
    OrderSource.WALK_IN: "Walk in",
    OrderSource.PHONE: "Phone",
}


def _order_type_label(order_type: OrderType) -> str:
    if order_type == OrderType.CATERING:
        return "Catering"
    return "Weekly Delivery"


def notify_team_new_order(order: Order) -> None:
    """Send an internal alert when a new order is created."""
    recipient = (settings.order_notification_email or "").strip()
    if not recipient:
        return

    customer = order.customer
    customer_name = (
        order.delivery_contact_name
        or f"{customer.first_name} {customer.last_name}".strip()
        or "Customer"
    )
    customer_email = customer.email
    customer_phone = order.delivery_phone_primary or customer.phone
    admin_base = settings.frontend_admin_url.rstrip("/")
    admin_order_url = f"{admin_base}/orders/{order.id}"

    package_fee_revenue = package_fee_revenue_from_order(order)
    send_email_safely(
        lambda: get_email_service().send_internal_order_notification_email(
            to_email=recipient,
            order_number=order.order_number,
            order_source_label=_ORDER_SOURCE_LABELS.get(order.source, order.source.value),
            order_type_label=_order_type_label(order.order_type),
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            scheduled_delivery_date=order.scheduled_delivery_date,
            total_amount=order.total_revenue_snapshot,
            admin_order_url=admin_order_url,
            products_subtotal=order.products_subtotal_snapshot,
            collections_subtotal=order.collections_subtotal_snapshot,
            package_fee_revenue=package_fee_revenue,
            delivery_fee=order.delivery_fee_snapshot,
        ),
        context=f"internal_order_notification:{order.order_number}",
    )
