"""Utility charge business logic — monthly overhead tracking."""

from sqlalchemy.orm import Session

from app.models.utility_bill_entry import UtilityBillEntry
from app.models.utility_charge import UtilityCharge
from app.schemas.charge import (
    UtilityChargeDetailResponse,
    UtilityChargeResponse,
)
from app.services.charge_service import OverheadChargeService


class UtilityChargeService(
    OverheadChargeService[UtilityCharge, UtilityBillEntry],
):
    """Handles utility charge and bill entry operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(
            db,
            model=UtilityCharge,
            bill_entry_model=UtilityBillEntry,
            charge_fk_attr="utility_charge_id",
            response_schema=UtilityChargeResponse,
            detail_response_schema=UtilityChargeDetailResponse,
            entity_label="Utility charge",
            duplicate_name_message="A utility charge with this name already exists",
        )
