"""FAQ Pydantic schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.faq_category import FaqCategorySummary


class FaqCreate(BaseModel):
    """Create FAQ."""

    category_id: uuid.UUID
    question: str = Field(min_length=1, max_length=300)
    answer: str = Field(min_length=1)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("question", "answer")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value cannot be empty")
        return stripped


class FaqUpdate(BaseModel):
    """Update FAQ."""

    category_id: uuid.UUID | None = None
    question: str | None = Field(default=None, min_length=1, max_length=300)
    answer: str | None = Field(default=None, min_length=1)
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("question", "answer")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value cannot be empty")
        return stripped


class FaqResponse(BaseModel):
    """FAQ response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    category: FaqCategorySummary
    question: str
    answer: str
    sort_order: int
    is_active: bool


class ClientFaqItem(BaseModel):
    """Public FAQ entry."""

    id: uuid.UUID
    question: str
    answer: str
    sort_order: int


class ClientFaqCategoryGroup(BaseModel):
    """Active FAQs grouped by category for the client website."""

    id: uuid.UUID
    name: str
    sort_order: int
    faqs: list[ClientFaqItem]


class ClientFaqsResponse(BaseModel):
    """Public FAQs payload for the client website."""

    section_enabled: bool
    categories: list[ClientFaqCategoryGroup]


class FaqsSectionSettingsResponse(BaseModel):
    """Admin settings for FAQ section visibility."""

    section_enabled: bool


class FaqsSectionSettingsUpdate(BaseModel):
    """Update FAQ section visibility."""

    section_enabled: bool
