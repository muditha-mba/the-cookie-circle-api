"""Branded HTML + plain-text transactional email templates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from html import escape

from app.core.config import settings
from app.services.delivery_schedule_copy_service import get_delivery_schedule_copy_standalone
from app.services.email.order_summary import OrderEmailSummary

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
    order_summary: OrderEmailSummary | None = None,
    premium_packaging_notice: str | None = None,
    products_subtotal: Decimal | None = None,
    collections_subtotal: Decimal | None = None,
    delivery_fee: Decimal | None = None,
    discount_amount: Decimal | None = None,
    discount_label: str | None = None,
    tax_lines: list[tuple[str, Decimal]] | None = None,
    confirmation_intro: str | None = None,
    bank_name: str | None = None,
    bank_account_name: str | None = None,
    bank_account_number: str | None = None,
    bank_branch: str | None = None,
    bank_transfer_instructions: str | None = None,
) -> EmailContent:
    meta_rows = [
        ("Order number", escape(order_number)),
        ("Order type", escape(order_type_label)),
        ("Scheduled delivery", escape(_format_date(scheduled_delivery_date))),
    ]
    meta_html = "".join(
        f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid {COLOR_PARCHMENT};
                     font-size:13px;color:{COLOR_TEXT_MUTED};width:42%;">{label}</td>
          <td style="padding:10px 0;border-bottom:1px solid {COLOR_PARCHMENT};
                     font-size:14px;color:{COLOR_CHOCOLATE};font-weight:600;">{value}</td>
        </tr>"""
        for label, value in meta_rows
    )

    summary_html = _render_order_summary_html(
        order_summary=order_summary,
        order_type_label=order_type_label,
        total_amount=total_amount,
        products_subtotal=products_subtotal,
        collections_subtotal=collections_subtotal,
        delivery_fee=delivery_fee,
        discount_amount=discount_amount,
        discount_label=discount_label,
        tax_lines=tax_lines,
        premium_packaging_notice=premium_packaging_notice,
    )

    body_intro = confirmation_intro or (
        f"Thank you, {first_name.strip() or 'there'}. We have received your order and our team "
        "will prepare your handcrafted batch with care."
    )

    bank_transfer_html = ""
    if bank_name and bank_account_number:
        branch_line = (
            f"<br>Branch: {escape(bank_branch)}"
            if bank_branch
            else ""
        )
        instructions_line = (
            f"<p style=\"margin:12px 0 0;color:{COLOR_TEXT_MUTED};font-size:14px;\">"
            f"{escape(bank_transfer_instructions or '')}</p>"
            if bank_transfer_instructions
            else ""
        )
        bank_transfer_html = f"""
      <div style="margin:0 0 18px;padding:14px 16px;border-radius:10px;
                  background:{COLOR_PARCHMENT};">
        <p style="margin:0 0 8px;font-size:13px;font-weight:600;color:{COLOR_CHOCOLATE};">
          Bank transfer details
        </p>
        <p style="margin:0;font-size:14px;line-height:1.6;color:{COLOR_CHOCOLATE};">
          Bank: {escape(bank_name)}<br>
          Account name: {escape(bank_account_name or '')}<br>
          Account number: {escape(bank_account_number)}{branch_line}<br>
          Reference: {escape(order_number)}
        </p>{instructions_line}
      </div>"""

    body_html = f"""
      <p style="margin:0 0 18px;">
        {escape(body_intro)}
      </p>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
             style="margin:0 0 18px;border-collapse:collapse;">
        {meta_html}
      </table>
      {summary_html}
      {bank_transfer_html}
      <p style="margin:0;color:{COLOR_TEXT_MUTED};font-size:14px;">
        {escape(get_delivery_schedule_copy_standalone().explanation)}
      </p>"""

    site_url = settings.frontend_client_url.rstrip("/")
    html = _render_layout(
        preheader=f"Your Cookie Circle order {order_number} is received.",
        eyebrow="Order received",
        headline="Thank you for your order",
        body_html=body_html,
        cta_label="View our collections",
        cta_url=site_url,
        footer_note="Questions? Reply to this email — we are happy to help.",
    )

    schedule = get_delivery_schedule_copy_standalone()
    text_lines = [
        f"{_subject_prefix()}Your Cookie Circle order {order_number}\n",
        f"{body_intro}\n",
        f"Order number: {order_number}",
        f"Order type: {order_type_label}",
        f"Scheduled delivery: {_format_date(scheduled_delivery_date)}",
        "",
        "Order summary",
    ]
    text_lines.extend(
        _render_order_summary_text(
            order_summary=order_summary,
            total_amount=total_amount,
            products_subtotal=products_subtotal,
            collections_subtotal=collections_subtotal,
            delivery_fee=delivery_fee,
            discount_amount=discount_amount,
            discount_label=discount_label,
            tax_lines=tax_lines,
            premium_packaging_notice=premium_packaging_notice,
        ),
    )
    if bank_name and bank_account_number:
        text_lines.append("")
        text_lines.append("Bank transfer details:")
        text_lines.append(f"Bank: {bank_name}")
        text_lines.append(f"Account name: {bank_account_name or ''}")
        text_lines.append(f"Account number: {bank_account_number}")
        if bank_branch:
            text_lines.append(f"Branch: {bank_branch}")
        text_lines.append(f"Reference: {order_number}")
        if bank_transfer_instructions:
            text_lines.append(bank_transfer_instructions)
    text_lines.extend(["", schedule.explanation])
    text = "\n".join(text_lines)
    return EmailContent(
        subject=f"{_subject_prefix()}Your Cookie Circle order {order_number}",
        html=html,
        text=text,
    )


