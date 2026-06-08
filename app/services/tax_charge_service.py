"""Tax charge business logic."""

from sqlalchemy.orm import Session

from app.models.tax_charge import TaxCharge
from app.schemas.charge import (
    TaxChargeCreate,
    TaxChargeResponse,
    TaxChargeUpdate,
)
from app.services.charge_service import ChargeService


class TaxChargeService(
    ChargeService[
        TaxCharge,
        TaxChargeCreate,
        TaxChargeUpdate,
        TaxChargeResponse,
    ],
):
    """Handles tax charge operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(
            db,
            model=TaxCharge,
            response_schema=TaxChargeResponse,
            entity_label="Tax charge",
            duplicate_name_message="A tax charge with this name already exists",
        )
