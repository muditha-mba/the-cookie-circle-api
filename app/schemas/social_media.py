"""Social media settings schemas."""

from pydantic import BaseModel, Field, field_validator

from app.core.social_platforms import SOCIAL_PLATFORMS, SocialPlatform


class SocialMediaLink(BaseModel):
    """Single social platform link with activation flag."""

    platform: SocialPlatform
    url: str = Field(default="", max_length=500)
    is_enabled: bool = False

    @field_validator("url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        return value.strip()


class SocialMediaSettingsResponse(BaseModel):
    """All configured social media links."""

    links: list[SocialMediaLink]


class SocialMediaLinkUpdate(BaseModel):
    """Update payload for one social platform."""

    platform: SocialPlatform
    url: str | None = Field(default=None, max_length=500)
    is_enabled: bool | None = None

    @field_validator("url")
    @classmethod
    def strip_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class SocialMediaSettingsUpdate(BaseModel):
    """Batch update for social media links."""

    links: list[SocialMediaLinkUpdate] = Field(min_length=1)

    @field_validator("links")
    @classmethod
    def validate_platforms(cls, links: list[SocialMediaLinkUpdate]) -> list[SocialMediaLinkUpdate]:
        seen: set[SocialPlatform] = set()
        for link in links:
            if link.platform in seen:
                raise ValueError(f"Duplicate platform: {link.platform}")
            seen.add(link.platform)
        return links


def default_social_media_links() -> list[SocialMediaLink]:
    """Return empty defaults for every supported platform."""
    return [SocialMediaLink(platform=platform, url="", is_enabled=False) for platform in SOCIAL_PLATFORMS]
