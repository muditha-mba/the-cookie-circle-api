"""S3 object key prefixes for uploaded assets."""

from enum import StrEnum


class StorageAssetCategory(StrEnum):
    """Top-level asset folders served via the media proxy."""

    SHARED_MEMORIES = "shared-memories"
    REVIEWS = "reviews"
    PURCHASE_RECEIPTS = "purchase-receipts"
    PROMOTIONS = "promotions"
