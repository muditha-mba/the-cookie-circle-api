"""Map admin API paths to structured activity log fields."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.enums import ActivityAction, ActivityResourceType

_RESOURCE_BY_SEGMENT: dict[str, ActivityResourceType] = {
    "discount-rules": ActivityResourceType.DISCOUNT_RULE,
    "promotion-slides": ActivityResourceType.PROMOTION_SLIDE,
    "discounts": ActivityResourceType.CUSTOMER_DISCOUNT_GRANT,
    "orders": ActivityResourceType.ORDER,
    "products": ActivityResourceType.PRODUCT,
    "customers": ActivityResourceType.CUSTOMER,
    "collections": ActivityResourceType.COLLECTION,
    "collection-packages": ActivityResourceType.COLLECTION_PACKAGE,
    "product-items": ActivityResourceType.PRODUCT_ITEM,
    "product-item-types": ActivityResourceType.PRODUCT_ITEM_TYPE,
    "product-categories": ActivityResourceType.PRODUCT_CATEGORY,
    "suppliers": ActivityResourceType.SUPPLIER,
    "delivery-areas": ActivityResourceType.DELIVERY_AREA,
    "utility-charges": ActivityResourceType.UTILITY_CHARGE,
    "labour-charges": ActivityResourceType.LABOUR_CHARGE,
    "tax-charges": ActivityResourceType.TAX_CHARGE,
    "business-settings": ActivityResourceType.BUSINESS_SETTINGS,
    "faqs": ActivityResourceType.FAQ,
    "faq-categories": ActivityResourceType.FAQ_CATEGORY,
    "shared-memories": ActivityResourceType.SHARED_MEMORY,
    "reviews": ActivityResourceType.REVIEW,
    "production": ActivityResourceType.PRODUCTION,
    "analytics": ActivityResourceType.ANALYTICS,
    "dashboard": ActivityResourceType.DASHBOARD,
    "users": ActivityResourceType.USER,
    "auth": ActivityResourceType.AUTH,
    "activity-logs": ActivityResourceType.SYSTEM,
    "inventory": ActivityResourceType.INVENTORY_LOT,
    "purchase-receipts": ActivityResourceType.PURCHASE_RECEIPT,
    "consumption-proposals": ActivityResourceType.CONSUMPTION_PROPOSAL,
}

_RESOURCE_LABELS: dict[ActivityResourceType, str] = {
    ActivityResourceType.ORDER: "Order",
    ActivityResourceType.PRODUCT: "Product",
    ActivityResourceType.CUSTOMER: "Customer",
    ActivityResourceType.COLLECTION: "Collection",
    ActivityResourceType.COLLECTION_PACKAGE: "Collection package",
    ActivityResourceType.PRODUCT_ITEM: "Product item",
    ActivityResourceType.PRODUCT_ITEM_TYPE: "Item type",
    ActivityResourceType.PRODUCT_CATEGORY: "Product category",
    ActivityResourceType.SUPPLIER: "Supplier",
    ActivityResourceType.DELIVERY_AREA: "Delivery area",
    ActivityResourceType.UTILITY_CHARGE: "Utility charge",
    ActivityResourceType.LABOUR_CHARGE: "Labour charge",
    ActivityResourceType.TAX_CHARGE: "Tax charge",
    ActivityResourceType.DISCOUNT_RULE: "Discount rule",
    ActivityResourceType.CUSTOMER_DISCOUNT_GRANT: "Customer discount grant",
    ActivityResourceType.PROMOTION_SLIDE: "Promotion slide",
    ActivityResourceType.BUSINESS_SETTINGS: "Business settings",
    ActivityResourceType.FAQ: "FAQ",
    ActivityResourceType.FAQ_CATEGORY: "FAQ category",
    ActivityResourceType.SHARED_MEMORY: "Shared memory",
    ActivityResourceType.REVIEW: "Review",
    ActivityResourceType.PRODUCTION: "Production",
    ActivityResourceType.ANALYTICS: "Analytics",
    ActivityResourceType.DASHBOARD: "Dashboard",
    ActivityResourceType.USER: "User",
    ActivityResourceType.AUTH: "Authentication",
    ActivityResourceType.SYSTEM: "System",
    ActivityResourceType.INVENTORY_LOT: "Inventory",
    ActivityResourceType.INVENTORY_MOVEMENT: "Inventory movement",
    ActivityResourceType.PURCHASE_RECEIPT: "Purchase receipt",
    ActivityResourceType.CONSUMPTION_PROPOSAL: "Consumption proposal",
}


@dataclass(frozen=True, slots=True)
class ParsedActivityPath:
    action: ActivityAction
    resource_type: ActivityResourceType
    resource_id: uuid.UUID | None
    resource_label: str


def _try_parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def parse_activity_path(method: str, path: str) -> ParsedActivityPath:
    """Derive activity fields from an admin API request path."""
    normalized_method = method.upper()
    trimmed = path.split("?", 1)[0]
    if trimmed.startswith("/api/v1/"):
        trimmed = trimmed[len("/api/v1/") :]
    segments = [segment for segment in trimmed.strip("/").split("/") if segment]

    resource_type = ActivityResourceType.SYSTEM
    resource_id: uuid.UUID | None = None
    subresource: str | None = None

    if segments:
        resource_type = _RESOURCE_BY_SEGMENT.get(segments[0], ActivityResourceType.SYSTEM)
        if len(segments) >= 2:
            resource_id = _try_parse_uuid(segments[1])
            if resource_id is None and len(segments) >= 3:
                subresource = segments[2]
            elif len(segments) >= 2 and not resource_id:
                subresource = segments[1]

    action = ActivityAction.UPDATED
    if normalized_method == "POST":
        action = ActivityAction.CREATED
    elif normalized_method == "DELETE":
        action = ActivityAction.DELETED
    elif normalized_method in {"PATCH", "PUT"}:
        action = ActivityAction.UPDATED

    if "export" in segments or trimmed.endswith("/export"):
        action = ActivityAction.EXPORTED

    label = _RESOURCE_LABELS.get(resource_type, "System")
    if resource_id is not None:
        label = f"{label} {str(resource_id)[:8]}"
    elif subresource:
        label = f"{label} ({subresource.replace('-', ' ')})"

    return ParsedActivityPath(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_label=label,
    )
