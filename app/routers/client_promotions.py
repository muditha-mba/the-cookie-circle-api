"""Client-facing promotion slide endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.client_account import get_optional_current_customer_id
from app.models.customer_discount_grant import CustomerDiscountGrant
from app.models.customer_discount_override import CustomerDiscountOverride
from app.models.discount_rule import DiscountRule
from app.models.promotion_slide import PromotionSlide
from app.utils.decimal_format import format_decimal_for_display
from app.schemas.promotion_slide import PromotionSlideResponse
from app.services.business_setting_service import BusinessSettingService
from app.core.enums import DiscountGrantStatus

router = APIRouter(prefix="/client/promotions", tags=["Client Promotions"])


def _active_slides(db: Session) -> list[PromotionSlideResponse]:
    now = datetime.now(tz=timezone.utc)
    stmt = (
        select(PromotionSlide)
        .where(
            PromotionSlide.is_active == True,  # noqa: E712
            (PromotionSlide.starts_at.is_(None)) | (PromotionSlide.starts_at <= now),
            (PromotionSlide.ends_at.is_(None)) | (PromotionSlide.ends_at >= now),
        )
        .order_by(PromotionSlide.sort_order.asc())
    )
    return [PromotionSlideResponse.model_validate(s) for s in db.scalars(stmt).all()]


@router.get("/slides", response_model=list[PromotionSlideResponse])
def list_promotion_slides(
    db: Annotated[Session, Depends(get_db)],
) -> list[PromotionSlideResponse]:
    """Return active, scheduled promotion slides (no auth required)."""
    return _active_slides(db)


@router.get("/slides/for-me", response_model=list[dict])
def list_promotion_slides_for_me(
    db: Annotated[Session, Depends(get_db)],
    customer_id: Annotated[uuid.UUID | None, Depends(get_optional_current_customer_id)] = None,
) -> list[dict]:
    """
    Return active slides + an injected discount slide if the authenticated customer
    has an active, non-expired grant and discounts are enabled.
    """
    slides: list[dict] = [s.model_dump() for s in _active_slides(db)]

    if customer_id is None:
        return slides

    settings = BusinessSettingService(db).get_settings()
    if not settings.discounts_enabled:
        return slides

    override = db.scalar(
        select(CustomerDiscountOverride).where(
            CustomerDiscountOverride.customer_id == customer_id
        )
    )
    if override is not None and not override.discounts_enabled:
        return slides

    now = datetime.now(tz=timezone.utc)
    grant = db.scalar(
        select(CustomerDiscountGrant).where(
            CustomerDiscountGrant.customer_id == customer_id,
            CustomerDiscountGrant.status == DiscountGrantStatus.ACTIVE,
            (CustomerDiscountGrant.expires_at.is_(None))
            | (CustomerDiscountGrant.expires_at > now),
        )
    )
    if grant is None:
        return slides

    image_url = _discount_slide_image_url(db, grant)

    discount_slide = {
        "slide_type": "discount",
        "discount_type": grant.discount_type.value,
        "discount_value": format_decimal_for_display(grant.discount_value),
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
        "title": _discount_slide_title(grant),
        "image_url": image_url,
        "cta_label": "Order Now",
        "cta_url": None,
        "sort_order": -1,
    }
    return [discount_slide] + slides


def _discount_slide_image_url(db: Session, grant: CustomerDiscountGrant) -> str | None:
    if grant.discount_rule_id is None:
        return None

    rule = db.get(DiscountRule, grant.discount_rule_id)
    if rule is None:
        return None

    raw = rule.config.get("image_url")
    if not isinstance(raw, str):
        return None

    value = raw.strip()
    return value or None


def _discount_slide_title(grant: CustomerDiscountGrant) -> str:
    from app.core.enums import DiscountType

    if grant.discount_type == DiscountType.PERCENTAGE:
        val = format_decimal_for_display(grant.discount_value)
        return f"You have a {val}% discount on your next order!"

    val = format_decimal_for_display(grant.discount_value)
    return f"You have LKR {val} off your next order!"
