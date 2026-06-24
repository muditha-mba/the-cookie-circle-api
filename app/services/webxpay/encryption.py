"""
WebXPay RSA encryption and public-key verification helpers.

WebXPay Redirect Integration cryptography (v3.0 spec):

REQUEST (us → WebXPay):
  payload  = f"{order_number}|{amount:.2f}"
  payment  = base64( RSA-PKCS1v15-encrypt(payload, webxpay_public_key) )

  PHP equivalent: openssl_public_encrypt($payload, $enc, $pubkey, OPENSSL_PKCS1_PADDING)
                  base64_encode($enc)

RETURN (WebXPay → us, via browser POST):
  Fields: payment, signature

  Both `payment` and `signature` are base64-encoded values that were signed
  (i.e., encrypted) by WebXPay using their *private* key.  We verify them by
  performing a raw RSA operation with the *public* key (modular exponentiation
  with the public exponent, then PKCS#1 type-1 unpadding).

  PHP equivalent: openssl_public_decrypt(base64_decode($field), $plain, $pubkey)

  Verification: both decrypted plaintexts must be identical.

  Decrypted `payment` format:
      order_number|gateway_reference|datetime|status_code|comment|gateway_id

  Status codes: "0" or "00" = approved, "15" = declined.
"""

from __future__ import annotations

import base64
import logging

from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.serialization import load_pem_public_key

logger = logging.getLogger(__name__)

# Session expiry threshold in minutes — sessions older than this are treated as expired.
SESSION_EXPIRY_MINUTES = 30


def load_public_key(pem: str):
    """Load an RSA public key from a PEM string (supports \\n-escaped newlines)."""
    normalized = pem.replace("\\n", "\n").strip()
    return load_pem_public_key(normalized.encode())


def encrypt_payment_blob(order_number: str, amount: str, public_key_pem: str) -> str:
    """
    Build and encrypt the WebXPay payment blob.

    payload  = "{order_number}|{amount}"  (e.g. "WEB-20240601-0001|1500.00")
    returns  base64-encoded RSA-PKCS1v15 ciphertext
    """
    payload = f"{order_number}|{amount}"
    pub_key = load_public_key(public_key_pem)
    ciphertext = pub_key.encrypt(payload.encode("utf-8"), PKCS1v15())
    return base64.b64encode(ciphertext).decode("ascii")


def _pkcs1_type1_unpad(data: bytes) -> bytes:
    """
    Strip PKCS#1 type-1 (signature) padding from raw RSA output.

    Format: 0x00 0x01 [0xFF ... 0xFF] 0x00 [message]
    """
    if len(data) < 11 or data[0] != 0x00 or data[1] != 0x01:
        raise ValueError("Invalid PKCS#1 type-1 padding header")
    try:
        sep = data.index(0x00, 2)
    except ValueError as exc:
        raise ValueError("Malformed PKCS#1 type-1 padding: no separator") from exc
    return data[sep + 1 :]


def public_key_decrypt(b64_data: str, public_key_pem: str) -> bytes:
    """
    PHP openssl_public_decrypt equivalent.

    WebXPay signs (encrypts with their private key) the return fields.
    We verify by applying the inverse RSA operation with the public key:
      plaintext = (ciphertext ^ e) mod n  then strip PKCS#1 type-1 padding.

    This is a raw modular-exponentiation using the public exponent — it does NOT
    use Python's standard verify() path because no hash digest is involved.
    """
    ciphertext = base64.b64decode(b64_data)
    pub_key = load_public_key(public_key_pem)
    numbers = pub_key.public_numbers()  # type: ignore[attr-defined]
    n = numbers.n
    e = numbers.e
    key_size_bytes = (pub_key.key_size + 7) // 8  # type: ignore[attr-defined]

    m = int.from_bytes(ciphertext, "big")
    result_int = pow(m, e, n)
    result_bytes = result_int.to_bytes(key_size_bytes, "big")

    return _pkcs1_type1_unpad(result_bytes)


def verify_return_signature(
    payment_b64: str,
    signature_b64: str,
    public_key_pem: str,
) -> tuple[bool, bytes | None]:
    """
    Verify the WebXPay return callback integrity.

    Both `payment` and `signature` are decrypted with the public key.
    The result is authentic if and only if both decrypted plaintexts match.

    Returns:
        (is_valid, decrypted_payment_bytes)
        If verification fails, decrypted_payment_bytes is None.
    """
    try:
        decrypted_payment = public_key_decrypt(payment_b64, public_key_pem)
        decrypted_signature = public_key_decrypt(signature_b64, public_key_pem)
    except Exception:
        logger.warning("WebXPay return: decryption failed — likely tampered payload")
        return False, None

    # Constant-time comparison to prevent timing attacks
    import hmac
    if not hmac.compare_digest(decrypted_payment, decrypted_signature):
        logger.warning("WebXPay return: payment/signature mismatch — payload tampered")
        return False, None

    return True, decrypted_payment


def parse_decrypted_payment(plaintext: bytes) -> dict[str, str]:
    """
    Parse the decrypted WebXPay return payload.

    Format: order_number|gateway_reference|datetime|status_code|comment|gateway_id
    Returns a dict with string values for all fields.
    """
    text = plaintext.decode("utf-8", errors="replace").strip()
    parts = text.split("|")
    keys = [
        "order_number",
        "gateway_reference",
        "transaction_datetime",
        "status_code",
        "comment",
        "gateway_id",
    ]
    result: dict[str, str] = {}
    for i, key in enumerate(keys):
        result[key] = parts[i].strip() if i < len(parts) else ""
    return result


def is_approved_status(status_code: str) -> bool:
    """Return True for WebXPay success status codes (0 or 00)."""
    return status_code.strip() in {"0", "00"}
