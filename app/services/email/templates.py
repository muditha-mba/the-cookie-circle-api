"""Branded HTML + plain-text transactional email templates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from html import escape

from app.core.config import settings
from app.services.delivery_schedule_copy_service import get_delivery_schedule_copy_standalone

# Kandyan Luxury palette (aligned with client globals.css)
COLOR_CREAM = "#FAF6F0"
COLOR_IVORY = "#F5EFE6"
COLOR_PARCHMENT = "#EDE3D4"
COLOR_CARAMEL = "#C4813A"
COLOR_COCOA = "#5C3317"
COLOR_CHOCOLATE = "#2D1610"
COLOR_GOLD = "#B5922E"
COLOR_TEXT_MUTED = "#8B6B52"

PAPER_WEAVE = (
    "repeating-linear-gradient(0deg, transparent 0, transparent 3px, "
    "rgba(45,22,16,0.04) 3px, rgba(45,22,16,0.04) 4px), "
    "repeating-linear-gradient(90deg, transparent 0, transparent 80px, "
    "rgba(196,129,58,0.05) 80px, rgba(196,129,58,0.05) 81px)"
)
MIX_MATCH_GRADIENT = (
    f"linear-gradient(180deg, {COLOR_CREAM} 0%, {COLOR_IVORY} 50%, {COLOR_CREAM} 100%)"
)


@dataclass(frozen=True, slots=True)
class EmailContent:
    """Rendered email payload."""

    subject: str
    html: str
    text: str


def _subject_prefix() -> str:
    if settings.is_development:
        return "[Dev] "
    if settings.is_staging:
        return "[Staging] "
    return ""


def _logo_url() -> str:
    base = settings.frontend_client_url.rstrip("/")
    return f"{base}/images/logos/main.png"


def _format_lkr(amount: Decimal) -> str:
    quantized = amount.quantize(Decimal("0.01"))
    return f"LKR {quantized:,.2f}"


def _format_date(value: date) -> str:
    return value.strftime("%A, %d %B %Y")


def _render_layout(
    *,
    preheader: str,
    eyebrow: str,
    headline: str,
    body_html: str,
    cta_label: str | None = None,
    cta_url: str | None = None,
    footer_note: str | None = None,
) -> str:
    """Responsive table-based email shell with paper texture styling."""
    schedule = get_delivery_schedule_copy_standalone()
    safe_preheader = escape(preheader)
    safe_eyebrow = escape(eyebrow)
    safe_headline = escape(headline)
    safe_footer = escape(footer_note or "")
    safe_brand_tagline = escape(
        f"Crafted Fresh, Every {schedule.delivery_day_label}",
    )

    cta_block = ""
    if cta_label and cta_url:
        safe_label = escape(cta_label)
        safe_url = escape(cta_url, quote=True)
        cta_block = f"""
          <tr>
            <td align="center" style="padding:8px 0 28px;">
              <a href="{safe_url}"
                 style="display:inline-block;min-width:220px;max-width:100%;padding:14px 28px;
                        background-color:{COLOR_CARAMEL};color:{COLOR_CREAM};text-decoration:none;
                        border-radius:999px;font-family:Inter,Arial,sans-serif;font-size:15px;
                        font-weight:600;letter-spacing:0.02em;text-align:center;
                        box-shadow:0 8px 24px -8px rgba(92,51,23,0.35);">
                {safe_label}
              </a>
            </td>
          </tr>"""

    footer_html = ""
    if footer_note:
        footer_html = f"""
          <tr>
            <td style="padding-top:18px;border-top:1px solid {COLOR_PARCHMENT};
                       font-family:Inter,Arial,sans-serif;font-size:12px;line-height:1.6;
                       color:{COLOR_TEXT_MUTED};text-align:center;">
              {safe_footer}
            </td>
          </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="color-scheme" content="light" />
  <meta name="supported-color-schemes" content="light" />
  <title>{safe_headline}</title>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;1,400&family=Playfair+Display:ital,wght@0,500;0,600;1,500&display=swap" rel="stylesheet" />
  <style>
    @media only screen and (max-width: 620px) {{
      .shell-pad {{ padding: 28px 14px !important; }}
      .card-pad {{ padding: 28px 22px !important; }}
      .headline {{ font-size: 28px !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background-color:{COLOR_CREAM};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
    {safe_preheader}
  </div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
         style="background:{MIX_MATCH_GRADIENT};background-color:{COLOR_CREAM};">
    <tr>
      <td class="shell-pad" align="center" style="padding:48px 20px;
          background-image:{PAPER_WEAVE};background-color:{COLOR_CREAM};">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
               style="max-width:600px;margin:0 auto;">
          <tr>
            <td align="center" style="padding-bottom:24px;">
              <img src="{escape(_logo_url(), quote=True)}" width="132" alt="The Cookie Circle"
                   style="display:block;width:132px;max-width:100%;height:auto;border:0;" />
            </td>
          </tr>
          <tr>
            <td style="border-radius:24px;border:1px solid {COLOR_PARCHMENT};
                       background-color:rgba(255,255,255,0.92);
                       box-shadow:0 12px 48px -12px rgba(45,22,16,0.12);overflow:hidden;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td style="height:2px;background:linear-gradient(90deg, transparent, {COLOR_GOLD}, transparent);"></td>
                </tr>
                <tr>
                  <td class="card-pad" style="padding:36px 34px 30px;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                      <tr>
                        <td align="center"
                            style="padding-bottom:10px;font-family:'Cormorant Garamond',Georgia,serif;
                                   font-size:13px;letter-spacing:0.22em;text-transform:uppercase;
                                   color:{COLOR_GOLD};">
                          {safe_eyebrow}
                        </td>
                      </tr>
                      <tr>
                        <td class="headline" align="center"
                            style="padding-bottom:18px;font-family:'Playfair Display',Georgia,serif;
                                   font-size:32px;line-height:1.2;color:{COLOR_CHOCOLATE};">
                          {safe_headline}
                        </td>
                      </tr>
                      <tr>
                        <td style="font-family:Inter,Arial,sans-serif;font-size:15px;line-height:1.75;
                                   color:{COLOR_COCOA};">
                          {body_html}
                        </td>
                      </tr>
                      {cta_block}
                      {footer_html}
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td align="center"
                style="padding:24px 12px 0;font-family:Inter,Arial,sans-serif;font-size:12px;
                       line-height:1.6;color:{COLOR_TEXT_MUTED};">
              The Cookie Circle · {safe_brand_tagline}<br />
              Handcrafted in Kandy, Sri Lanka
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_verification_email(
    *,
    to_email: str,
    verification_url: str,
    dev_verification_url: str | None = None,
) -> EmailContent:
    _ = to_email
    body_html = f"""
      <p style="margin:0 0 16px;">
        Welcome to The Cookie Circle. Please confirm your email address to unlock your
        account, order history, and future member features.
      </p>
      <p style="margin:0;color:{COLOR_TEXT_MUTED};font-size:14px;">
        This link expires in {settings.email_verification_token_expire_hours} hours.
        If you did not create an account, you can safely ignore this email.
      </p>"""
    dev_text = ""
    if dev_verification_url:
        body_html += f"""
      <p style="margin:18px 0 0;padding:14px 16px;border:1px dashed {COLOR_PARCHMENT};
                border-radius:12px;background-color:{COLOR_IVORY};font-size:13px;
                color:{COLOR_TEXT_MUTED};">
        Development shortcut:<br />
        <a href="{escape(dev_verification_url, quote=True)}" style="color:{COLOR_CARAMEL};">
          {escape(dev_verification_url)}
        </a>
      </p>"""
        dev_text = f"\n\nDevelopment shortcut: {dev_verification_url}"

    html = _render_layout(
        preheader="Confirm your email to join The Cookie Circle.",
        eyebrow="Account",
        headline="Verify your email",
        body_html=body_html,
        cta_label="Verify email address",
        cta_url=verification_url,
    )
    text = (
        f"{_subject_prefix()}Verify your Cookie Circle account\n\n"
        "Welcome to The Cookie Circle.\n\n"
        f"Verify your email: {verification_url}\n\n"
        f"This link expires in {settings.email_verification_token_expire_hours} hours."
        f"{dev_text}"
    )
    return EmailContent(
        subject=f"{_subject_prefix()}Verify your Cookie Circle account",
        html=html,
        text=text,
    )


def build_password_reset_email(*, to_email: str, reset_url: str) -> EmailContent:
    _ = to_email
    body_html = f"""
      <p style="margin:0 0 16px;">
        We received a request to reset your password. Use the button below to choose a new one.
      </p>
      <p style="margin:0;color:{COLOR_TEXT_MUTED};font-size:14px;">
        This link expires in {settings.password_reset_token_expire_hours} hour(s).
        If you did not request a reset, you can ignore this email.
      </p>"""
    html = _render_layout(
        preheader="Reset your Cookie Circle password.",
        eyebrow="Security",
        headline="Reset your password",
        body_html=body_html,
        cta_label="Reset password",
        cta_url=reset_url,
    )
    text = (
        f"{_subject_prefix()}Reset your Cookie Circle password\n\n"
        f"Reset your password: {reset_url}\n\n"
        f"This link expires in {settings.password_reset_token_expire_hours} hour(s)."
    )
    return EmailContent(
        subject=f"{_subject_prefix()}Reset your Cookie Circle password",
        html=html,
        text=text,
    )


def build_welcome_email(*, first_name: str | None) -> EmailContent:
    greeting_name = escape((first_name or "there").strip() or "there")
    site_url = escape(settings.frontend_client_url.rstrip("/"), quote=True)
    body_html = f"""
      <p style="margin:0 0 16px;">
        Hello {greeting_name}, your email is confirmed and your circle is ready.
      </p>
      <p style="margin:0 0 16px;">
        Explore our curated collections, build your own weekend circle, and pre-order
        handcrafted batches prepared with care in Kandy.
      </p>
      <p style="margin:0;color:{COLOR_TEXT_MUTED};font-size:14px;">
        {escape(get_delivery_schedule_copy_standalone().explanation)}
      </p>"""
    html = _render_layout(
        preheader="Welcome to The Cookie Circle — your account is ready.",
        eyebrow="Welcome",
        headline="You are part of the circle",
        body_html=body_html,
        cta_label="Explore collections",
        cta_url=site_url,
    )
    text = (
        f"{_subject_prefix()}Welcome to The Cookie Circle\n\n"
        f"Hello {(first_name or 'there').strip() or 'there'},\n\n"
        "Your email is confirmed and your account is ready.\n\n"
        f"Visit us: {settings.frontend_client_url.rstrip('/')}\n"
    )
    return EmailContent(
        subject=f"{_subject_prefix()}Welcome to The Cookie Circle",
        html=html,
        text=text,
    )


def build_order_confirmation_email(
    *,
    first_name: str,
    order_number: str,
    order_type_label: str,
    scheduled_delivery_date: date,
    total_amount: Decimal,
    whatsapp_url: str | None = None,
    premium_packaging_notice: str | None = None,
    products_subtotal: Decimal | None = None,
    collections_subtotal: Decimal | None = None,
    delivery_fee: Decimal | None = None,
    discount_amount: Decimal | None = None,
    discount_label: str | None = None,
    tax_lines: list[tuple[str, Decimal]] | None = None,
) -> EmailContent:
    safe_name = escape(first_name.strip() or "there")

    # Build breakdown rows when detail is available
    breakdown_rows: list[tuple[str, str]] = []
    if products_subtotal is not None and products_subtotal > 0:
        breakdown_rows.append(("Cookies", escape(_format_lkr(products_subtotal))))
    if collections_subtotal is not None and collections_subtotal > 0:
        breakdown_rows.append(("Packages", escape(_format_lkr(collections_subtotal))))
    if delivery_fee is not None and delivery_fee > 0:
        breakdown_rows.append(("Delivery", escape(_format_lkr(delivery_fee))))
    if discount_amount is not None and discount_amount > 0:
        label = escape(discount_label or "Discount")
        breakdown_rows.append((label, f"<span style='color:#2d6a2d'>− {escape(_format_lkr(discount_amount))}</span>"))
    if tax_lines:
        for tax_label, tax_applied in tax_lines:
            breakdown_rows.append((escape(tax_label), escape(_format_lkr(tax_applied))))

    details_rows = [
        ("Order number", escape(order_number)),
        ("Order type", escape(order_type_label)),
        ("Scheduled delivery", escape(_format_date(scheduled_delivery_date))),
    ]
    details_rows.extend(breakdown_rows)
    details_rows.append(("Customer total", escape(_format_lkr(total_amount))))

    details_html = "".join(
        f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid {COLOR_PARCHMENT};
                     font-size:13px;color:{COLOR_TEXT_MUTED};width:42%;">{label}</td>
          <td style="padding:10px 0;border-bottom:1px solid {COLOR_PARCHMENT};
                     font-size:14px;color:{COLOR_CHOCOLATE};font-weight:600;">{value}</td>
        </tr>"""
        for label, value in details_rows
    )

    premium_packaging_html = ""
    if premium_packaging_notice:
        premium_packaging_html = f"""
      <p style="margin:0 0 18px;padding:12px 14px;border-radius:10px;
                background:{COLOR_PARCHMENT};font-size:13px;line-height:1.5;
                color:{COLOR_CHOCOLATE};">
        🎁 {escape(premium_packaging_notice)}
      </p>"""

    body_html = f"""
      <p style="margin:0 0 18px;">
        Thank you, {safe_name}. We have received your order and our team will prepare your
        handcrafted batch with care.
      </p>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
             style="margin:0 0 18px;border-collapse:collapse;">
        {details_html}
      </table>{premium_packaging_html}
      <p style="margin:0;color:{COLOR_TEXT_MUTED};font-size:14px;">
        {escape(get_delivery_schedule_copy_standalone().explanation)}
      </p>
      <p style="margin:12px 0 0;color:{COLOR_TEXT_MUTED};font-size:14px;">
        If you have not already completed your WhatsApp confirmation, please do so to help
        our team finalize your order smoothly.
      </p>"""

    cta_label = "Complete on WhatsApp" if whatsapp_url else "View our collections"
    cta_url = whatsapp_url or settings.frontend_client_url.rstrip("/")

    html = _render_layout(
        preheader=f"Your Cookie Circle order {order_number} is received.",
        eyebrow="Order received",
        headline="Thank you for your order",
        body_html=body_html,
        cta_label=cta_label,
        cta_url=cta_url,
        footer_note="Questions? Reply to this email or message us on WhatsApp.",
    )

    schedule = get_delivery_schedule_copy_standalone()
    whatsapp_line = f"\nWhatsApp confirmation: {whatsapp_url}\n" if whatsapp_url else ""
    premium_packaging_line = (
        f"\n{premium_packaging_notice}\n" if premium_packaging_notice else ""
    )
    text_lines = [
        f"{_subject_prefix()}Your Cookie Circle order {order_number}\n",
        f"Thank you, {first_name.strip() or 'there'}.\n",
        f"Order number: {order_number}",
        f"Order type: {order_type_label}",
        f"Scheduled delivery: {_format_date(scheduled_delivery_date)}",
    ]
    if products_subtotal is not None and products_subtotal > 0:
        text_lines.append(f"Cookies: {_format_lkr(products_subtotal)}")
    if collections_subtotal is not None and collections_subtotal > 0:
        text_lines.append(f"Packages: {_format_lkr(collections_subtotal)}")
    if delivery_fee is not None and delivery_fee > 0:
        text_lines.append(f"Delivery: {_format_lkr(delivery_fee)}")
    if discount_amount is not None and discount_amount > 0:
        text_lines.append(f"{discount_label or 'Discount'}: − {_format_lkr(discount_amount)}")
    if tax_lines:
        for tax_label, tax_applied in tax_lines:
            text_lines.append(f"{tax_label}: {_format_lkr(tax_applied)}")
    text_lines.extend([
        f"Customer total: {_format_lkr(total_amount)}\n",
        f"{premium_packaging_line}",
        f"{schedule.explanation}",
        f"{whatsapp_line}",
    ])
    text = "\n".join(text_lines)
    return EmailContent(
        subject=f"{_subject_prefix()}Your Cookie Circle order {order_number}",
        html=html,
        text=text,
    )


def build_internal_order_notification_email(
    *,
    order_number: str,
    order_source_label: str,
    order_type_label: str,
    customer_name: str,
    customer_email: str | None,
    customer_phone: str | None,
    scheduled_delivery_date: date,
    total_amount: Decimal,
    admin_order_url: str,
    products_subtotal: Decimal | None = None,
    collections_subtotal: Decimal | None = None,
    package_fee_revenue: Decimal | None = None,
    delivery_fee: Decimal | None = None,
    discount_amount: Decimal | None = None,
    discount_label: str | None = None,
    tax_lines: list[tuple[str, Decimal]] | None = None,
) -> EmailContent:
    details_rows = [
        ("Order number", escape(order_number)),
        ("Channel", escape(order_source_label)),
        ("Order type", escape(order_type_label)),
        ("Customer", escape(customer_name)),
        ("Email", escape(customer_email or "—")),
        ("Phone", escape(customer_phone or "—")),
        ("Scheduled delivery", escape(_format_date(scheduled_delivery_date))),
    ]
    if products_subtotal is not None and products_subtotal > 0:
        details_rows.append(
            ("Cookies subtotal", escape(_format_lkr(products_subtotal))),
        )
    if collections_subtotal is not None and collections_subtotal > 0:
        details_rows.append(
            ("Collections subtotal", escape(_format_lkr(collections_subtotal))),
        )
    if package_fee_revenue is not None and package_fee_revenue > 0:
        details_rows.append(
            ("Package fee revenue", escape(_format_lkr(package_fee_revenue))),
        )
    if delivery_fee is not None and delivery_fee > 0:
        details_rows.append(("Delivery fee", escape(_format_lkr(delivery_fee))))
    if discount_amount is not None and discount_amount > 0:
        label = escape(discount_label or "Discount")
        details_rows.append((label, f"<span style='color:#2d6a2d'>− {escape(_format_lkr(discount_amount))}</span>"))
    if tax_lines:
        for tax_label, tax_applied in tax_lines:
            details_rows.append((escape(tax_label), escape(_format_lkr(tax_applied))))
    details_rows.append(("Customer total", escape(_format_lkr(total_amount))))
    details_html = "".join(
        f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid {COLOR_PARCHMENT};
                     font-size:13px;color:{COLOR_TEXT_MUTED};width:42%;">{label}</td>
          <td style="padding:10px 0;border-bottom:1px solid {COLOR_PARCHMENT};
                     font-size:14px;color:{COLOR_CHOCOLATE};font-weight:600;">{value}</td>
        </tr>"""
        for label, value in details_rows
    )

    body_html = f"""
      <p style="margin:0 0 18px;">
        A new order has been placed and is ready for your team to review in the admin panel.
      </p>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
             style="margin:0 0 18px;border-collapse:collapse;">
        {details_html}
      </table>
      <p style="margin:0;color:{COLOR_TEXT_MUTED};font-size:14px;">
        This notification is sent only to your internal team inbox.
      </p>"""

    html = _render_layout(
        preheader=f"New order {order_number} received.",
        eyebrow="Team alert",
        headline="New order received",
        body_html=body_html,
        cta_label="Open in admin",
        cta_url=admin_order_url,
    )
    text_lines = [
        f"{_subject_prefix()}New Cookie Circle order {order_number}\n",
        f"Channel: {order_source_label}",
        f"Order type: {order_type_label}",
        f"Customer: {customer_name}",
        f"Email: {customer_email or '—'}",
        f"Phone: {customer_phone or '—'}",
        f"Scheduled delivery: {_format_date(scheduled_delivery_date)}",
    ]
    if products_subtotal is not None and products_subtotal > 0:
        text_lines.append(f"Cookies subtotal: {_format_lkr(products_subtotal)}")
    if collections_subtotal is not None and collections_subtotal > 0:
        text_lines.append(f"Collections subtotal: {_format_lkr(collections_subtotal)}")
    if package_fee_revenue is not None and package_fee_revenue > 0:
        text_lines.append(f"Package fee revenue: {_format_lkr(package_fee_revenue)}")
    if delivery_fee is not None and delivery_fee > 0:
        text_lines.append(f"Delivery fee: {_format_lkr(delivery_fee)}")
    if discount_amount is not None and discount_amount > 0:
        text_lines.append(f"{discount_label or 'Discount'}: − {_format_lkr(discount_amount)}")
    if tax_lines:
        for tax_label, tax_applied in tax_lines:
            text_lines.append(f"{tax_label}: {_format_lkr(tax_applied)}")
    text_lines.extend(
        [
            f"Customer total: {_format_lkr(total_amount)}\n",
            f"Admin: {admin_order_url}\n",
        ],
    )
    text = "\n".join(text_lines)
    return EmailContent(
        subject=f"{_subject_prefix()}New order {order_number}",
        html=html,
        text=text,
    )
