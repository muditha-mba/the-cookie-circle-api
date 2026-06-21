"""Shared memory Pydantic schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.social_platforms import SOCIAL_PLATFORM_LABELS, SocialPlatform


def _validate_http_url(value: str, field_label: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_label} cannot be empty")
    if not (stripped.startswith("http://") or stripped.startswith("https://")):
        raise ValueError(f"{field_label} must start with http:// or https://")
    return stripped


class SharedMemoryCreate(BaseModel):
    """Create shared memory."""

    title: str = Field(default="", max_length=200)
    preview_image_url: str = Field(min_length=1, max_length=2000)
    post_url: str = Field(min_length=1, max_length=500)
    platform: SocialPlatform
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()

    @field_validator("preview_image_url")
    @classmethod
    def validate_preview_image_url(cls, value: str) -> str:
        return _validate_http_url(value, "Preview image URL")

    @field_validator("post_url")
    @classmethod
    def validate_post_url(cls, value: str) -> str:
        return _validate_http_url(value, "Post URL")


class SharedMemoryUpdate(BaseModel):
    """Update shared memory."""

    title: str | None = Field(default=None, max_length=200)
    preview_image_url: str | None = Field(default=None, min_length=1, max_length=2000)
    post_url: str | None = Field(default=None, min_length=1, max_length=500)
    platform: SocialPlatform | None = None
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("preview_image_url")
    @classmethod
    def validate_preview_image_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_http_url(value, "Preview image URL")

    @field_validator("post_url")
    @classmethod
    def validate_post_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_http_url(value, "Post URL")


class SharedMemoryResponse(BaseModel):
    """Shared memory response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    preview_image_url: str
    post_url: str
    platform: SocialPlatform
    platform_label: str
    sort_order: int
    is_active: bool


class ClientSharedMemoryItem(BaseModel):
    """Public shared memory entry."""

    id: uuid.UUID
    title: str
    preview_image_url: str
    post_url: str
    platform: SocialPlatform
    platform_label: str
    sort_order: int


class ClientSharedMemoriesResponse(BaseModel):
    """Public shared memories payload for the client website."""

    section_enabled: bool
    posts: list[ClientSharedMemoryItem]


class SharedMemoriesSectionSettingsResponse(BaseModel):
    """Admin settings for the shared memories section visibility."""

    section_enabled: bool


class SharedMemoriesSectionSettingsUpdate(BaseModel):
    """Update shared memories section visibility."""

    section_enabled: bool


def platform_label(platform: SocialPlatform) -> str:
    return SOCIAL_PLATFORM_LABELS[platform]
