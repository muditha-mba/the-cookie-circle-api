"""Labour charge business logic — monthly overhead tracking."""

from sqlalchemy.orm import Session

from app.models.labour_bill_entry import LabourBillEntry
from app.models.labour_charge import LabourCharge
from app.schemas.charge import (
    LabourChargeDetailResponse,
    LabourChargeResponse,
)
from app.services.charge_service import OverheadChargeService


class LabourChargeService(
    OverheadChargeService[LabourCharge, LabourBillEntry],
):
    """Handles labour charge and bill entry operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(
            db,
            model=LabourCharge,
            bill_entry_model=LabourBillEntry,
            charge_fk_attr="labour_charge_id",
            response_schema=LabourChargeResponse,
            detail_response_schema=LabourChargeDetailResponse,
            entity_label="Labour charge",
            duplicate_name_message="A labour charge with this name already exists",
        )
