"""Labour charge business logic."""

from sqlalchemy.orm import Session

from app.models.labour_charge import LabourCharge
from app.schemas.charge import (
    LabourChargeCreate,
    LabourChargeResponse,
    LabourChargeUpdate,
)
from app.services.charge_service import ChargeService


class LabourChargeService(
    ChargeService[
        LabourCharge,
        LabourChargeCreate,
        LabourChargeUpdate,
        LabourChargeResponse,
    ],
):
    """Handles labour charge operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(
            db,
            model=LabourCharge,
            response_schema=LabourChargeResponse,
            entity_label="Labour charge",
            duplicate_name_message="A labour charge with this name already exists",
        )
