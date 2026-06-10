"""Utility charge routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_utility_charge_service
from app.dependencies.permissions import require_super_admin
from app.schemas.charge import (
    UtilityChargeCreate,
    UtilityChargeResponse,
    UtilityChargeUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.utility_charge_service import UtilityChargeService

router = APIRouter(
    prefix="/utility-charges",
    tags=["Utility Charges"],
    dependencies=[Depends(require_super_admin)],
)


@router.get("", response_model=PaginatedResponse[UtilityChargeResponse])
def list_utility_charges(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[UtilityChargeService, Depends(get_utility_charge_service)],
) -> PaginatedResponse[UtilityChargeResponse]:
    """List utility charges with pagination."""
    return service.list(params)


@router.post("", response_model=UtilityChargeResponse, status_code=status.HTTP_201_CREATED)
def create_utility_charge(
    payload: UtilityChargeCreate,
    service: Annotated[UtilityChargeService, Depends(get_utility_charge_service)],
) -> UtilityChargeResponse:
    """Create a utility charge."""
    return service.create(payload)


@router.get("/{charge_id}", response_model=UtilityChargeResponse)
def get_utility_charge(
    charge_id: uuid.UUID,
    service: Annotated[UtilityChargeService, Depends(get_utility_charge_service)],
) -> UtilityChargeResponse:
    """Get a utility charge by ID."""
    return service.get(charge_id)


@router.patch("/{charge_id}", response_model=UtilityChargeResponse)
def update_utility_charge(
    charge_id: uuid.UUID,
    payload: UtilityChargeUpdate,
    service: Annotated[UtilityChargeService, Depends(get_utility_charge_service)],
) -> UtilityChargeResponse:
    """Update a utility charge."""
    return service.update(charge_id, payload)


@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_utility_charge(
    charge_id: uuid.UUID,
    service: Annotated[UtilityChargeService, Depends(get_utility_charge_service)],
) -> None:
    """Delete a utility charge."""
    service.delete(charge_id)
