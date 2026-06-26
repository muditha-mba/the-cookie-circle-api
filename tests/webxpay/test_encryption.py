"""
Unit tests for WebXPay encryption and signature verification helpers.

These tests use a fixture RSA key pair (test_private.pem / test_public.pem)
generated for test purposes only.  No real WebXPay credentials are used.

The key pair simulates WebXPay's role:
  - test_public.pem  = what we use to encrypt (WebXPay's public key)
  - test_private.pem = what "WebXPay" uses to sign return payloads
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from app.services.webxpay.encryption import (
    encrypt_payment_blob,
    is_approved_status,
    load_public_key,
    parse_decrypted_payment,
    public_key_decrypt,
    verify_return_signature,
)

FIXTURES = Path(__file__).parent
PUBLIC_KEY_PEM = (FIXTURES / "test_public.pem").read_text()
PRIVATE_KEY_PEM = (FIXTURES / "test_private.pem").read_text()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _private_key_sign(plaintext: bytes) -> str:
    """
    Simulate WebXPay's private-key 'encryption' of the return payload.
    PHP: openssl_private_encrypt($data, $enc, $private_key)
    Python: raw RSA with private exponent, then PKCS#1 type-1 pad.
    """
    private_key = load_pem_private_key(PRIVATE_KEY_PEM.encode(), password=None)
    # Use cryptography's sign with PKCS1v15 + no hash (raw)
    # We simulate openssl_private_encrypt which is PKCS#1 type 1 signature padding
    # The standard way in cryptography for this is to sign the raw data
    # Actually: PHP openssl_private_encrypt = RSA raw with private key + PKCS1 type 1 pad
    # In Python cryptography, we use PKCS1v15 signing which adds type 1 padding
    # but it normally hashes. We'll do it via the hazmat layer without hashing.
    #
    # For testing purposes, we use the RSA private key math directly:
    numbers = private_key.private_numbers()  # type: ignore[attr-defined]
    n = numbers.public_numbers.n
    d = numbers.d
    key_size_bytes = (private_key.key_size + 7) // 8  # type: ignore[attr-defined]

    # Build PKCS#1 type-1 padded message
    msg = plaintext
    pad_len = key_size_bytes - len(msg) - 3
    if pad_len < 8:
        raise ValueError("Message too long for key size")
    padded = b"\x00\x01" + (b"\xff" * pad_len) + b"\x00" + msg

    m = int.from_bytes(padded, "big")
    result_int = pow(m, d, n)
    ciphertext = result_int.to_bytes(key_size_bytes, "big")
    return base64.b64encode(ciphertext).decode("ascii")


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_load_public_key() -> None:
    key = load_public_key(PUBLIC_KEY_PEM)
    assert key.key_size == 2048  # type: ignore[attr-defined]


def test_encrypt_payment_blob_returns_base64() -> None:
    blob = encrypt_payment_blob("WEB-20240601-0001", "1500.00", PUBLIC_KEY_PEM)
    # Should be valid base64
    decoded = base64.b64decode(blob)
    assert len(decoded) == 256  # 2048-bit key = 256 bytes


def test_encrypt_payment_blob_is_not_plaintext() -> None:
    blob = encrypt_payment_blob("WEB-20240601-0001", "1500.00", PUBLIC_KEY_PEM)
    assert "WEB-20240601-0001" not in blob
    assert "1500.00" not in blob


def test_public_key_decrypt_roundtrip() -> None:
    """Encrypt with private key, decrypt with public key (simulates WebXPay return)."""
    plaintext = b"WEB-20240601-0001|T12345|2024-06-01 10:00:00|0|Approved|5"
    signed = _private_key_sign(plaintext)
    decrypted = public_key_decrypt(signed, PUBLIC_KEY_PEM)
    assert decrypted == plaintext


def test_public_key_decrypt_wrong_data_raises() -> None:
    with pytest.raises(Exception):
        public_key_decrypt("not_valid_base64!!!!", PUBLIC_KEY_PEM)


def test_verify_return_signature_valid() -> None:
    payload = b"WEB-20240601-0001|T12345|2024-06-01 10:00:00|0|Approved|5"
    payment_b64 = _private_key_sign(payload)
    signature_b64 = _private_key_sign(payload)

    is_valid, decrypted = verify_return_signature(payment_b64, signature_b64, PUBLIC_KEY_PEM)
    assert is_valid is True
    assert decrypted == payload


def test_verify_return_signature_tampered_payment() -> None:
    payload = b"WEB-20240601-0001|T12345|2024-06-01 10:00:00|0|Approved|5"
    tampered = b"WEB-20240601-0001|T12345|2024-06-01 10:00:00|0|Approved|5|EXTRA"
    payment_b64 = _private_key_sign(tampered)
    signature_b64 = _private_key_sign(payload)

    is_valid, decrypted = verify_return_signature(payment_b64, signature_b64, PUBLIC_KEY_PEM)
    assert is_valid is False
    assert decrypted is None


def test_verify_return_signature_invalid_b64() -> None:
    is_valid, decrypted = verify_return_signature("!!!not_base64", "also_bad", PUBLIC_KEY_PEM)
    assert is_valid is False
    assert decrypted is None


def test_parse_decrypted_payment_full() -> None:
    plaintext = b"WEB-20240601-0001|T372016I24522|2024-06-01 09:57:52|0|Approved|5"
    result = parse_decrypted_payment(plaintext)
    assert result["order_number"] == "WEB-20240601-0001"
    assert result["gateway_reference"] == "T372016I24522"
    assert result["transaction_datetime"] == "2024-06-01 09:57:52"
    assert result["status_code"] == "0"
    assert result["comment"] == "Approved"
    assert result["gateway_id"] == "5"


def test_parse_decrypted_payment_partial() -> None:
    plaintext = b"WEB-20240601-0001|T12345"
    result = parse_decrypted_payment(plaintext)
    assert result["order_number"] == "WEB-20240601-0001"
    assert result["gateway_reference"] == "T12345"
    assert result["status_code"] == ""


def test_is_approved_status_codes() -> None:
    assert is_approved_status("0") is True
    assert is_approved_status("00") is True
    assert is_approved_status("15") is False
    assert is_approved_status("") is False
    assert is_approved_status("401") is False
