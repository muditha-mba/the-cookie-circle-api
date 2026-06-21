"""Labour charge routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_labour_charge_service
from app.dependencies.permissions import require_super_admin
from app.schemas.charge import (
    LabourChargeCreate,
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
    """List labour charges with pagination."""
    return service.list(params)


@router.post("", response_model=LabourChargeResponse, status_code=status.HTTP_201_CREATED)
def create_labour_charge(
    payload: LabourChargeCreate,
    service: Annotated[LabourChargeService, Depends(get_labour_charge_service)],
) -> LabourChargeResponse:
    """Create a labour charge."""
    return service.create(payload)


@router.get("/{charge_id}", response_model=LabourChargeResponse)
def get_labour_charge(
    charge_id: uuid.UUID,
    service: Annotated[LabourChargeService, Depends(get_labour_charge_service)],
) -> LabourChargeResponse:
    """Get a labour charge by ID."""
    return service.get(charge_id)


@router.patch("/{charge_id}", response_model=LabourChargeResponse)
def update_labour_charge(
    charge_id: uuid.UUID,
    payload: LabourChargeUpdate,
    service: Annotated[LabourChargeService, Depends(get_labour_charge_service)],
) -> LabourChargeResponse:
    """Update a labour charge."""
    return service.update(charge_id, payload)


@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_labour_charge(
    charge_id: uuid.UUID,
    service: Annotated[LabourChargeService, Depends(get_labour_charge_service)],
) -> None:
    """Delete a labour charge."""
    service.delete(charge_id)
