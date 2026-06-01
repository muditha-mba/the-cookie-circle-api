"""Shared global charge Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.enums import ChargeType

ModelT = TypeVar("ModelT", bound=BaseModel)


class ChargeBase(BaseModel):
    """Shared charge fields."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    charge_type: ChargeType
    amount: Decimal = Field(gt=0)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_amount_for_type(self) -> "ChargeBase":
        if self.charge_type == ChargeType.PERCENTAGE and self.amount > Decimal("100"):
            raise ValueError("Percentage amount cannot exceed 100")
        return self


class ChargeUpdate(BaseModel):
    """Shared charge update fields."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    charge_type: ChargeType | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @model_validator(mode="after")
    def validate_amount_for_type(self) -> "ChargeUpdate":
        if self.amount is None or self.charge_type is None:
            return self
        if self.charge_type == ChargeType.PERCENTAGE and self.amount > Decimal("100"):
            raise ValueError("Percentage amount cannot exceed 100")
        return self


class ChargeResponse(ChargeBase):
    """Shared charge response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def make_charge_schemas(label: str) -> tuple[type[BaseModel], type[BaseModel], type[BaseModel]]:
    """Create module-specific schema types for OpenAPI clarity."""

    create_schema = type(
        f"{label}Create",
        (ChargeBase,),
        {"__doc__": f"Create {label} request."},
    )
    update_schema = type(
        f"{label}Update",
        (ChargeUpdate,),
        {"__doc__": f"Update {label} request."},
    )
    response_schema = type(
        f"{label}Response",
        (ChargeResponse,),
        {"__doc__": f"{label} response."},
    )
    return create_schema, update_schema, response_schema


UtilityChargeCreate, UtilityChargeUpdate, UtilityChargeResponse = make_charge_schemas(
    "UtilityCharge",
)
LabourChargeCreate, LabourChargeUpdate, LabourChargeResponse = make_charge_schemas(
    "LabourCharge",
)
TaxChargeCreate, TaxChargeUpdate, TaxChargeResponse = make_charge_schemas("TaxCharge")
