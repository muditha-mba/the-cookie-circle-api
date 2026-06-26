"""Discount rule routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_discount_rule_service
from app.dependencies.permissions import require_super_admin
from app.schemas.discount import DiscountRuleCreate, DiscountRuleResponse, DiscountRuleUpdate
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.discount_rule_service import DiscountRuleService

router = APIRouter(
    prefix="/discount-rules",
    tags=["Discount Rules"],
    dependencies=[Depends(require_super_admin)],
)


@router.get("", response_model=PaginatedResponse[DiscountRuleResponse])
def list_discount_rules(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[DiscountRuleService, Depends(get_discount_rule_service)],
) -> PaginatedResponse[DiscountRuleResponse]:
    return service.list(params)


@router.post("", response_model=DiscountRuleResponse, status_code=status.HTTP_201_CREATED)
def create_discount_rule(
    payload: DiscountRuleCreate,
    service: Annotated[DiscountRuleService, Depends(get_discount_rule_service)],
) -> DiscountRuleResponse:
    return service.create(payload)


@router.get("/{rule_id}", response_model=DiscountRuleResponse)
def get_discount_rule(
    rule_id: uuid.UUID,
    service: Annotated[DiscountRuleService, Depends(get_discount_rule_service)],
) -> DiscountRuleResponse:
    return service.get(rule_id)


@router.patch("/{rule_id}", response_model=DiscountRuleResponse)
def update_discount_rule(
    rule_id: uuid.UUID,
    payload: DiscountRuleUpdate,
    service: Annotated[DiscountRuleService, Depends(get_discount_rule_service)],
) -> DiscountRuleResponse:
    return service.update(rule_id, payload)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discount_rule(
    rule_id: uuid.UUID,
    service: Annotated[DiscountRuleService, Depends(get_discount_rule_service)],
) -> None:
    service.delete(rule_id)
