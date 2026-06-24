"""
WebXPay payment endpoints.

GET  /payments/webxpay/initiate/{session_id}
    Server-side HTML page that auto-submits a hidden form to the WebXPay
    billing URL.  Serves the secret_key inside the form — this is WebXPay's
    designed security model for redirect integration.  The page is only
    accessible by knowing the unguessable session_id UUID.

POST /payments/webxpay/return
    Receives the browser POST redirect from WebXPay after payment processing.
    Verifies signature, transitions PaymentSession and Order.payment_status,
    then redirects the browser to success or failure page.

Neither endpoint requires authentication — the initiation page is secured by
the unguessable session UUID, and the return handler is secured by WebXPay's
cryptographic signature.
"""

from __future__ import annotations

import logging
import textwrap
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.services.webxpay.webxpay_service import WebXPayService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])

# ── Initiation page ───────────────────────────────────────────────────────────


@router.get(
    "/webxpay/initiate/{session_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def initiate_webxpay_payment(
    session_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    """
    Serve an HTML page that auto-submits a POST form to the WebXPay billing URL.

    This keeps the secret_key and encrypted payment blob server-side until
    the final form submission.  The page is single-use per session.
    """
    if not settings.webxpay_enabled:
        return _error_page("Online payment is currently unavailable.")

    service = WebXPayService(db)
    session = service.get_active_session(session_id)

    if session is None:
        return _error_page(
            "Your payment session has expired or is no longer valid. "
            "Please return to the website and place your order again.",
            title="Session Expired",
        )

    order = session.order
    if order is None:
        return _error_page("Order not found.")

    try:
        form_fields = service.build_form_fields(order, session)
    except Exception:
        logger.exception(
            "Failed to build WebXPay form fields for session=%s", session_id
        )
        return _error_page("Unable to initiate payment. Please try again.")

    service.mark_redirected(session)
    db.commit()

    cancel_url = settings.webxpay_cancel_url or f"{settings.frontend_client_url.rstrip('/')}/cart"
    billing_url = settings.webxpay_billing_url

    hidden_inputs = "\n".join(
        f'    <input type="hidden" name="{_esc(k)}" value="{_esc(v)}">'
        for k, v in form_fields.items()
    )

    html = textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>Redirecting to Secure Payment…</title>
          <style>
            body {{
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              display: flex; flex-direction: column; align-items: center;
              justify-content: center; min-height: 100vh; margin: 0;
              background: #faf9f7; color: #333;
            }}
            .card {{
              background: #fff; border-radius: 12px; padding: 40px 48px;
              box-shadow: 0 2px 16px rgba(0,0,0,.08); text-align: center;
              max-width: 420px; width: 90%;
            }}
            .spinner {{
              width: 40px; height: 40px; border: 3px solid #eee;
              border-top-color: #8b5e3c; border-radius: 50%;
              animation: spin .8s linear infinite; margin: 0 auto 24px;
            }}
            @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
            h2 {{ font-size: 1.2rem; margin: 0 0 8px; font-weight: 600; }}
            p  {{ color: #666; font-size: .9rem; margin: 0 0 24px; }}
            button {{
              background: #8b5e3c; color: #fff; border: none; border-radius: 8px;
              padding: 12px 28px; font-size: .95rem; cursor: pointer; display: none;
            }}
            button:hover {{ background: #7a5232; }}
            a {{ color: #8b5e3c; font-size: .85rem; }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="spinner" id="spinner"></div>
            <h2>Redirecting to Secure Payment</h2>
            <p>Please wait while we redirect you to WebXPay's secure payment page.</p>
            <button id="manual-btn" onclick="document.getElementById('pay-form').submit()">
              Continue to Payment
            </button>
            <br>
            <a href="{_esc(cancel_url)}" id="cancel-link" style="display:none;margin-top:12px;">
              Cancel and return to cart
            </a>
          </div>

          <form id="pay-form" method="POST" action="{_esc(billing_url)}">
        {hidden_inputs}
          </form>

          <script>
            (function () {{
              try {{
                document.getElementById("pay-form").submit();
              }} catch (e) {{
                document.getElementById("spinner").style.display = "none";
                document.getElementById("manual-btn").style.display = "inline-block";
                document.getElementById("cancel-link").style.display = "inline";
              }}
              // Fallback: show manual button after 5 s if form hasn't submitted
              setTimeout(function () {{
                var btn = document.getElementById("manual-btn");
                var lnk = document.getElementById("cancel-link");
                if (btn) {{ btn.style.display = "inline-block"; }}
                if (lnk) {{ lnk.style.display = "inline"; }}
              }}, 5000);
            }})();
          </script>
        </body>
        </html>
    """)
    return HTMLResponse(content=html, status_code=200)


# ── Return handler ────────────────────────────────────────────────────────────


@router.post(
    "/webxpay/return",
    response_class=RedirectResponse,
    include_in_schema=False,
)
async def handle_webxpay_return(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    """
    Handle the browser POST redirect from WebXPay after payment processing.

    WebXPay POSTs: payment (base64 RSA-signed blob), signature, custom_fields
    We: verify signature → parse → transition session + order → redirect browser.

    This endpoint must NOT require authentication and must NOT validate CSRF tokens,
    as it is called by a browser redirect from WebXPay's domain.

    Always returns a redirect — never a JSON error — because the browser is
    waiting for a navigation response.
    """
    client_base = settings.frontend_client_url.rstrip("/")

    try:
        form_data = await request.form()
        fields = dict(form_data)
    except Exception:
        logger.error("WebXPay return: failed to parse form data")
        return _redirect_failed(client_base)

    if not settings.webxpay_enabled:
        logger.warning("WebXPay return received but WEBXPAY_ENABLED=false")
        return _redirect_failed(client_base)

    service = WebXPayService(db)

    try:
        session, order, approved = service.process_return(fields)
        db.commit()
    except ValueError as exc:
        logger.warning("WebXPay return rejected: %s", exc)
        return _redirect_failed(client_base)
    except Exception:
        logger.exception("WebXPay return: unexpected error during processing")
        db.rollback()
        return _redirect_failed(client_base)

    if approved:
        return _redirect_success(client_base, order.id)
    return _redirect_failed(client_base, order_id=order.id)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _esc(value: str) -> str:
    """Minimal HTML attribute escaping."""
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _error_page(message: str, title: str = "Payment Unavailable") -> HTMLResponse:
    html = textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <title>{_esc(title)}</title>
          <style>
            body {{
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              display: flex; align-items: center; justify-content: center;
              min-height: 100vh; margin: 0; background: #faf9f7;
            }}
            .card {{
              background: #fff; border-radius: 12px; padding: 40px 48px;
              box-shadow: 0 2px 16px rgba(0,0,0,.08); text-align: center;
              max-width: 420px; width: 90%;
            }}
            h2 {{ color: #c0392b; margin: 0 0 12px; }}
            p  {{ color: #666; margin: 0 0 24px; }}
            a  {{ color: #8b5e3c; }}
          </style>
        </head>
        <body>
          <div class="card">
            <h2>{_esc(title)}</h2>
            <p>{_esc(message)}</p>
            <a href="{_esc(settings.frontend_client_url.rstrip('/') + '/cart')}">
              Return to cart
            </a>
          </div>
        </body>
        </html>
    """)
    return HTMLResponse(content=html, status_code=200)


def _redirect_success(client_base: str, order_id: object) -> RedirectResponse:
    url = f"{client_base}/account/orders/{order_id}/payment/success"
    return RedirectResponse(url=url, status_code=303)


def _redirect_failed(client_base: str, order_id: object | None = None) -> RedirectResponse:
    if order_id is not None:
        url = f"{client_base}/account/orders/{order_id}/payment/failed"
    else:
        url = f"{client_base}/cart"
    return RedirectResponse(url=url, status_code=303)
