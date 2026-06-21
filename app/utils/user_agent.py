"""Lightweight User-Agent parsing for client context logging."""

import re
from dataclasses import dataclass

from app.core.enums import ClientDeviceType

_MAX_UA_LENGTH = 512

_BOT_PATTERN = re.compile(
    r"(bot|crawler|spider|slurp|curl|wget|python-requests|httpclient|postman)",
    re.IGNORECASE,
)
_EDGE_PATTERN = re.compile(r"Edg/([\d.]+)")
_CHROME_PATTERN = re.compile(r"Chrome/([\d.]+)")
_FIREFOX_PATTERN = re.compile(r"Firefox/([\d.]+)")
_SAFARI_VERSION_PATTERN = re.compile(r"Version/([\d.]+)")
_WINDOWS_PATTERN = re.compile(r"Windows NT ([\d.]+)")
_MAC_PATTERN = re.compile(r"Mac OS X ([\d_]+)")
_ANDROID_PATTERN = re.compile(r"Android ([\d.]+)")
_IOS_PATTERN = re.compile(r"OS ([\d_]+) like Mac OS X")
_IPAD_PATTERN = re.compile(r"iPad")


@dataclass(frozen=True, slots=True)
class ParsedUserAgent:
    """Normalized browser and device details."""

    user_agent: str | None
    browser_name: str | None
    browser_version: str | None
    os_name: str | None
    os_version: str | None
    device_type: ClientDeviceType


def _normalize_version(value: str) -> str:
    return value.replace("_", ".")


def parse_user_agent(raw_user_agent: str | None) -> ParsedUserAgent:
    """Parse a User-Agent string into coarse browser/OS/device fields."""
    if not raw_user_agent or not raw_user_agent.strip():
        return ParsedUserAgent(
            user_agent=None,
            browser_name=None,
            browser_version=None,
            os_name=None,
            os_version=None,
            device_type=ClientDeviceType.UNKNOWN,
        )

    user_agent = raw_user_agent.strip()[:_MAX_UA_LENGTH]

    if _BOT_PATTERN.search(user_agent):
        return ParsedUserAgent(
            user_agent=user_agent,
            browser_name="Bot",
            browser_version=None,
            os_name=None,
            os_version=None,
            device_type=ClientDeviceType.BOT,
        )

    browser_name: str | None = None
    browser_version: str | None = None
    if edge_match := _EDGE_PATTERN.search(user_agent):
        browser_name = "Edge"
        browser_version = edge_match.group(1)
    elif chrome_match := _CHROME_PATTERN.search(user_agent):
        browser_name = "Chrome"
        browser_version = chrome_match.group(1)
    elif firefox_match := _FIREFOX_PATTERN.search(user_agent):
        browser_name = "Firefox"
        browser_version = firefox_match.group(1)
    elif "Safari/" in user_agent and "Chrome/" not in user_agent:
        browser_name = "Safari"
        if safari_match := _SAFARI_VERSION_PATTERN.search(user_agent):
            browser_version = safari_match.group(1)

    os_name: str | None = None
    os_version: str | None = None
    if windows_match := _WINDOWS_PATTERN.search(user_agent):
        os_name = "Windows"
        os_version = windows_match.group(1)
    elif _IPAD_PATTERN.search(user_agent):
        os_name = "iPadOS"
        if ios_match := _IOS_PATTERN.search(user_agent):
            os_version = _normalize_version(ios_match.group(1))
    elif "iPhone" in user_agent or "iPod" in user_agent:
        os_name = "iOS"
        if ios_match := _IOS_PATTERN.search(user_agent):
            os_version = _normalize_version(ios_match.group(1))
    elif android_match := _ANDROID_PATTERN.search(user_agent):
        os_name = "Android"
        os_version = android_match.group(1)
    elif mac_match := _MAC_PATTERN.search(user_agent):
        os_name = "macOS"
        os_version = _normalize_version(mac_match.group(1))
    elif "Linux" in user_agent:
        os_name = "Linux"

    device_type = ClientDeviceType.DESKTOP
    if _IPAD_PATTERN.search(user_agent) or "Tablet" in user_agent:
        device_type = ClientDeviceType.TABLET
    elif (
        "Mobile" in user_agent
        or "iPhone" in user_agent
        or "iPod" in user_agent
        or (os_name == "Android" and "Mobile" in user_agent)
    ):
        device_type = ClientDeviceType.MOBILE
    elif os_name in {"iOS", "Android"}:
        device_type = ClientDeviceType.MOBILE

    return ParsedUserAgent(
        user_agent=user_agent,
        browser_name=browser_name,
        browser_version=browser_version,
        os_name=os_name,
        os_version=os_version,
        device_type=device_type,
    )
