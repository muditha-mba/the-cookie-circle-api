"""HTTP client context helpers for audit logging."""

from dataclasses import dataclass

from starlette.requests import Request

from app.core.enums import ClientDeviceType
from app.utils.client_ip import get_client_ip
from app.utils.user_agent import ParsedUserAgent, parse_user_agent


@dataclass(frozen=True, slots=True)
class ClientContext:
    """Network and client software context for a request."""

    ip_address: str | None
    user_agent: str | None
    browser_name: str | None
    browser_version: str | None
    os_name: str | None
    os_version: str | None
    device_type: ClientDeviceType


def client_context_from_request(request: Request) -> ClientContext:
    """Build client context from an incoming HTTP request."""
    parsed = parse_user_agent(request.headers.get("user-agent"))
    return ClientContext(
        ip_address=get_client_ip(request),
        user_agent=parsed.user_agent,
        browser_name=parsed.browser_name,
        browser_version=parsed.browser_version,
        os_name=parsed.os_name,
        os_version=parsed.os_version,
        device_type=parsed.device_type,
    )


def client_context_from_headers(
    *,
    ip_address: str | None,
    user_agent: str | None,
) -> ClientContext:
    """Build client context from explicit header values."""
    parsed = parse_user_agent(user_agent)
    return ClientContext(
        ip_address=ip_address,
        user_agent=parsed.user_agent,
        browser_name=parsed.browser_name,
        browser_version=parsed.browser_version,
        os_name=parsed.os_name,
        os_version=parsed.os_version,
        device_type=parsed.device_type,
    )
