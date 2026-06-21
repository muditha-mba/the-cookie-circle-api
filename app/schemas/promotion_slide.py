"""Promotion slide Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PromotionSlideCreate(BaseModel):
    """Create a new promotion slide."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    image_url: str = Field(min_length=1, max_length=2000)
    cta_text: str | None = Field(default=None, max_length=100)
    cta_destination: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(default=0, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool = True

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str) -> str:
        value = value.strip()
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("image_url must start with http:// or https://")
        return value


class PromotionSlideUpdate(BaseModel):
    """Update a promotion slide."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, min_length=1, max_length=2000)
    cta_text: str | None = Field(default=None, max_length=100)
    cta_destination: str | None = Field(default=None, max_length=500)
    sort_order: int | None = Field(default=None, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("image_url must start with http:// or https://")
        return value


class PromotionSlideResponse(BaseModel):
    """Promotion slide response."""

    id: UUID
    title: str
    description: str | None
    image_url: str
    cta_text: str | None
    cta_destination: str | None
    sort_order: int
    starts_at: datetime | None
    ends_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromotionSlideReorder(BaseModel):
    """Update the sort order of multiple slides at once."""

    slide_ids: list[UUID] = Field(min_length=1, description="Ordered list of slide IDs")
