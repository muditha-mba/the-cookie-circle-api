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
    DiscountAuditEventType,
    DiscountGrantStatus,
    DiscountRuleType,
    DiscountSource,
    DiscountType,
    InventoryMovementReferenceType,
    InventoryMovementType,
    MarketingSource,
    OrderSource,
    OrderStatus,
    OrderType,
    PaymentMethod,
    PaymentSessionStatus,
    PaymentStatus,
    ProductionBatchStatus,
    PurchasePlanningStatus,
    PurchaseReceiptStatus,
    ConsumptionDemandType,
    ConsumptionProposalStatus,
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

payment_session_status_enum = Enum(
    PaymentSessionStatus,
    name="payment_session_status",
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

consumption_proposal_status_enum = Enum(
    ConsumptionProposalStatus,
    name="consumption_proposal_status",
    values_callable=_enum_values,
)

consumption_demand_type_enum = Enum(
    ConsumptionDemandType,
    name="consumption_demand_type",
    values_callable=_enum_values,
)

review_item_sentiment_enum = Enum(
    ReviewItemSentiment,
    name="review_item_sentiment",
    values_callable=_enum_values,
)

discount_type_enum = Enum(
    DiscountType,
    name="discount_type",
    values_callable=_enum_values,
)

discount_rule_type_enum = Enum(
    DiscountRuleType,
    name="discount_rule_type",
    values_callable=_enum_values,
)

discount_grant_status_enum = Enum(
    DiscountGrantStatus,
    name="discount_grant_status",
    values_callable=_enum_values,
)

discount_source_enum = Enum(
    DiscountSource,
    name="discount_source",
    values_callable=_enum_values,
)

discount_audit_event_type_enum = Enum(
    DiscountAuditEventType,
    name="discount_audit_event_type",
    values_callable=_enum_values,
)
