"""Admin order review routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies.admin import get_current_admin_user
from app.dependencies.client_account import get_order_review_service
from app.models.user import User
from app.schemas.order_review import OrderReviewAdminResponse, OrderReviewAnalyticsSummary
from app.schemas.pagination import PaginatedResponse
from app.services.order_review_service import OrderReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("", response_model=PaginatedResponse[OrderReviewAdminResponse])
def list_reviews(
    _: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[OrderReviewService, Depends(get_order_review_service)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    customer_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
) -> PaginatedResponse[OrderReviewAdminResponse]:
    return service.list_reviews_admin(
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        order_id=order_id,
    )


@router.get("/analytics/summary", response_model=OrderReviewAnalyticsSummary)
def review_analytics_summary(
    _: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[OrderReviewService, Depends(get_order_review_service)],
) -> OrderReviewAnalyticsSummary:
    return service.get_analytics_summary()


@router.get("/by-order/{order_id}", response_model=OrderReviewAdminResponse)
def get_review_for_order(
    order_id: uuid.UUID,
    _: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[OrderReviewService, Depends(get_order_review_service)],
) -> OrderReviewAdminResponse:
    return service.get_review_for_order_admin(order_id)


@router.get("/{review_id}", response_model=OrderReviewAdminResponse)
def get_review(
    review_id: uuid.UUID,
    _: Annotated[User, Depends(get_current_admin_user)],
    service: Annotated[OrderReviewService, Depends(get_order_review_service)],
) -> OrderReviewAdminResponse:
    return service.get_review_admin(review_id)
