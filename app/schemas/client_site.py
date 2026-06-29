"""Public client site content schemas."""

from pydantic import BaseModel, Field

from app.core.social_platforms import SocialPlatform


class ClientSocialLink(BaseModel):
    """Active social link exposed to the client footer."""

    platform: SocialPlatform
    label: str
    url: str


class ClientSiteProfileResponse(BaseModel):
    """Public contact and social profile for the client website."""

    business_phone: str = ""
    business_email: str = ""
    social_links: list[ClientSocialLink] = Field(default_factory=list)