def _dashed_rule_html() -> str:
    return f"""
      <tr>
        <td colspan="2" style="padding:12px 0;">
          <div style="border-top:1px dashed {COLOR_PARCHMENT};font-size:0;line-height:0;">&nbsp;</div>
        </td>
      </tr>"""


def _money_row_html(label: str, value_html: str, *, emphasize: bool = False) -> str:
    label_weight = "700" if emphasize else "400"
    value_weight = "700" if emphasize else "600"
    label_size = "15px" if emphasize else "13px"
    value_size = "15px" if emphasize else "14px"
    return f"""
      <tr>
        <td style="padding:6px 0;font-size:{label_size};font-weight:{label_weight};
                   color:{COLOR_TEXT_MUTED if not emphasize else COLOR_CHOCOLATE};">{label}</td>
        <td align="right" style="padding:6px 0;font-size:{value_size};font-weight:{value_weight};
                   color:{COLOR_CHOCOLATE};white-space:nowrap;">{value_html}</td>
      </tr>"""


def _render_order_summary_html(
    *,
    order_summary: OrderEmailSummary | None,
    order_type_label: str,
    total_amount: Decimal,
    products_subtotal: Decimal | None,
    collections_subtotal: Decimal | None,
    delivery_fee: Decimal | None,
    discount_amount: Decimal | None,
    discount_label: str | None,
    tax_lines: list[tuple[str, Decimal]] | None,
    premium_packaging_notice: str | None,
) -> str:
    items_html = ""
    if order_summary:
        for block in order_summary.collection_blocks:
            cookie_rows = "".join(
                f"""
                <tr>
                  <td style="padding:3px 0;font-size:13px;color:{COLOR_TEXT_MUTED};">
                    {escape(cookie.name)}
                  </td>
                  <td align="right" style="padding:3px 0;font-size:13px;color:{COLOR_TEXT_MUTED};
                             white-space:nowrap;">×{escape(cookie.quantity_label)}</td>
                </tr>"""
                for cookie in block.cookies
            )
            items_html += f"""
              <tr>
                <td colspan="2" style="padding:10px 0 4px;font-size:14px;font-weight:600;
                           color:{COLOR_CHOCOLATE};">{escape(block.title)}</td>
              </tr>
              {cookie_rows}"""

        for product in order_summary.product_lines:
            items_html += f"""
              <tr>
                <td style="padding:6px 0;font-size:14px;color:{COLOR_CHOCOLATE};">
                  {escape(product.name)}
                </td>
                <td align="right" style="padding:6px 0;font-size:13px;color:{COLOR_TEXT_MUTED};
                           white-space:nowrap;">×{escape(product.quantity_label)}</td>
              </tr>"""

    packages = (
        order_summary.packages_subtotal
        if order_summary and order_summary.packages_subtotal is not None
        else collections_subtotal
    )
    cookies = (
        order_summary.cookies_subtotal
        if order_summary and order_summary.cookies_subtotal is not None
        else products_subtotal
    )
    delivery = (
        order_summary.delivery_fee
        if order_summary and order_summary.delivery_fee is not None
        else delivery_fee
    )
    discount = (
        order_summary.discount_amount
        if order_summary and order_summary.discount_amount is not None
        else discount_amount
    )
    discount_name = (
        (order_summary.discount_label if order_summary else None) or discount_label or "Discount"
    )
    resolved_tax_lines = (
        list(order_summary.tax_lines) if order_summary and order_summary.tax_lines else (tax_lines or [])
    )
    total = order_summary.total if order_summary else total_amount
    packaging_notice = (
        (order_summary.premium_packaging_notice if order_summary else None)
        or premium_packaging_notice
    )
    payment_label = order_summary.payment_method_label if order_summary else None
    subtitle = order_summary.order_type_label if order_summary else order_type_label

    totals_html = ""
    if cookies is not None and cookies > 0:
        totals_html += _money_row_html("Cookies subtotal", escape(_format_lkr(cookies)))
    if packages is not None and packages > 0:
        totals_html += _money_row_html("Packages subtotal", escape(_format_lkr(packages)))
    if delivery is not None:
        totals_html += _money_row_html("Delivery", escape(_format_lkr(delivery)))
    if discount is not None and discount > 0:
        totals_html += _money_row_html(
            escape(discount_name),
            f"<span style='color:#2d6a2d'>− {escape(_format_lkr(discount))}</span>",
        )
    for tax_label, tax_applied in resolved_tax_lines:
        totals_html += _money_row_html(escape(tax_label), escape(_format_lkr(tax_applied)))

    packaging_html = ""
    if packaging_notice:
        packaging_html = f"""
      <tr>
        <td colspan="2" style="padding:10px 0 4px;">
          <div style="display:inline-block;padding:8px 12px;border-radius:999px;
                      background:{COLOR_PARCHMENT};font-size:12px;color:{COLOR_CHOCOLATE};">
            🎁 {escape(packaging_notice)}
          </div>
        </td>
      </tr>"""

    payment_html = ""
    if payment_label:
        payment_html = f"""
      <tr>
        <td colspan="2" style="padding-top:14px;">
          <div style="padding:14px 16px;border-radius:12px;border:1px solid {COLOR_PARCHMENT};
                      background:{COLOR_IVORY};">
            <p style="margin:0 0 4px;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;
                      color:{COLOR_TEXT_MUTED};">Payment method</p>
            <p style="margin:0;font-size:14px;font-weight:600;color:{COLOR_CHOCOLATE};">
              {escape(payment_label)}
            </p>
          </div>
        </td>
      </tr>"""

    return f"""
      <div style="margin:0 0 18px;padding:16px 16px 14px;border-radius:14px;
                  border:1px solid {COLOR_PARCHMENT};background:{COLOR_CREAM};">
        <p style="margin:0 0 4px;font-size:11px;letter-spacing:0.18em;text-transform:uppercase;
                  color:{COLOR_TEXT_MUTED};">Order summary</p>
        <p style="margin:0 0 4px;font-size:15px;font-weight:600;color:{COLOR_CHOCOLATE};">
          {escape(subtitle)}
        </p>
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
               style="border-collapse:collapse;">
          {_dashed_rule_html()}
          {items_html}
          {_dashed_rule_html() if items_html else ""}
          {totals_html}
          {packaging_html}
          {_dashed_rule_html()}
          {_money_row_html("Total", escape(_format_lkr(total)), emphasize=True)}
          {payment_html}
        </table>
      </div>"""


