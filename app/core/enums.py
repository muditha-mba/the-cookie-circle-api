"""Application enums."""

import enum


class UserRole(str, enum.Enum):
    """Supported user roles."""

    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"


class AdminRole(str, enum.Enum):
    """Admin panel access tier — only meaningful when role is ADMIN."""

    SUPER_ADMIN = "super_admin"
    CLERK_ADMIN = "clerk_admin"


class AppContext(str, enum.Enum):
    """Application context for login role enforcement."""

    ADMIN = "admin"
    CLIENT = "client"


class ChargeType(str, enum.Enum):
    """Global charge calculation type."""

    FIXED = "fixed"
    PERCENTAGE = "percentage"


class ChargeApplicability(str, enum.Enum):
    """Where a global charge may be attached."""

    PRODUCT = "product"
    COLLECTION = "collection"
    BOTH = "both"


class Weekday(str, enum.Enum):
    """Day of week for delivery scheduling."""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class CustomerSource(str, enum.Enum):
    """How a customer record was created."""

    REGISTERED = "registered"
    GUEST = "guest"
    MANUAL = "manual"


class MarketingSource(str, enum.Enum):
    """How the customer discovered the business (admin-tracked)."""

    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    WHATSAPP = "whatsapp"
    TIKTOK = "tiktok"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    PINTEREST = "pinterest"
    EMAIL = "email"
    REFERRAL = "referral"
    GOOGLE = "google"
    WALK_IN = "walk_in"
    OTHER = "other"


class CustomerSegment(str, enum.Enum):
    """System-calculated customer relationship segment."""

    NEW = "new"
    RETURNING = "returning"
    VIP = "vip"
    INACTIVE = "inactive"


class CommunicationType(str, enum.Enum):
    """Internal customer communication log entry type."""

    PHONE_CALL = "phone_call"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    MANUAL_FOLLOW_UP = "manual_follow_up"


class OrderSource(str, enum.Enum):
    """Channel where the order originated."""

    WEBSITE = "website"
    ADMIN = "admin"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    MANUAL = "manual"
    WALK_IN = "walk_in"
    PHONE = "phone"


class OrderType(str, enum.Enum):
    """Customer-facing order classification for operations and analytics."""

    WEEKLY_DELIVERY = "weekly_delivery"
    CATERING = "catering"


class CollectionSelectionMode(str, enum.Enum):
    """How customers configure cookies within a collection."""

    FIXED = "fixed"
    FLEXIBLE = "flexible"
    PREMIUM_LIMITED = "premium_limited"


class PaymentMethod(str, enum.Enum):
    """How the customer will pay."""

    CASH_ON_DELIVERY = "cash_on_delivery"
    BANK_TRANSFER = "bank_transfer"
    ONLINE_CARD = "online_card"
    ONLINE_BANK_DEBIT = "online_bank_debit"
    MANUAL = "manual"


class PaymentStatus(str, enum.Enum):
    """Payment lifecycle state."""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentSessionStatus(str, enum.Enum):
    """WebXPay payment session lifecycle state."""

    INITIATED = "initiated"      # Session created; redirect payload ready
    REDIRECTED = "redirected"    # Customer was sent to WebXPay billing page
    COMPLETED = "completed"      # WebXPay confirmed payment approved — terminal
    FAILED = "failed"            # WebXPay reported payment declined — terminal (retry allowed)
    EXPIRED = "expired"          # Session timed out before callback received — terminal
    TAMPERED = "tampered"        # Return payload failed integrity check — terminal (critical alert)


