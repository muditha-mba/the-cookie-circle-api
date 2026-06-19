"""Shared SQLAlchemy enum column types (persist enum values, not names)."""

from sqlalchemy import Enum

from app.core.enums import (
    ActivityAction,
    ActivityResourceType,
    AdminRole,
    ClientDeviceType,
    CollectionSelectionMode,
    CommunicationType,
    CustomerSource,
    InventoryMovementReferenceType,
    InventoryMovementType,
    MarketingSource,
    OrderSource,
    OrderStatus,
    OrderType,
    PaymentMethod,
    PaymentStatus,
    ProductionBatchStatus,
    PurchasePlanningStatus,
    PurchaseReceiptStatus,
    ReviewItemSentiment,
)


def _enum_values(enum_cls: type) -> list[str]:
    return [member.value for member in enum_cls]


admin_role_enum = Enum(
    AdminRole,
    name="admin_role",
    values_callable=_enum_values,
)

activity_action_enum = Enum(
    ActivityAction,
    name="activity_action",
    values_callable=_enum_values,
)

activity_resource_type_enum = Enum(
    ActivityResourceType,
    name="activity_resource_type",
    values_callable=_enum_values,
)

client_device_type_enum = Enum(
    ClientDeviceType,
    name="client_device_type",
    values_callable=_enum_values,
)

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

order_type_enum = Enum(
    OrderType,
    name="order_type",
    values_callable=_enum_values,
)

collection_selection_mode_enum = Enum(
    CollectionSelectionMode,
    name="collection_selection_mode",
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

inventory_movement_type_enum = Enum(
    InventoryMovementType,
    name="inventory_movement_type",
    values_callable=_enum_values,
)

inventory_movement_reference_type_enum = Enum(
    InventoryMovementReferenceType,
    name="inventory_movement_reference_type",
    values_callable=_enum_values,
)

purchase_receipt_status_enum = Enum(
    PurchaseReceiptStatus,
    name="purchase_receipt_status",
    values_callable=_enum_values,
)

review_item_sentiment_enum = Enum(
    ReviewItemSentiment,
    name="review_item_sentiment",
    values_callable=_enum_values,
)
