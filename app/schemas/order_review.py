"""Order-level customer review schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.enums import ReviewItemSentiment
from app.core.review_tags import (
    item_tags_for_sentiment,
    label_for_item_tag,
    label_for_order_tag,
    order_tags_for_rating,
)


class ReviewTagCatalogResponse(BaseModel):
    positive_order: list[dict[str, str]]
    negative_order: list[dict[str, str]]
    positive_item: list[dict[str, str]]
    negative_item: list[dict[str, str]]


class ReviewableOrderSummary(BaseModel):
    order_id: UUID
    order_number: str
    scheduled_delivery_date: date
    item_count: int
    already_reviewed: bool


class OrderReviewItemInput(BaseModel):
    product_id: UUID
    sentiment: ReviewItemSentiment
    tags: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str], info) -> list[str]:
        sentiment = info.data.get("sentiment")
        if sentiment is None:
            return tags
        allowed = item_tags_for_sentiment(
            sentiment.value if hasattr(sentiment, "value") else str(sentiment),
        )
        cleaned = []
        for tag in tags:
            normalized = tag.strip().lower()
            if normalized and normalized in allowed:
                cleaned.append(normalized)
        return cleaned


class OrderReviewCreate(BaseModel):
    order_id: UUID
    rating: int = Field(ge=1, le=5)
    order_tags: list[str] = Field(default_factory=list, max_length=8)
    comment: str | None = Field(default=None, max_length=2000)
    items: list[OrderReviewItemInput] = Field(min_length=1)

    @field_validator("order_tags")
    @classmethod
    def normalize_order_tags(cls, tags: list[str], info) -> list[str]:
        rating = info.data.get("rating")
        if rating is None:
            return tags
        allowed = order_tags_for_rating(int(rating))
        cleaned = []
        for tag in tags:
            normalized = tag.strip().lower()
            if normalized and normalized in allowed:
                cleaned.append(normalized)
        return cleaned

    @field_validator("comment")
    @classmethod
    def strip_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class OrderReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    order_tags: list[str] | None = Field(default=None, max_length=8)
    comment: str | None = Field(default=None, max_length=2000)
    items: list[OrderReviewItemInput] | None = None


class OrderReviewItemResponse(BaseModel):
    product_id: UUID
    product_name: str
    quantity: Decimal
    sentiment: ReviewItemSentiment
    tags: list[str]
    tag_labels: list[str]


class OrderReviewResponse(BaseModel):
    id: UUID
    order_id: UUID
    order_number: str
    rating: int
    order_tags: list[str]
    order_tag_labels: list[str]
    comment: str | None
    items: list[OrderReviewItemResponse]
    created_at: datetime
    updated_at: datetime


class OrderReviewAdminResponse(OrderReviewResponse):
    customer_id: UUID
    customer_name: str


class OrderReviewAnalyticsSummary(BaseModel):
    total_reviews: int
    average_rating: float | None
    positive_item_feedback: int
    negative_item_feedback: int
    most_liked_product: str | None


class OrderReviewSummaryEmbed(BaseModel):
    """Lightweight review pointer on admin order detail."""

    id: UUID
    rating: int