def _render_order_summary_text(
    *,
    order_summary: OrderEmailSummary | None,
    total_amount: Decimal,
    products_subtotal: Decimal | None,
    collections_subtotal: Decimal | None,
    delivery_fee: Decimal | None,
    discount_amount: Decimal | None,
    discount_label: str | None,
    tax_lines: list[tuple[str, Decimal]] | None,
    premium_packaging_notice: str | None,
) -> list[str]:
    lines: list[str] = []
    if order_summary:
        for block in order_summary.collection_blocks:
            lines.append(block.title)
            for cookie in block.cookies:
                lines.append(f"  - {cookie.name} ×{cookie.quantity_label}")
        for product in order_summary.product_lines:
            lines.append(f"{product.name} ×{product.quantity_label}")

    packages = (
        order_summary.packages_subtotal
        if order_summary and order_summary.packages_subtotal is not None
        else collections_subtotal
    )
    cookies = (
        order_summary.cookies_subtotal
        if order_summary and order_summary.cookies_subtotal is not None
        else products_subtotal
    )
    delivery = (
        order_summary.delivery_fee
        if order_summary and order_summary.delivery_fee is not None
        else delivery_fee
    )
    discount = (
        order_summary.discount_amount
        if order_summary and order_summary.discount_amount is not None
        else discount_amount
    )
    discount_name = (
        (order_summary.discount_label if order_summary else None) or discount_label or "Discount"
    )
    resolved_tax_lines = (
        list(order_summary.tax_lines) if order_summary and order_summary.tax_lines else (tax_lines or [])
    )
    total = order_summary.total if order_summary else total_amount
    packaging_notice = (
        (order_summary.premium_packaging_notice if order_summary else None)
        or premium_packaging_notice
    )

    if cookies is not None and cookies > 0:
        lines.append(f"Cookies subtotal: {_format_lkr(cookies)}")
    if packages is not None and packages > 0:
        lines.append(f"Packages subtotal: {_format_lkr(packages)}")
    if delivery is not None:
        lines.append(f"Delivery: {_format_lkr(delivery)}")
    if discount is not None and discount > 0:
        lines.append(f"{discount_name}: − {_format_lkr(discount)}")
    for tax_label, tax_applied in resolved_tax_lines:
        lines.append(f"{tax_label}: {_format_lkr(tax_applied)}")
    if packaging_notice:
        lines.append(packaging_notice)
    lines.append(f"Total: {_format_lkr(total)}")
    if order_summary and order_summary.payment_method_label:
        lines.append(f"Payment method: {order_summary.payment_method_label}")
    return lines


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
    notification_intro: str | None = None,
    notification_headline: str | None = None,
    notification_eyebrow: str | None = None,
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

    intro = notification_intro or (
        "A new order has been placed and is ready for your team to review in the admin panel."
    )
    headline = notification_headline or "New order received"
    eyebrow = notification_eyebrow or "Team alert"

    body_html = f"""
      <p style="margin:0 0 18px;">
        {escape(intro)}
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
        eyebrow=eyebrow,
        headline=headline,
        body_html=body_html,
        cta_label="Open in admin",
        cta_url=admin_order_url,
    )
    text_lines = [
        f"{_subject_prefix()}New Cookie Circle order {order_number}\n",
        f"{intro}\n",
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
