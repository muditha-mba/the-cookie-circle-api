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
    STRIPE = "stripe"
    MANUAL = "manual"


class PaymentStatus(str, enum.Enum):
    """Payment lifecycle state."""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


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


class ClientDeviceType(str, enum.Enum):
    """Coarse device classification from User-Agent."""

    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    BOT = "bot"
    UNKNOWN = "unknown"


