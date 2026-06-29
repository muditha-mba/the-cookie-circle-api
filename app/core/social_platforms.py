"""Supported social media platforms for public footer links."""

from typing import Literal

SocialPlatform = Literal["instagram", "facebook", "tiktok", "youtube"]

SOCIAL_PLATFORMS: tuple[SocialPlatform, ...] = (
    "instagram",
    "facebook",
    "tiktok",
    "youtube",
)

SOCIAL_PLATFORM_LABELS: dict[SocialPlatform, str] = {
    "instagram": "Instagram",
    "facebook": "Facebook",
    "tiktok": "TikTok",
    "youtube": "YouTube",
}
