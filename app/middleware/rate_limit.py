"""In-memory rate limiting for sensitive public endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.services.security_audit import log_security_event
from app.utils.client_ip import get_client_ip


@dataclass(frozen=True)
class RateLimitRule:
    method: str
    path: str
    max_requests: int
    window_seconds: int


RATE_LIMIT_RULES: tuple[RateLimitRule, ...] = (
    RateLimitRule("POST", "/api/v1/auth/login", 10, 60),
    RateLimitRule("POST", "/api/v1/auth/register", 5, 60),
    RateLimitRule("POST", "/api/v1/auth/forgot-password", 5, 60),
    RateLimitRule("POST", "/api/v1/auth/resend-verification", 5, 60),
    RateLimitRule("POST", "/api/v1/auth/refresh", 30, 60),
    RateLimitRule("GET", "/api/v1/client/auth/check-email", 20, 60),
    RateLimitRule("POST", "/api/v1/client/orders/checkout", 10, 60),
    RateLimitRule("POST", "/api/v1/client/orders/preview", 30, 60),
    # WebXPay payment endpoints — the return endpoint is called by a browser
    # redirect from WebXPay, so a generous limit is appropriate.
    RateLimitRule("POST", "/api/v1/payments/webxpay/return", 20, 60),
)


class InMemoryRateLimiter:
    """Simple sliding-window limiter keyed by IP + route."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str, *, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        window_start = now - window_seconds
        events = self._events[key]

        while events and events[0] <= window_start:
            events.popleft()

        if len(events) >= max_requests:
            retry_after = max(1, int(window_seconds - (now - events[0])))
            return False, retry_after

        events.append(now)
        return True, 0


_rate_limiter = InMemoryRateLimiter()


def _match_rule(method: str, path: str) -> RateLimitRule | None:
    for rule in RATE_LIMIT_RULES:
        if rule.method == method and rule.path == path:
            return rule
    return None


def setup_rate_limit(app) -> None:
    """Register rate limiting middleware when enabled."""

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        rule = _match_rule(request.method.upper(), request.url.path)
        if rule is None:
            return await call_next(request)

        client_ip = get_client_ip(request)
        key = f"{client_ip}:{rule.method}:{rule.path}"
        allowed, retry_after = _rate_limiter.is_allowed(
            key,
            max_requests=rule.max_requests,
            window_seconds=rule.window_seconds,
        )

        if not allowed:
            log_security_event(
                "rate_limit_exceeded",
                ip_address=client_ip,
                method=rule.method,
                path=rule.path,
                metadata={"retry_after": retry_after},
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
