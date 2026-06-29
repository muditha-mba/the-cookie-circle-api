"""Labour charge routes — charge definition and monthly bill entries."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_labour_charge_service
from app.dependencies.permissions import require_super_admin
from app.schemas.charge import (
    BillEntryCreate,
    BillEntryResponse,
    BillEntryUpdate,
    LabourChargeCreate,
    LabourChargeDetailResponse,
    LabourChargeResponse,
    LabourChargeUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.services.labour_charge_service import LabourChargeService

router = APIRouter(
    prefix="/labour-charges",
    tags=["Labour Charges"],
    dependencies=[Depends(require_super_admin)],
)


@router.get("", response_model=PaginatedResponse[LabourChargeResponse])
def list_labour_charges(
    params: Annotated[PaginationParams, Depends()],
    service: Annotated[LabourChargeService, Depends(get_labour_charge_service)],
) -> PaginatedResponse[LabourChargeResponse]:
    """List labour charge types with pagination."""
    return service.list(params)


@router.post("", response_model=LabourChargeDetailResponse, status_code=status.HTTP_201_CREATED)
def create_labour_charge(
    payload: LabourChargeCreate,
    service: Annotated[LabourChargeService, Depends(get_labour_charge_service)],
) -> LabourChargeDetailResponse:
    """Create a labour charge type (e.g. Preparation, Packaging)."""
    return service.create(payload)


@router.get("/{charge_id}", response_model=LabourChargeDetailResponse)
def get_labour_charge(
    charge_id: uuid.UUID,
    service: Annotated[LabourChargeService, Depends(get_labour_charge_service)],
) -> LabourChargeDetailResponse:
    """Get a labour charge type with all its monthly bill entries."""
    return service.get(charge_id)


@router.patch("/{charge_id}", response_model=LabourChargeDetailResponse)
def update_labour_charge(
    charge_id: uuid.UUID,
    payload: LabourChargeUpdate,
    service: Annotated[LabourChargeService, Depends(get_labour_charge_service)],
) -> LabourChargeDetailResponse:
    """Update a labour charge type."""
    return service.update(charge_id, payload)


@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_labour_charge(
    charge_id: uuid.UUID,
    service: Annotated[LabourChargeService, Depends(get_labour_charge_service)],
) -> None:
    """Delete a labour charge type."""
    service.delete(charge_id)


# ── Bill Entries ──────────────────────────────────────────────────────────────

@router.post(
    "/{charge_id}/bills",
    response_model=BillEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_labour_bill_entry(
    charge_id: uuid.UUID,
    payload: BillEntryCreate,
    service: Annotated[LabourChargeService, Depends(get_labour_charge_service)],
) -> BillEntryResponse:
    """Record a monthly labour cost for a category. Each month can only have one entry."""
    return service.add_bill_entry(charge_id, payload)


@router.patch(
    "/{charge_id}/bills/{entry_id}",
    response_model=BillEntryResponse,
)
def update_labour_bill_entry(
    charge_id: uuid.UUID,
    entry_id: uuid.UUID,
    payload: BillEntryUpdate,
    service: Annotated[LabourChargeService, Depends(get_labour_charge_service)],
) -> BillEntryResponse:
    """Update an existing monthly labour bill entry."""
    return service.update_bill_entry(charge_id, entry_id, payload)


@router.delete(
    "/{charge_id}/bills/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_labour_bill_entry(
    charge_id: uuid.UUID,
    entry_id: uuid.UUID,
    service: Annotated[LabourChargeService, Depends(get_labour_charge_service)],
) -> None:
    """Delete a monthly labour bill entry."""
    service.delete_bill_entry(charge_id, entry_id)
