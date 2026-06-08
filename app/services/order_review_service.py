"""Order-level customer reviews with per-item sentiment."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import OrderStatus, ReviewItemSentiment
from app.core.exceptions import NotFoundError, ValidationError
from app.core.review_tags import (
    item_tags_for_sentiment,
    label_for_item_tag,
    label_for_order_tag,
    order_tags_for_rating,
    tag_catalog,
)
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_collection_line import OrderCollectionLine
from app.models.order_review import OrderReview
from app.models.order_review_item import OrderReviewItem
from app.repositories.order_repository import OrderRepository
from app.repositories.order_review_repository import OrderReviewRepository
from app.schemas.order_review import (
    OrderReviewAnalyticsSummary,
    OrderReviewAdminResponse,
    OrderReviewCreate,
    OrderReviewItemInput,
    OrderReviewItemResponse,
    OrderReviewResponse,
    OrderReviewSummaryEmbed,
    OrderReviewUpdate,
    ReviewTagCatalogResponse,
    ReviewableOrderSummary,
)
from app.schemas.pagination import PaginatedResponse


class OrderReviewService:
    """Customer and admin order review operations."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.reviews = OrderReviewRepository(db)
        self.orders = OrderRepository(db)

    def get_tag_catalog(self) -> ReviewTagCatalogResponse:
        return ReviewTagCatalogResponse(**tag_catalog())

    def list_reviews(self, customer: Customer) -> list[OrderReviewResponse]:
        rows = self.reviews.list_for_customer(customer.id)
        return [self._to_response(row) for row in rows]

    def get_review(self, customer: Customer, review_id: uuid.UUID) -> OrderReviewResponse:
        review = self._get_owned_review(customer, review_id)
        return self._to_response(review)

    def list_reviews_admin(
        self,
        *,
        page: int,
        page_size: int,
        customer_id: uuid.UUID | None = None,
        order_id: uuid.UUID | None = None,
    ) -> PaginatedResponse[OrderReviewAdminResponse]:
        rows, total = self.reviews.list_paginated(
            page=page,
            page_size=page_size,
            customer_id=customer_id,
            order_id=order_id,
        )
        return PaginatedResponse(
            items=[self._to_admin_response(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=self.reviews.total_pages(total, page_size),
        )

    def get_review_admin(self, review_id: uuid.UUID) -> OrderReviewAdminResponse:
        review = self.reviews.get_by_id(review_id)
        if not review:
            raise NotFoundError("Review not found")
        return self._to_admin_response(review)

    def get_review_for_order_admin(self, order_id: uuid.UUID) -> OrderReviewAdminResponse:
        review = self.reviews.get_by_order_id(order_id)
        if not review:
            raise NotFoundError("Review not found for this order")
        return self._to_admin_response(review)

    def get_order_review_summary(self, order_id: uuid.UUID) -> OrderReviewSummaryEmbed | None:
        review = self.reviews.get_by_order_id(order_id)
        if not review:
            return None
        return OrderReviewSummaryEmbed(id=review.id, rating=review.rating)

    def get_analytics_summary(self) -> OrderReviewAnalyticsSummary:
        data = self.reviews.analytics_summary()
        return OrderReviewAnalyticsSummary(
            total_reviews=int(data["total_reviews"]),
            average_rating=data["average_rating"],
            positive_item_feedback=int(data["positive_item_feedback"]),
            negative_item_feedback=int(data["negative_item_feedback"]),
            most_liked_product=data["most_liked_product"],
        )

    def list_reviewable_orders(self, customer: Customer) -> list[ReviewableOrderSummary]:
        delivered_orders = self._delivered_orders(customer.id)
        reviewed_order_ids = {
            review.order_id for review in self.reviews.list_for_customer(customer.id)
        }
        items: list[ReviewableOrderSummary] = []
        for order in delivered_orders:
            product_count = self._order_product_count(order)
            items.append(
                ReviewableOrderSummary(
                    order_id=order.id,
                    order_number=order.order_number,
                    scheduled_delivery_date=order.scheduled_delivery_date,
                    item_count=product_count,
                    already_reviewed=order.id in reviewed_order_ids,
                ),
            )
        return items

    def create_review(
        self,
        customer: Customer,
        payload: OrderReviewCreate,
    ) -> OrderReviewResponse:
        order = self._get_reviewable_order(customer.id, payload.order_id)
        if self.reviews.get_for_customer_order(customer_id=customer.id, order_id=payload.order_id):
            raise ValidationError("You have already reviewed this order.")

        order_products = self._order_products(order)
        self._validate_items(payload.items, order_products)
        self._validate_order_tags(payload.rating, payload.order_tags)

        review = OrderReview(
            customer_id=customer.id,
            order_id=payload.order_id,
            rating=payload.rating,
            order_tags=payload.order_tags,
            comment=payload.comment,
            items=self._build_item_rows(payload.items, order_products),
        )
        self.reviews.create(review)
        self.db.commit()
        loaded = self.reviews.get_by_id(review.id)
        assert loaded is not None
        return self._to_response(loaded)

    def update_review(
        self,
        customer: Customer,
        review_id: uuid.UUID,
        payload: OrderReviewUpdate,
    ) -> OrderReviewResponse:
        review = self._get_owned_review(customer, review_id)
        order = self.orders.get_by_id(review.order_id)
        assert order is not None
        order_products = self._order_products(order)

        rating = payload.rating if payload.rating is not None else review.rating
        if payload.order_tags is not None:
            self._validate_order_tags(rating, payload.order_tags)
            review.order_tags = payload.order_tags
        elif payload.rating is not None:
            self._validate_order_tags(rating, review.order_tags)

        if payload.rating is not None:
            review.rating = payload.rating
        if payload.comment is not None:
            review.comment = payload.comment.strip() or None
        if payload.items is not None:
            self._validate_items(payload.items, order_products)
            review.items.clear()
            self.db.flush()
            review.items = self._build_item_rows(payload.items, order_products)

        self.db.commit()
        self.db.refresh(review)
        return self._to_response(review)

    def delete_review(self, customer: Customer, review_id: uuid.UUID) -> None:
        review = self._get_owned_review(customer, review_id)
        self.reviews.delete(review)
        self.db.commit()

    def _get_reviewable_order(self, customer_id: uuid.UUID, order_id: uuid.UUID) -> Order:
        order = self.orders.get_by_id(order_id)
        if not order or order.customer_id != customer_id:
            raise NotFoundError("Order not found")
        if order.status != OrderStatus.DELIVERED:
            raise ValidationError("Reviews are only allowed for delivered orders.")
        return order

    def _delivered_orders(self, customer_id: uuid.UUID) -> list[Order]:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.product_lines),
                selectinload(Order.collection_lines).selectinload(
                    OrderCollectionLine.selections,
                ),
            )
            .where(
                Order.customer_id == customer_id,
                Order.status == OrderStatus.DELIVERED,
            )
            .order_by(Order.created_at.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def _order_products(self, order: Order) -> dict[uuid.UUID, dict]:
        products: dict[uuid.UUID, dict] = {}
        for line in order.product_lines:
            products[line.product_id] = {
                "product_name": line.product_name_snapshot,
                "quantity": line.quantity,
            }
        for collection_line in order.collection_lines:
            for selection in collection_line.selections:
                existing = products.get(selection.product_id)
                qty = selection.quantity
                if existing:
                    qty = existing["quantity"] + selection.quantity
                products[selection.product_id] = {
                    "product_name": selection.product_name_snapshot,
                    "quantity": qty,
                }
        return products

    def _order_product_count(self, order: Order) -> int:
        return len(self._order_products(order))

    def _validate_items(
        self,
        items: list[OrderReviewItemInput],
        order_products: dict[uuid.UUID, dict],
    ) -> None:
        if len(items) != len(order_products):
            raise ValidationError("Please provide feedback for every item in the order.")
        seen: set[uuid.UUID] = set()
        for item in items:
            if item.product_id not in order_products:
                raise ValidationError("One or more items are not part of this order.")
            if item.product_id in seen:
                raise ValidationError("Duplicate item feedback is not allowed.")
            seen.add(item.product_id)
            allowed = item_tags_for_sentiment(item.sentiment.value)
            for tag in item.tags:
                if tag not in allowed:
                    raise ValidationError(f"Invalid tag '{tag}' for this item feedback.")

    def _validate_order_tags(self, rating: int, tags: list[str]) -> None:
        allowed = order_tags_for_rating(rating)
        for tag in tags:
            if tag not in allowed:
                raise ValidationError(f"Invalid tag '{tag}' for this order rating.")

    def _build_item_rows(
        self,
        items: list[OrderReviewItemInput],
        order_products: dict[uuid.UUID, dict],
    ) -> list[OrderReviewItem]:
        rows: list[OrderReviewItem] = []
        for item in items:
            meta = order_products[item.product_id]
            rows.append(
                OrderReviewItem(
                    product_id=item.product_id,
                    product_name_snapshot=meta["product_name"],
                    quantity=meta["quantity"],
                    sentiment=item.sentiment,
                    item_tags=item.tags,
                ),
            )
        return rows

    def _get_owned_review(self, customer: Customer, review_id: uuid.UUID) -> OrderReview:
        review = self.reviews.get_by_id(review_id)
        if not review or review.customer_id != customer.id:
            raise NotFoundError("Review not found")
        return review

    def _to_item_response(self, item: OrderReviewItem) -> OrderReviewItemResponse:
        return OrderReviewItemResponse(
            product_id=item.product_id,
            product_name=item.product_name_snapshot,
            quantity=item.quantity,
            sentiment=item.sentiment,
            tags=item.item_tags,
            tag_labels=[label_for_item_tag(tag) for tag in item.item_tags],
        )

    def _to_response(self, review: OrderReview) -> OrderReviewResponse:
        return OrderReviewResponse(
            id=review.id,
            order_id=review.order_id,
            order_number=review.order.order_number,
            rating=review.rating,
            order_tags=review.order_tags,
            order_tag_labels=[label_for_order_tag(tag) for tag in review.order_tags],
            comment=review.comment,
            items=[self._to_item_response(item) for item in review.items],
            created_at=review.created_at,
            updated_at=review.updated_at,
        )

    def _to_admin_response(self, review: OrderReview) -> OrderReviewAdminResponse:
        base = self._to_response(review)
        return OrderReviewAdminResponse(
            **base.model_dump(),
            customer_id=review.customer_id,
            customer_name=f"{review.customer.first_name} {review.customer.last_name}".strip(),
        )
