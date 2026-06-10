"""FAQ category Pydantic schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FaqCategoryCreate(BaseModel):
    """Create FAQ category."""

    name: str = Field(min_length=1, max_length=120)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name cannot be empty")
        return stripped


class FaqCategoryUpdate(BaseModel):
    """Update FAQ category."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name cannot be empty")
        return stripped


class FaqCategoryResponse(BaseModel):
    """FAQ category response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    sort_order: int
    is_active: bool
    faq_count: int = 0


class FaqCategorySummary(BaseModel):
    """Nested category summary on FAQ responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
