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

        total_cookies = sum(per_pack.values(), Decimal("0"))
        if total_cookies != Decimal(collection.package_size):
            raise ValidationError(
                f"'{collection.name}' requires exactly {collection.package_size} cookies per pack; "
                f"received {total_cookies.normalize()}.",
            )

        return [(product, qty * line_quantity) for product, qty in per_pack.items()]

    def validate_per_pack(
        self,
        collection: Collection,
        *,
        selections: list[CollectionCookieSelectionInput],
    ) -> dict[Product, Decimal]:
        products_by_id = self._load_products(collection, selections)
        return normalize_per_pack(selections, products_by_id)

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
