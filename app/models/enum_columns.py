"""Shared SQLAlchemy enum column types (persist enum values, not names)."""

from sqlalchemy import Enum

from app.core.enums import (
    CommunicationType,
    CustomerSource,
    MarketingSource,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    ProductionBatchStatus,
    PurchasePlanningStatus,
)


def _enum_values(enum_cls: type) -> list[str]:
    return [member.value for member in enum_cls]


customer_source_enum = Enum(
    CustomerSource,
    name="customer_source",
    values_callable=_enum_values,
)

marketing_source_enum = Enum(
    MarketingSource,
    name="marketing_source",
    values_callable=_enum_values,
)

communication_type_enum = Enum(
    CommunicationType,
    name="communication_type",
    values_callable=_enum_values,
)

order_source_enum = Enum(
    OrderSource,
    name="order_source",
    values_callable=_enum_values,
)

payment_method_enum = Enum(
    PaymentMethod,
    name="payment_method",
    values_callable=_enum_values,
)

payment_status_enum = Enum(
    PaymentStatus,
    name="payment_status",
    values_callable=_enum_values,
)

order_status_enum = Enum(
    OrderStatus,
    name="order_status",
    values_callable=_enum_values,
)

production_batch_status_enum = Enum(
    ProductionBatchStatus,
    name="production_batch_status",
    values_callable=_enum_values,
)

purchase_planning_status_enum = Enum(
    PurchasePlanningStatus,
    name="purchase_planning_status",
    values_callable=_enum_values,
)
