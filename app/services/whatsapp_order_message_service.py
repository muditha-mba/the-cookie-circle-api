"""Format WhatsApp messages for new website orders."""

from decimal import Decimal
from urllib.parse import quote

from app.core.config import settings
from app.core.enums import OrderType, PaymentMethod
from app.models.order import Order
from app.models.order_collection_line import OrderCollectionLine
from app.schemas.business_settings import BankTransferDetailsResponse
from app.services.client_payment_options import payment_method_label
from app.utils.collection_display_name import format_collection_display_name
from app.utils.discount_format import format_discount_label
from app.utils.premium_packaging_copy import premium_packaging_notice_from_collection_lines


class WhatsAppOrderMessageService:
    """Build customer-facing WhatsApp deep links after order persistence."""

    @staticmethod
    def _format_lkr(amount: Decimal | None) -> str:
        if amount is None:
            return "LKR —"
        normalized = amount.normalize()
        if normalized == normalized.to_integral():
            return f"LKR {int(normalized):,}"
        return f"LKR {amount:,.2f}"

    @staticmethod
    def build_maps_url(latitude: Decimal | None, longitude: Decimal | None) -> str | None:
        if latitude is None or longitude is None:
            return None
        return f"https://maps.google.com/?q={latitude},{longitude}"

    @classmethod
    def format_message(cls, order: Order) -> str:
        order_type_label = order.order_type.value.replace("_", " ").title()

        lines: list[str] = [
            "*The Cookie Circle — New Order*",
            "",
            f"*Order Ref:* {order.order_number}",
            f"*Order Type:* {order_type_label}",
        ]
        if order.event_name:
            lines.append(f"*Event:* {order.event_name}")

        if order.collection_lines:
            lines.append("")
            lines.append("*Collections*")
            for collection_line in order.collection_lines:
                lines.extend(cls._format_collection_line(collection_line))

        if order.product_lines:
            lines.append("")
            lines.append("*Cookies*")
            for product_line in order.product_lines:
                lines.append(
                    f"- {product_line.product_name_snapshot} ×{product_line.quantity.normalize()}",
                )

        lines.extend(["", "*Delivery & Customer*"])
        lines.append(f"*Delivery Date:* {order.scheduled_delivery_date.isoformat()}")
        lines.append(f"*Customer Name:* {order.delivery_contact_name or '—'}")
        lines.append(f"*Phone:* {order.delivery_phone_primary or '—'}")
        if order.delivery_phone_secondary:
            lines.append(f"*Additional Phone:* {order.delivery_phone_secondary}")

        address_parts = [
            order.delivery_address_line_1,
            order.delivery_address_line_2,
            order.delivery_city,
            order.delivery_postal_code,
        ]
        address = ", ".join(part for part in address_parts if part)
        if address:
            lines.append(f"*Address:* {address}")
        if order.delivery_landmark:
            lines.append(f"*Landmark:* {order.delivery_landmark}")

        maps_url = cls.build_maps_url(order.delivery_latitude, order.delivery_longitude)
        if maps_url:
            lines.append(f"*Map Pin:* {maps_url}")

        if order.customer_notes:
            lines.append("")
            lines.append("*Notes*")
            lines.append(order.customer_notes)

        lines.extend(["", "*Payment Summary*"])
        if order.products_subtotal_snapshot and order.products_subtotal_snapshot > 0:
            lines.append(f"*Cookies Subtotal:* {cls._format_lkr(order.products_subtotal_snapshot)}")
        if order.collections_subtotal_snapshot and order.collections_subtotal_snapshot > 0:
            lines.append(f"*Collections Subtotal:* {cls._format_lkr(order.collections_subtotal_snapshot)}")
        lines.append(f"*Delivery Fee:* {cls._format_lkr(order.delivery_fee_snapshot)}")
        discount = getattr(order, "discount_amount_snapshot", None)
        if discount and discount > 0:
            discount_label = format_discount_label(
                getattr(order, "discount_type_snapshot", None),
                getattr(order, "discount_value_snapshot", None),
            )
            lines.append(f"*{discount_label}:* − {cls._format_lkr(discount)}")
        for tax in (order.tax_lines_snapshot or []):
            name = tax.get("name", "Tax")
            charge_type = tax.get("charge_type")
            configured = tax.get("configured_amount", "")
            applied = tax.get("applied_amount")
            if applied is not None:
                from decimal import Decimal as _D
                label = f"{name} ({configured}%)" if charge_type == "percentage" else name
                lines.append(f"*{label}:* {cls._format_lkr(_D(str(applied)))}")
        lines.append(f"*Total:* {cls._format_lkr(order.total_revenue_snapshot)}")
        premium_notice = premium_packaging_notice_from_collection_lines(order.collection_lines)
        if premium_notice:
            lines.append(f"🎁 {premium_notice}")
        lines.append(f"*Payment Method:* {payment_method_label(order.payment_method)}")

        return "\n".join(lines)

    @classmethod
    def build_order_details_message(
        cls,
        order: Order,
        *,
        bank_details: BankTransferDetailsResponse | None = None,
    ) -> str:
        """Full customer-facing message for clipboard copy (includes payment follow-up)."""
        base = cls.format_message(order)
        follow_up = cls._build_follow_up_instructions(order, bank_details=bank_details)
        if not follow_up:
            return base
        return f"{base}\n\n{follow_up}"

    @classmethod
    def _build_follow_up_instructions(
        cls,
        order: Order,
        *,
        bank_details: BankTransferDetailsResponse | None,
    ) -> str | None:
        if order.payment_method == PaymentMethod.CASH_ON_DELIVERY:
            return "\n".join(
                [
                    "*Next Step — WhatsApp*",
                    "Please copy and send this message to us on WhatsApp so we can confirm your order.",
                    "Payment will be collected in cash on delivery.",
                ],
            )

        if order.payment_method != PaymentMethod.BANK_TRANSFER:
            return None

        if bank_details is None:
            return "\n".join(
                [
                    "*Next Step — WhatsApp*",
                    "Please copy and send this message to us on WhatsApp.",
                    "After your bank transfer, share a screenshot or photo of your receipt in the same chat.",
                ],
            )

        lines = ["*Payment — Bank Transfer*"]
        if order.order_type == OrderType.CATERING:
            lines.extend(
                [
                    "Our team will call you to confirm your event details and final total.",
                    "Please transfer only after we confirm.",
                    "",
                    "When ready, transfer to:",
                ],
            )
        else:
            lines.extend(
                [
                    f"Please transfer *{cls._format_lkr(order.total_revenue_snapshot)}* to:",
                ],
            )

        lines.extend(
            [
                f"*Bank:* {bank_details.bank_name}",
                f"*Account Name:* {bank_details.account_name}",
                f"*Account No:* {bank_details.account_number}",
            ],
        )
        if bank_details.branch:
            lines.append(f"*Branch:* {bank_details.branch}")
        lines.extend(
            [
                "",
                f"Use order ref *{order.order_number}* as the payment reference.",
                "After payment, please share a screenshot or photo of your transfer receipt in WhatsApp.",
            ],
        )
        if bank_details.instructions:
            lines.extend(["", bank_details.instructions])
        return "\n".join(lines)

    @staticmethod
    def _format_collection_line(line: OrderCollectionLine) -> list[str]:
        display_name = format_collection_display_name(line.collection_name_snapshot)
        header = f"- {display_name} (x{line.quantity.normalize()} pack"
        header += "s)" if line.quantity != Decimal("1") else ")"

        block = [header]
        if line.selections:
            block.append("  Cookies:")
            for selection in line.selections:
                block.append(
                    f"   • {selection.product_name_snapshot} ×{selection.quantity.normalize()}",
                )
        return block

    @classmethod
    def build_whatsapp_open_url(cls) -> str:
        phone = "".join(ch for ch in settings.whatsapp_business_phone if ch.isdigit())
        return f"https://wa.me/{phone}"

    @classmethod
    def build_whatsapp_url(cls, order: Order) -> str:
        phone = "".join(ch for ch in settings.whatsapp_business_phone if ch.isdigit())
        text = quote(
            cls.build_order_details_message(order),
            safe="",
        )
        return f"https://wa.me/{phone}?text={text}"
