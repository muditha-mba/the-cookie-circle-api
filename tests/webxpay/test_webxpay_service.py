"""
Unit tests for WebXPay service layer.

Covers: idempotency, state machine, amount verification, and return processing.
Uses fixture keys and an in-memory SQLite-like test harness (pure unit tests).
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.enums import PaymentMethod, PaymentSessionStatus, PaymentStatus
from app.models.payment_session import PaymentSession
from app.services.webxpay.encryption import (
    is_approved_status,
    parse_decrypted_payment,
)

FIXTURES = Path(__file__).parent
PUBLIC_KEY_PEM = (FIXTURES / "test_public.pem").read_text()
PRIVATE_KEY_PEM = (FIXTURES / "test_private.pem").read_text()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _private_key_sign(plaintext: bytes) -> str:
    """Simulate WebXPay private-key signing (same helper as test_encryption.py)."""
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    private_key = load_pem_private_key(PRIVATE_KEY_PEM.encode(), password=None)
    numbers = private_key.private_numbers()  # type: ignore[attr-defined]
    n = numbers.public_numbers.n
    d = numbers.d
    key_size_bytes = (private_key.key_size + 7) // 8  # type: ignore[attr-defined]

    msg = plaintext
    pad_len = key_size_bytes - len(msg) - 3
    padded = b"\x00\x01" + (b"\xff" * pad_len) + b"\x00" + msg
    m = int.from_bytes(padded, "big")
    result_int = pow(m, d, n)
    ciphertext = result_int.to_bytes(key_size_bytes, "big")
    return base64.b64encode(ciphertext).decode("ascii")


def _make_valid_return_fields(
    order_number: str = "WEB-20240601-0001",
    status_code: str = "0",
    gateway_reference: str = "T12345",
) -> dict[str, str]:
    payload = f"{order_number}|{gateway_reference}|2024-06-01 10:00:00|{status_code}|Approved|5".encode()
    payment_b64 = _private_key_sign(payload)
    signature_b64 = _private_key_sign(payload)
    return {"payment": payment_b64, "signature": signature_b64}


# ── Encryption / idempotency key tests ───────────────────────────────────────


def test_is_approved_status_known_codes() -> None:
    assert is_approved_status("0") is True
    assert is_approved_status("00") is True
    assert is_approved_status("15") is False


def test_parse_returns_all_fields() -> None:
    plaintext = b"ORD-001|T99999|2024-01-01 00:00:00|0|Ok|5"
    result = parse_decrypted_payment(plaintext)
    assert result["order_number"] == "ORD-001"
    assert result["gateway_reference"] == "T99999"
    assert result["status_code"] == "0"


# ── Session state machine tests ───────────────────────────────────────────────


def _mock_session(
    status: PaymentSessionStatus = PaymentSessionStatus.REDIRECTED,
    initiated_at: datetime | None = None,
    gateway_reference: str | None = None,
) -> MagicMock:
    session = MagicMock(spec=PaymentSession)
    session.status = status
    session.initiated_at = initiated_at or datetime.now(UTC)
    session.gateway_reference = gateway_reference
    session.amount = Decimal("1500.00")
    return session


def _mock_order(order_number: str = "WEB-20240601-0001") -> MagicMock:
    order = MagicMock()
    order.order_number = order_number
    order.payment_status = PaymentStatus.PENDING
    order.total_revenue_snapshot = Decimal("1500.00")
    return order


def test_return_handler_success_with_valid_signature() -> None:
    from app.services.webxpay.webxpay_service import WebXPayService

    session = _mock_session()
    order = _mock_order()
    session.order = order

    fields = _make_valid_return_fields(order_number="WEB-20240601-0001", status_code="0")

    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.first.return_value = session
    db.flush = MagicMock()

    service = WebXPayService(db)

    with patch("app.services.webxpay.webxpay_service.settings") as mock_cfg:
        mock_cfg.webxpay_public_key_pem = PUBLIC_KEY_PEM
        result_session, result_order, approved = service.process_return(fields)

    assert approved is True
    assert result_session.status == PaymentSessionStatus.COMPLETED
    assert result_order.payment_status == PaymentStatus.PAID


def test_return_handler_declined_payment() -> None:
    from app.services.webxpay.webxpay_service import WebXPayService

    session = _mock_session()
    order = _mock_order()
    session.order = order

    fields = _make_valid_return_fields(order_number="WEB-20240601-0001", status_code="15")

    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.first.return_value = session
    db.flush = MagicMock()

    service = WebXPayService(db)

    with patch("app.services.webxpay.webxpay_service.settings") as mock_cfg:
        mock_cfg.webxpay_public_key_pem = PUBLIC_KEY_PEM
        result_session, result_order, approved = service.process_return(fields)

    assert approved is False
    assert result_session.status == PaymentSessionStatus.FAILED
    assert result_order.payment_status == PaymentStatus.FAILED


def test_return_handler_invalid_signature_raises() -> None:
    from app.services.webxpay.webxpay_service import WebXPayService

    db = MagicMock()
    service = WebXPayService(db)

    with patch("app.services.webxpay.webxpay_service.settings") as mock_cfg:
        mock_cfg.webxpay_public_key_pem = PUBLIC_KEY_PEM
        with pytest.raises(ValueError, match="[Ss]ignature"):
            service.process_return({"payment": "aGVsbG8=", "signature": "d29ybGQ="})


def test_return_handler_missing_fields_raises() -> None:
    from app.services.webxpay.webxpay_service import WebXPayService

    db = MagicMock()
    service = WebXPayService(db)

    with patch("app.services.webxpay.webxpay_service.settings") as mock_cfg:
        mock_cfg.webxpay_public_key_pem = PUBLIC_KEY_PEM
        with pytest.raises(ValueError, match="Missing"):
            service.process_return({})


def test_return_handler_idempotent_completed() -> None:
    """Duplicate callback for already-completed session returns approved without re-processing."""
    from app.services.webxpay.webxpay_service import WebXPayService

    session = _mock_session(status=PaymentSessionStatus.COMPLETED)
    order = _mock_order()
    session.order = order

    fields = _make_valid_return_fields()

    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.first.return_value = session
    db.flush = MagicMock()

    service = WebXPayService(db)

    with patch("app.services.webxpay.webxpay_service.settings") as mock_cfg:
        mock_cfg.webxpay_public_key_pem = PUBLIC_KEY_PEM
        result_session, result_order, approved = service.process_return(fields)

    assert approved is True
    # Status must NOT change — already completed
    assert result_session.status == PaymentSessionStatus.COMPLETED


def test_return_handler_idempotent_failed() -> None:
    """Duplicate callback for already-failed session returns not-approved without re-processing."""
    from app.services.webxpay.webxpay_service import WebXPayService

    session = _mock_session(status=PaymentSessionStatus.FAILED)
    order = _mock_order()
    session.order = order

    fields = _make_valid_return_fields()

    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.order_by.return_value.first.return_value = session
    db.flush = MagicMock()

    service = WebXPayService(db)

    with patch("app.services.webxpay.webxpay_service.settings") as mock_cfg:
        mock_cfg.webxpay_public_key_pem = PUBLIC_KEY_PEM
        result_session, result_order, approved = service.process_return(fields)

    assert approved is False
    assert result_session.status == PaymentSessionStatus.FAILED


def test_session_expiry_detection() -> None:
    from app.services.webxpay.webxpay_service import _is_session_expired

    old_initiated = datetime.now(UTC) - timedelta(minutes=31)
    recent_initiated = datetime.now(UTC) - timedelta(minutes=10)

    old_session = _mock_session(initiated_at=old_initiated)
    recent_session = _mock_session(initiated_at=recent_initiated)

    assert _is_session_expired(old_session) is True
    assert _is_session_expired(recent_session) is False


def test_idempotency_key_is_deterministic() -> None:
    from app.services.webxpay.webxpay_service import _build_idempotency_key

    order = MagicMock()
    order.id = "550e8400-e29b-41d4-a716-446655440000"
    order.order_number = "WEB-20240601-0001"
    order.total_revenue_snapshot = Decimal("1500.00")

    key1 = _build_idempotency_key(order)
    key2 = _build_idempotency_key(order)
    assert key1 == key2
    assert len(key1) == 64  # sha256 hex
