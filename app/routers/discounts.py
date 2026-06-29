"""Discount grant + audit routes — eligible customers, history, audit events."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.admin import (
    get_customer_discount_grant_service,
    get_discount_audit_service,
)
from app.dependencies.permissions import require_super_admin
from app.schemas.discount import (
    DiscountAuditEventResponse,
    DiscountHistoryItem,
    EligibleCustomerItem,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.customer_discount_grant_service import CustomerDiscountGrantService
from app.services.discount_audit_service import DiscountAuditService

router = APIRouter(
    prefix="/discounts",
    tags=["Discounts"],
    dependencies=[Depends(require_super_admin)],
)


@router.get("/eligible-customers", response_model=PaginatedResponse[EligibleCustomerItem])
def list_eligible_customers(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[CustomerDiscountGrantService, Depends(get_customer_discount_grant_service)],
) -> PaginatedResponse[EligibleCustomerItem]:
    return service.list_eligible(params)


@router.get("/history", response_model=PaginatedResponse[DiscountHistoryItem])
def list_discount_history(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[CustomerDiscountGrantService, Depends(get_customer_discount_grant_service)],
    customer_id: uuid.UUID | None = None,
) -> PaginatedResponse[DiscountHistoryItem]:
    return service.list_history(params, customer_id=customer_id)


@router.get("/audit-events", response_model=PaginatedResponse[DiscountAuditEventResponse])
def list_audit_events(
    params: Annotated[PaginationParams, Depends()],
    audit_service: Annotated[DiscountAuditService, Depends(get_discount_audit_service)],
    customer_id: uuid.UUID | None = None,
) -> PaginatedResponse[DiscountAuditEventResponse]:
    return audit_service.list(params, customer_id=customer_id)
