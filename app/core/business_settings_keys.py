"""Known business setting keys stored in the key-value settings table."""

from app.core.social_platforms import SOCIAL_PLATFORMS, SocialPlatform

DELIVERY_FEE = "delivery_fee"
USE_FIXED_DELIVERY_FEE = "use_fixed_delivery_fee"
ORDER_CUTOFF_DAY = "order_cutoff_day"
DELIVERY_DAY = "delivery_day"
BUSINESS_PHONE = "business_phone"
BUSINESS_EMAIL = "business_email"
ONLINE_CARD_ENABLED = "online_card_enabled"
ONLINE_BANK_DEBIT_ENABLED = "online_bank_debit_enabled"
BANK_TRANSFER_ENABLED = "bank_transfer_enabled"
COD_ENABLED = "cod_enabled"
BANK_NAME = "bank_name"
BANK_ACCOUNT_NAME = "bank_account_name"
BANK_ACCOUNT_NUMBER = "bank_account_number"
BANK_BRANCH = "bank_branch"
BANK_TRANSFER_INSTRUCTIONS = "bank_transfer_instructions"
SHARED_MEMORIES_ENABLED = "shared_memories_enabled"
FAQS_ENABLED = "faqs_enabled"
DISCOUNTS_ENABLED = "discounts_enabled"
CATERING_PACKAGING_FEE_MODE = "catering_packaging_fee_mode"
CATERING_PACKAGING_FEE_AMOUNT = "catering_packaging_fee_amount"


def social_url_key(platform: SocialPlatform) -> str:
    return f"social_{platform}_url"


def social_enabled_key(platform: SocialPlatform) -> str:
    return f"social_{platform}_enabled"


SOCIAL_KEYS: tuple[str, ...] = tuple(
    key
    for platform in SOCIAL_PLATFORMS
    for key in (social_url_key(platform), social_enabled_key(platform))
)

ALL_KEYS = (
    DELIVERY_FEE,
    USE_FIXED_DELIVERY_FEE,
    ORDER_CUTOFF_DAY,
    DELIVERY_DAY,
    BUSINESS_PHONE,
    BUSINESS_EMAIL,
    ONLINE_CARD_ENABLED,
    ONLINE_BANK_DEBIT_ENABLED,
    BANK_TRANSFER_ENABLED,
    COD_ENABLED,
    BANK_NAME,
    BANK_ACCOUNT_NAME,
    BANK_ACCOUNT_NUMBER,
    BANK_BRANCH,
    BANK_TRANSFER_INSTRUCTIONS,
    SHARED_MEMORIES_ENABLED,
    FAQS_ENABLED,
    DISCOUNTS_ENABLED,
    CATERING_PACKAGING_FEE_MODE,
    CATERING_PACKAGING_FEE_AMOUNT,
    *SOCIAL_KEYS,
)
