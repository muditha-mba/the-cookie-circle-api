"""Order review persistence."""

import uuid
from math import ceil

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.order_review import OrderReview
from app.models.order_review_item import OrderReviewItem


class OrderReviewRepository:
    """Repository for order-level customer reviews."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, review_id: uuid.UUID) -> OrderReview | None:
        stmt = (
            select(OrderReview)
            .options(
                joinedload(OrderReview.customer),
                joinedload(OrderReview.order),
                selectinload(OrderReview.items),
            )
            .where(OrderReview.id == review_id)
        )
        return self.db.scalar(stmt)

    def get_for_customer_order(
        self,
        *,
        customer_id: uuid.UUID,
        order_id: uuid.UUID,
    ) -> OrderReview | None:
        stmt = (
            select(OrderReview)
            .options(selectinload(OrderReview.items))
            .where(
                OrderReview.customer_id == customer_id,
                OrderReview.order_id == order_id,
            )
        )
        return self.db.scalar(stmt)

    def get_by_order_id(self, order_id: uuid.UUID) -> OrderReview | None:
        stmt = (
            select(OrderReview)
            .options(
                joinedload(OrderReview.customer),
                joinedload(OrderReview.order),
                selectinload(OrderReview.items),
            )
            .where(OrderReview.order_id == order_id)
        )
        return self.db.scalar(stmt)

    def list_for_customer(self, customer_id: uuid.UUID) -> list[OrderReview]:
        stmt = (
            select(OrderReview)
            .options(joinedload(OrderReview.order), selectinload(OrderReview.items))
            .where(OrderReview.customer_id == customer_id)
            .order_by(OrderReview.created_at.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        customer_id: uuid.UUID | None = None,
        order_id: uuid.UUID | None = None,
    ) -> tuple[list[OrderReview], int]:
        stmt = select(OrderReview).options(
            joinedload(OrderReview.customer),
            joinedload(OrderReview.order),
            selectinload(OrderReview.items),
        )
        count_stmt = select(func.count()).select_from(OrderReview)

        if customer_id:
            stmt = stmt.where(OrderReview.customer_id == customer_id)
            count_stmt = count_stmt.where(OrderReview.customer_id == customer_id)
        if order_id:
            stmt = stmt.where(OrderReview.order_id == order_id)
            count_stmt = count_stmt.where(OrderReview.order_id == order_id)

        total = int(self.db.scalar(count_stmt) or 0)
        stmt = (
            stmt.order_by(desc(OrderReview.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(stmt).unique().all()), total

    def create(self, review: OrderReview) -> OrderReview:
        self.db.add(review)
        self.db.flush()
        return review

    def delete(self, review: OrderReview) -> None:
        self.db.delete(review)

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        if total == 0:
            return 0
        return ceil(total / page_size)

    def analytics_summary(self) -> dict[str, object]:
        total_reviews = int(self.db.scalar(select(func.count()).select_from(OrderReview)) or 0)
        avg_rating = self.db.scalar(select(func.avg(OrderReview.rating)))

        thumbs_up = int(
            self.db.scalar(
                select(func.count())
                .select_from(OrderReviewItem)
                .where(OrderReviewItem.sentiment == "positive"),
            )
            or 0,
        )
        thumbs_down = int(
            self.db.scalar(
                select(func.count())
                .select_from(OrderReviewItem)
                .where(OrderReviewItem.sentiment == "negative"),
            )
            or 0,
        )

        top_positive_item = self.db.execute(
            select(
                OrderReviewItem.product_name_snapshot,
                func.count(OrderReviewItem.id).label("count"),
            )
            .where(OrderReviewItem.sentiment == "positive")
            .group_by(OrderReviewItem.product_name_snapshot)
            .order_by(desc("count"))
            .limit(1),
        ).first()

        return {
            "total_reviews": total_reviews,
            "average_rating": float(avg_rating) if avg_rating is not None else None,
            "positive_item_feedback": thumbs_up,
            "negative_item_feedback": thumbs_down,
            "most_liked_product": top_positive_item[0] if top_positive_item else None,
        }
