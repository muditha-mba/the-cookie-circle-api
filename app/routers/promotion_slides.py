"""Promotion slide routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_promotion_slide_service
from app.dependencies.permissions import require_super_admin
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.promotion_slide import (
    PromotionSlideCreate,
    PromotionSlideResponse,
    PromotionSlideReorder,
    PromotionSlideUpdate,
)
from app.services.promotion_slide_service import PromotionSlideService

router = APIRouter(
    prefix="/promotion-slides",
    tags=["Promotion Slides"],
    dependencies=[Depends(require_super_admin)],
)


@router.get("", response_model=PaginatedResponse[PromotionSlideResponse])
def list_promotion_slides(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[PromotionSlideService, Depends(get_promotion_slide_service)],
) -> PaginatedResponse[PromotionSlideResponse]:
    return service.list(params)


@router.post("", response_model=PromotionSlideResponse, status_code=status.HTTP_201_CREATED)
def create_promotion_slide(
    payload: PromotionSlideCreate,
    service: Annotated[PromotionSlideService, Depends(get_promotion_slide_service)],
) -> PromotionSlideResponse:
    return service.create(payload)


@router.get("/{slide_id}", response_model=PromotionSlideResponse)
def get_promotion_slide(
    slide_id: uuid.UUID,
    service: Annotated[PromotionSlideService, Depends(get_promotion_slide_service)],
) -> PromotionSlideResponse:
    return service.get(slide_id)


@router.patch("/{slide_id}", response_model=PromotionSlideResponse)
def update_promotion_slide(
    slide_id: uuid.UUID,
    payload: PromotionSlideUpdate,
    service: Annotated[PromotionSlideService, Depends(get_promotion_slide_service)],
) -> PromotionSlideResponse:
    return service.update(slide_id, payload)


@router.delete("/{slide_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_promotion_slide(
    slide_id: uuid.UUID,
    service: Annotated[PromotionSlideService, Depends(get_promotion_slide_service)],
) -> None:
    service.delete(slide_id)


@router.post("/reorder", response_model=list[PromotionSlideResponse])
def reorder_promotion_slides(
    payload: PromotionSlideReorder,
    service: Annotated[PromotionSlideService, Depends(get_promotion_slide_service)],
) -> list[PromotionSlideResponse]:
    return service.reorder(payload)
