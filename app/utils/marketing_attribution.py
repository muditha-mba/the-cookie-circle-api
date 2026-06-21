"""Resolve marketing attribution into CRM enums and stored metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from app.core.enums import MarketingSource
from app.schemas.attribution import MarketingAttributionInput

_UTM_SOURCE_ALIASES: dict[str, MarketingSource] = {
    "instagram": MarketingSource.INSTAGRAM,
    "ig": MarketingSource.INSTAGRAM,
    "facebook": MarketingSource.FACEBOOK,
    "fb": MarketingSource.FACEBOOK,
    "meta": MarketingSource.FACEBOOK,
    "whatsapp": MarketingSource.WHATSAPP,
    "wa": MarketingSource.WHATSAPP,
    "google": MarketingSource.GOOGLE,
    "gmb": MarketingSource.GOOGLE,
    "google_search": MarketingSource.GOOGLE,
    "tiktok": MarketingSource.TIKTOK,
    "tt": MarketingSource.TIKTOK,
    "linkedin": MarketingSource.LINKEDIN,
    "youtube": MarketingSource.YOUTUBE,
    "yt": MarketingSource.YOUTUBE,
    "twitter": MarketingSource.TWITTER,
    "x": MarketingSource.TWITTER,
    "pinterest": MarketingSource.PINTEREST,
    "pin": MarketingSource.PINTEREST,
    "email": MarketingSource.EMAIL,
    "newsletter": MarketingSource.EMAIL,
    "referral": MarketingSource.REFERRAL,
    "friend": MarketingSource.REFERRAL,
    "word_of_mouth": MarketingSource.REFERRAL,
    "walk_in": MarketingSource.WALK_IN,
    "walkin": MarketingSource.WALK_IN,
}

_REFERRER_HOST_SOURCES: dict[str, MarketingSource] = {
    "instagram.com": MarketingSource.INSTAGRAM,
    "l.instagram.com": MarketingSource.INSTAGRAM,
    "facebook.com": MarketingSource.FACEBOOK,
    "m.facebook.com": MarketingSource.FACEBOOK,
    "l.facebook.com": MarketingSource.FACEBOOK,
    "fb.com": MarketingSource.FACEBOOK,
    "web.facebook.com": MarketingSource.FACEBOOK,
    "tiktok.com": MarketingSource.TIKTOK,
    "www.tiktok.com": MarketingSource.TIKTOK,
    "linkedin.com": MarketingSource.LINKEDIN,
    "www.linkedin.com": MarketingSource.LINKEDIN,
    "lnkd.in": MarketingSource.LINKEDIN,
    "google.com": MarketingSource.GOOGLE,
    "www.google.com": MarketingSource.GOOGLE,
    "google.lk": MarketingSource.GOOGLE,
    "www.google.lk": MarketingSource.GOOGLE,
    "youtube.com": MarketingSource.YOUTUBE,
    "www.youtube.com": MarketingSource.YOUTUBE,
    "m.youtube.com": MarketingSource.YOUTUBE,
    "youtu.be": MarketingSource.YOUTUBE,
    "twitter.com": MarketingSource.TWITTER,
    "www.twitter.com": MarketingSource.TWITTER,
    "x.com": MarketingSource.TWITTER,
    "www.x.com": MarketingSource.TWITTER,
    "t.co": MarketingSource.TWITTER,
    "pinterest.com": MarketingSource.PINTEREST,
    "www.pinterest.com": MarketingSource.PINTEREST,
    "pin.it": MarketingSource.PINTEREST,
    "api.whatsapp.com": MarketingSource.WHATSAPP,
    "wa.me": MarketingSource.WHATSAPP,
    "chat.whatsapp.com": MarketingSource.WHATSAPP,
}


@dataclass(frozen=True, slots=True)
class ResolvedMarketingAttribution:
    """Normalized marketing source plus persisted attribution metadata."""

    source: MarketingSource | None
    payload: dict[str, Any]
    resolution: str | None


def _normalize_token(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized or None


def _extract_referrer_host(referrer: str | None) -> str | None:
    if not referrer:
        return None
    try:
        host = urlparse(referrer).hostname
    except ValueError:
        return None
    if not host:
        return None
    return host.lower().removeprefix("www.")


def _resolve_from_utm_source(utm_source: str | None) -> MarketingSource | None:
    token = _normalize_token(utm_source)
    if not token:
        return None
    if token in _UTM_SOURCE_ALIASES:
        return _UTM_SOURCE_ALIASES[token]
    return MarketingSource.OTHER


def _resolve_from_referrer(referrer: str | None) -> MarketingSource | None:
    host = _extract_referrer_host(referrer)
    if not host:
        return None
    if host in _REFERRER_HOST_SOURCES:
        return _REFERRER_HOST_SOURCES[host]
    for known_host, source in _REFERRER_HOST_SOURCES.items():
        if host == known_host or host.endswith(f".{known_host}"):
            return source
    return None


def resolve_marketing_attribution(
    attribution: MarketingAttributionInput,
) -> ResolvedMarketingAttribution:
    """Resolve first-touch attribution with UTM priority over referrer."""
    referrer_host = _extract_referrer_host(attribution.referrer)
    captured_at = attribution.captured_at or datetime.now(UTC)

    source: MarketingSource | None = None
    resolution: str | None = None

    if attribution.utm_source:
        source = _resolve_from_utm_source(attribution.utm_source)
        resolution = "utm_source"
    elif attribution.referrer:
        source = _resolve_from_referrer(attribution.referrer)
        if source is not None:
            resolution = "referrer"

    payload = {
        "utm_source": attribution.utm_source,
        "utm_medium": attribution.utm_medium,
        "utm_campaign": attribution.utm_campaign,
        "utm_content": attribution.utm_content,
        "utm_term": attribution.utm_term,
        "referrer": attribution.referrer,
        "referrer_host": referrer_host,
        "landing_path": attribution.landing_path,
        "captured_at": captured_at.isoformat(),
        "resolution": resolution,
        "resolved_source": source.value if source else None,
    }
    return ResolvedMarketingAttribution(source=source, payload=payload, resolution=resolution)
