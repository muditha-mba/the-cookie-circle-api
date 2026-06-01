"""Shared SQLAlchemy column types for global charge models."""

from sqlalchemy import Enum

from app.core.enums import ChargeType

charge_type_enum = Enum(
    ChargeType,
    name="charge_type",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)
