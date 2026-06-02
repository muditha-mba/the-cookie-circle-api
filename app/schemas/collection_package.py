"""Collection package schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CollectionPackageBase(BaseModel):
    """Shared collection package fields."""

    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    badge_tone: str = Field(min_length=2, max_length=32)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name", "badge_tone")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class CollectionPackageCreate(CollectionPackageBase):
    """Create collection package request."""


class CollectionPackageUpdate(BaseModel):
    """Update collection package request."""

    code: str | None = Field(default=None, min_length=2, max_length=64)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    badge_tone: str | None = Field(default=None, min_length=2, max_length=32)
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("name", "badge_tone")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class CollectionPackageResponse(CollectionPackageBase):
    """Collection package response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
