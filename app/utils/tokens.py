"""Token generation and hashing utilities."""

import hashlib
import secrets


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure URL-safe token."""
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
