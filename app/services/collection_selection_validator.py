"""Validate customer cookie selections against package configuration."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.collection import Collection
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.client_ordering import CollectionCookieSelectionInput
from app.services.package_pricing_service import normalize_per_pack
from app.utils.collection_packaging_fee import collection_order_quantity_bounds


class CollectionSelectionValidator:
    """Shared UI/API validation for package builder rules."""

    def __init__(self, db: Session) -> None:
        self.products = ProductRepository(db)

    def validate(
        self,
        collection: Collection,
        *,
        selections: list[CollectionCookieSelectionInput] | None,
        line_quantity: Decimal,
    ) -> list[tuple[Product, Decimal]]:
        if not selections:
            raise ValidationError(f"Cookie selections are required for '{collection.name}'.")

        products_by_id = self._load_products(collection, selections)
        per_pack = normalize_per_pack(selections, products_by_id)
        self._validate_cookie_count(collection, per_pack)

        return [(product, qty * line_quantity) for product, qty in per_pack.items()]

    def validate_per_pack(
        self,
        collection: Collection,
        *,
        selections: list[CollectionCookieSelectionInput],
    ) -> dict[Product, Decimal]:
        products_by_id = self._load_products(collection, selections)
        per_pack = normalize_per_pack(selections, products_by_id)
        self._validate_cookie_count(collection, per_pack)
        return per_pack

    def _validate_cookie_count(
        self,
        collection: Collection,
        per_pack: dict[Product, Decimal],
    ) -> None:
        total_cookies = sum(per_pack.values(), Decimal("0"))
        min_qty, max_qty = collection_order_quantity_bounds(collection)

        if total_cookies < Decimal(min_qty) or total_cookies > Decimal(max_qty):
            if min_qty == max_qty:
                raise ValidationError(
                    f"'{collection.name}' requires exactly {min_qty} cookies; "
                    f"received {total_cookies.normalize()}.",
                )
            raise ValidationError(
                f"'{collection.name}' requires between {min_qty} and {max_qty} cookies; "
                f"received {total_cookies.normalize()}.",
            )

    def _load_products(
        self,
        collection: Collection,
        selections: list[CollectionCookieSelectionInput],
    ) -> dict[UUID, Product]:
        allowed_category_ids = {category.id for category in collection.allowed_categories}
        if not allowed_category_ids:
            raise ValidationError(
                f"Package '{collection.name}' has no allowed categories configured.",
            )

        ids = [selection.product_id for selection in selections]
        loaded = {product.id: product for product in self.products.get_for_costing_by_ids(ids)}
        products_by_id: dict[UUID, Product] = {}

        for selection in selections:
            product = loaded.get(selection.product_id)
            if product is None:
                raise ValidationError("Selected product was not found.")
            if not product.is_active or not product.is_public:
                raise ValidationError(f"Product '{product.name}' is not available for ordering.")
            if product.category_id not in allowed_category_ids:
                raise ValidationError(
                    f"Product '{product.name}' is not allowed for package '{collection.name}'.",
                )
            products_by_id[selection.product_id] = product
        return products_by_id
