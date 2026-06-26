"""Utility charge routes — charge definition and monthly bill entries."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_utility_charge_service
from app.dependencies.permissions import require_super_admin
from app.schemas.charge import (
    BillEntryCreate,
    BillEntryResponse,
    BillEntryUpdate,
    UtilityChargeCreate,
    UtilityChargeDetailResponse,
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
    """List utility charge types with pagination."""
    return service.list(params)


@router.post("", response_model=UtilityChargeDetailResponse, status_code=status.HTTP_201_CREATED)
def create_utility_charge(
    payload: UtilityChargeCreate,
    service: Annotated[UtilityChargeService, Depends(get_utility_charge_service)],
) -> UtilityChargeDetailResponse:
    """Create a utility charge type (e.g. Electricity, Water)."""
    return service.create(payload)


@router.get("/{charge_id}", response_model=UtilityChargeDetailResponse)
def get_utility_charge(
    charge_id: uuid.UUID,
    service: Annotated[UtilityChargeService, Depends(get_utility_charge_service)],
) -> UtilityChargeDetailResponse:
    """Get a utility charge type with all its monthly bill entries."""
    return service.get(charge_id)


@router.patch("/{charge_id}", response_model=UtilityChargeDetailResponse)
def update_utility_charge(
    charge_id: uuid.UUID,
    payload: UtilityChargeUpdate,
    service: Annotated[UtilityChargeService, Depends(get_utility_charge_service)],
) -> UtilityChargeDetailResponse:
    """Update a utility charge type."""
    return service.update(charge_id, payload)


@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_utility_charge(
    charge_id: uuid.UUID,
    service: Annotated[UtilityChargeService, Depends(get_utility_charge_service)],
) -> None:
    """Delete a utility charge type (only if no bill entries exist)."""
    service.delete(charge_id)


# ── Bill Entries ──────────────────────────────────────────────────────────────

@router.post(
    "/{charge_id}/bills",
    response_model=BillEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_utility_bill_entry(
    charge_id: uuid.UUID,
    payload: BillEntryCreate,
    service: Annotated[UtilityChargeService, Depends(get_utility_charge_service)],
) -> BillEntryResponse:
    """Record a monthly bill for a utility type. Each month can only have one entry."""
    return service.add_bill_entry(charge_id, payload)


@router.patch(
    "/{charge_id}/bills/{entry_id}",
    response_model=BillEntryResponse,
)
def update_utility_bill_entry(
    charge_id: uuid.UUID,
    entry_id: uuid.UUID,
    payload: BillEntryUpdate,
    service: Annotated[UtilityChargeService, Depends(get_utility_charge_service)],
) -> BillEntryResponse:
    """Update an existing monthly bill entry."""
    return service.update_bill_entry(charge_id, entry_id, payload)


@router.delete(
    "/{charge_id}/bills/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_utility_bill_entry(
    charge_id: uuid.UUID,
    entry_id: uuid.UUID,
    service: Annotated[UtilityChargeService, Depends(get_utility_charge_service)],
) -> None:
    """Delete a monthly bill entry."""
    service.delete_bill_entry(charge_id, entry_id)
