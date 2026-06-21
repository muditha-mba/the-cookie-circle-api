"""URL safety helpers for server-side fetches."""

from __future__ import annotations

from urllib.parse import urlparse

from app.core.exceptions import ValidationError

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "[::1]",
    },
)


def _is_private_ipv4(hostname: str) -> bool:
    parts = hostname.split(".")
    if len(parts) != 4:
        return False

    try:
        octets = [int(part) for part in parts]
    except ValueError:
        return True

    if any(octet < 0 or octet > 255 for octet in octets):
        return True

    first, second = octets[0], octets[1]

    if first == 10:
        return True
    if first == 127:
        return True
    if first == 0:
        return True
    if first == 169 and second == 254:
        return True
    if first == 172 and 16 <= second <= 31:
        return True
    if first == 192 and second == 168:
        return True

    return False


def assert_safe_remote_url(raw_url: str) -> str:
    """Validate that a URL is safe to fetch from the API (SSRF protection)."""
    trimmed = raw_url.strip()
    if not trimmed:
        raise ValidationError("Preview image URL is required.")

    parsed = urlparse(trimmed)
    if parsed.scheme not in {"http", "https"}:
        raise ValidationError("Preview image URL must use http or https.")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValidationError("Preview image URL is invalid.")

    if hostname in _BLOCKED_HOSTNAMES or _is_private_ipv4(hostname):
        raise ValidationError("Preview image URL cannot point to a private address.")

    return trimmed
