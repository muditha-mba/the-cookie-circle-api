"""Predefined review tags for order-level and item-level feedback."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewTagDefinition:
    id: str
    label: str


POSITIVE_ORDER_TAGS: tuple[ReviewTagDefinition, ...] = (
    ReviewTagDefinition("delivered_on_time", "Delivered on time"),
    ReviewTagDefinition("friendly_service", "Friendly service"),
    ReviewTagDefinition("good_packaging", "Good packaging"),
    ReviewTagDefinition("great_value", "Great value"),
    ReviewTagDefinition("easy_ordering", "Easy ordering"),
    ReviewTagDefinition("would_order_again", "Would order again"),
)

NEGATIVE_ORDER_TAGS: tuple[ReviewTagDefinition, ...] = (
    ReviewTagDefinition("late_delivery", "Late delivery"),
    ReviewTagDefinition("bad_packaging", "Bad packaging"),
    ReviewTagDefinition("unfriendly_service", "Unfriendly service"),
    ReviewTagDefinition("wrong_items", "Wrong items"),
    ReviewTagDefinition("poor_communication", "Poor communication"),
    ReviewTagDefinition("would_not_order_again", "Would not order again"),
)

POSITIVE_ITEM_TAGS: tuple[ReviewTagDefinition, ...] = (
    ReviewTagDefinition("tasty", "Tasty"),
    ReviewTagDefinition("fresh", "Fresh"),
    ReviewTagDefinition("perfect_texture", "Perfect texture"),
    ReviewTagDefinition("generous_portion", "Generous portion"),
    ReviewTagDefinition("beautifully_made", "Beautifully made"),
)

NEGATIVE_ITEM_TAGS: tuple[ReviewTagDefinition, ...] = (
    ReviewTagDefinition("soggy", "Soggy"),
    ReviewTagDefinition("stale", "Stale"),
    ReviewTagDefinition("too_sweet", "Too sweet"),
    ReviewTagDefinition("too_bland", "Too bland"),
    ReviewTagDefinition("damaged", "Damaged"),
)

POSITIVE_ORDER_TAG_IDS = frozenset(tag.id for tag in POSITIVE_ORDER_TAGS)
NEGATIVE_ORDER_TAG_IDS = frozenset(tag.id for tag in NEGATIVE_ORDER_TAGS)
POSITIVE_ITEM_TAG_IDS = frozenset(tag.id for tag in POSITIVE_ITEM_TAGS)
NEGATIVE_ITEM_TAG_IDS = frozenset(tag.id for tag in NEGATIVE_ITEM_TAGS)

_ORDER_LABELS = {tag.id: tag.label for tag in (*POSITIVE_ORDER_TAGS, *NEGATIVE_ORDER_TAGS)}
_ITEM_LABELS = {tag.id: tag.label for tag in (*POSITIVE_ITEM_TAGS, *NEGATIVE_ITEM_TAGS)}


def order_tags_for_rating(rating: int) -> frozenset[str]:
    if rating >= 4:
        return POSITIVE_ORDER_TAG_IDS
    return NEGATIVE_ORDER_TAG_IDS


def item_tags_for_sentiment(sentiment: str) -> frozenset[str]:
    if sentiment == "positive":
        return POSITIVE_ITEM_TAG_IDS
    return NEGATIVE_ITEM_TAG_IDS


def label_for_order_tag(tag_id: str) -> str:
    return _ORDER_LABELS.get(tag_id, tag_id.replace("_", " ").title())


def label_for_item_tag(tag_id: str) -> str:
    return _ITEM_LABELS.get(tag_id, tag_id.replace("_", " ").title())


def tag_catalog() -> dict[str, list[dict[str, str]]]:
    return {
        "positive_order": [{"id": t.id, "label": t.label} for t in POSITIVE_ORDER_TAGS],
        "negative_order": [{"id": t.id, "label": t.label} for t in NEGATIVE_ORDER_TAGS],
        "positive_item": [{"id": t.id, "label": t.label} for t in POSITIVE_ITEM_TAGS],
        "negative_item": [{"id": t.id, "label": t.label} for t in NEGATIVE_ITEM_TAGS],
    }
