"""Utility charge business logic."""

from sqlalchemy.orm import Session

from app.models.utility_charge import UtilityCharge
from app.schemas.charge import (
    UtilityChargeCreate,
    UtilityChargeResponse,
    UtilityChargeUpdate,
)
from app.services.charge_service import ChargeService


class UtilityChargeService(
    ChargeService[
        UtilityCharge,
        UtilityChargeCreate,
        UtilityChargeUpdate,
        UtilityChargeResponse,
    ],
):
    """Handles utility charge operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(
            db,
            model=UtilityCharge,
            response_schema=UtilityChargeResponse,
            entity_label="Utility charge",
            duplicate_name_message="A utility charge with this name already exists",
        )
