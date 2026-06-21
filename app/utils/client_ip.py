"""Client IP resolution for rate limiting and access controls."""

from fastapi import Request

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """Resolve the client IP, optionally trusting reverse-proxy headers."""
    if settings.rate_limit_trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host
    return "unknown"