class ReviewItemSentiment(str, enum.Enum):
    """Per-item thumbs feedback within an order review."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class OrderStatus(str, enum.Enum):
    """Order fulfillment lifecycle."""

    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class ProductionBatchStatus(str, enum.Enum):
    """Production batch planning lifecycle (not execution or inventory)."""

    DRAFT = "draft"
    PLANNING = "planning"
    READY = "ready"


class PurchasePlanningStatus(str, enum.Enum):
    """Purchase planning status per item for a production batch."""

    NOT_PLANNED = "not_planned"
    PLANNED = "planned"
    ORDERED = "ordered"


class InventoryMovementType(str, enum.Enum):
    """Inventory ledger movement classification."""

    RECEIPT = "receipt"
    ADJUSTMENT = "adjustment"
    WASTE = "waste"
    CONSUMPTION = "consumption"


class InventoryMovementReferenceType(str, enum.Enum):
    """Source document linked to an inventory movement."""

    PURCHASE_RECEIPT = "purchase_receipt"
    MANUAL = "manual"
    CONSUMPTION_PROPOSAL = "consumption_proposal"


class PurchaseReceiptStatus(str, enum.Enum):
    """Purchase receipt lifecycle."""

    DRAFT = "draft"
    CONFIRMED = "confirmed"


class ConsumptionProposalStatus(str, enum.Enum):
    """Inventory consumption proposal lifecycle."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    DISMISSED = "dismissed"


class ConsumptionDemandType(str, enum.Enum):
    """Ingredient vs packaging demand on a consumption proposal line."""

    INGREDIENT = "ingredient"
    PACKAGING = "packaging"


class ActivityAction(str, enum.Enum):
    """Admin activity log action."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    EXPORTED = "exported"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    LOGOUT_ALL = "logout_all"


class ActivityResourceType(str, enum.Enum):
    """Entity or module targeted by an admin activity."""

    ORDER = "order"
    PRODUCT = "product"
    CUSTOMER = "customer"
    COLLECTION = "collection"
    COLLECTION_PACKAGE = "collection_package"
    PRODUCT_ITEM = "product_item"
    PRODUCT_ITEM_TYPE = "product_item_type"
    PRODUCT_CATEGORY = "product_category"
    SUPPLIER = "supplier"
    DELIVERY_AREA = "delivery_area"
    UTILITY_CHARGE = "utility_charge"
    LABOUR_CHARGE = "labour_charge"
    TAX_CHARGE = "tax_charge"
    DISCOUNT_RULE = "discount_rule"
    CUSTOMER_DISCOUNT_GRANT = "customer_discount_grant"
    PROMOTION_SLIDE = "promotion_slide"
    BUSINESS_SETTINGS = "business_settings"
    FAQ = "faq"
    FAQ_CATEGORY = "faq_category"
    SHARED_MEMORY = "shared_memory"
    REVIEW = "review"
    PRODUCTION = "production"
    ANALYTICS = "analytics"
    DASHBOARD = "dashboard"
    AUTH = "auth"
    USER = "user"
    SYSTEM = "system"
    INVENTORY_LOT = "inventory_lot"
    INVENTORY_MOVEMENT = "inventory_movement"
    PURCHASE_RECEIPT = "purchase_receipt"
    CONSUMPTION_PROPOSAL = "consumption_proposal"


class ClientDeviceType(str, enum.Enum):
    """Coarse device classification from User-Agent."""

    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    BOT = "bot"
    UNKNOWN = "unknown"


class DiscountType(str, enum.Enum):
    """How a discount is calculated."""

    FIXED = "fixed"
    PERCENTAGE = "percentage"


class DiscountRuleType(str, enum.Enum):
    """Rule evaluation strategy — extensible for future strategies."""

    ORDER_FREQUENCY_IN_WINDOW = "order_frequency_in_window"


class DiscountGrantStatus(str, enum.Enum):
    """Lifecycle state of a customer discount grant."""

    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    REVOKED = "revoked"


class DiscountSource(str, enum.Enum):
    """How a discount grant was created."""

    RULE = "rule"
    MANUAL = "manual"


class DiscountAuditEventType(str, enum.Enum):
    """Business-level events tracked in the discount audit trail."""

    RULE_EVALUATED = "rule_evaluated"
    GRANTED = "granted"
    USED = "used"
    EXPIRED = "expired"
    REVOKED = "revoked"
    OVERRIDE_SET = "override_set"


