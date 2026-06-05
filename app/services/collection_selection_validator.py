"""Validate customer cookie selections against collection rules."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.enums import CollectionSelectionMode
from app.core.exceptions import ValidationError
from app.models.collection import Collection
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.client_ordering import CollectionCookieSelectionInput


class CollectionSelectionValidator:
    """Shared UI/API validation for build-your-order collection rules."""

    def __init__(self, db: Session) -> None:
        self.products = ProductRepository(db)

    def validate(
        self,
        collection: Collection,
        *,
        selections: list[CollectionCookieSelectionInput] | None,
        line_quantity: Decimal,
    ) -> list[tuple[Product, Decimal]]:
        mode = collection.selection_mode
        slot_count = collection.cookie_slot_count

        if mode == CollectionSelectionMode.FIXED:
            if selections:
                raise ValidationError(
                    f"'{collection.name}' has a fixed composition and cannot be customized.",
                )
            return self._fixed_selections(collection, line_quantity)

        if not selections:
            raise ValidationError(f"Cookie selections are required for '{collection.name}'.")

        products_by_id = self._load_products(collection, selections)
        per_pack = self._normalize_per_pack(selections, products_by_id)

        total_cookies = sum(per_pack.values(), Decimal("0"))
        if slot_count is not None and total_cookies != Decimal(slot_count):
            raise ValidationError(
                f"'{collection.name}' requires exactly {slot_count} cookies per pack; "
                f"received {total_cookies.normalize()}.",
            )

        premium_count = sum(
            qty for product, qty in per_pack.items() if product.is_premium
        )
        if mode == CollectionSelectionMode.PREMIUM_LIMITED:
            max_premium = collection.max_premium_cookies
            if max_premium is not None and premium_count > Decimal(max_premium):
                raise ValidationError(
                    f"'{collection.name}' allows at most {max_premium} premium cookies per pack.",
                )

        return [(product, qty * line_quantity) for product, qty in per_pack.items()]

    @staticmethod
    def _fixed_selections(
        collection: Collection,
        line_quantity: Decimal,
    ) -> list[tuple[Product, Decimal]]:
        if not collection.product_lines:
            raise ValidationError(f"Collection '{collection.name}' has no composition configured.")
        rows: list[tuple[Product, Decimal]] = []
        for line in collection.product_lines:
            if line.product is None:
                raise ValidationError(f"Collection '{collection.name}' has an invalid product reference.")
            rows.append((line.product, line.quantity * line_quantity))
        return rows

    def _load_products(
        self,
        collection: Collection,
        selections: list[CollectionCookieSelectionInput],
    ) -> dict[UUID, Product]:
        allowed_line_ids = {line.product_id for line in collection.product_lines}
        restrict_to_lines = collection.selection_mode == CollectionSelectionMode.FIXED
        ids = [selection.product_id for selection in selections]
        loaded = {product.id: product for product in self.products.get_for_costing_by_ids(ids)}
        products_by_id: dict[UUID, Product] = {}

        for selection in selections:
            product = loaded.get(selection.product_id)
            if product is None:
                raise ValidationError("Selected product was not found.")
            if not product.is_active or not product.is_public:
                raise ValidationError(f"Product '{product.name}' is not available for ordering.")
            if restrict_to_lines and selection.product_id not in allowed_line_ids:
                raise ValidationError(
                    "One or more selected cookies are not allowed for this collection.",
                )
            products_by_id[selection.product_id] = product
        return products_by_id

    @staticmethod
    def _normalize_per_pack(
        selections: list[CollectionCookieSelectionInput],
        products_by_id: dict,
    ) -> dict[Product, Decimal]:
        per_pack: dict[Product, Decimal] = {}
        for selection in selections:
            product = products_by_id[selection.product_id]
            per_pack[product] = per_pack.get(product, Decimal("0")) + selection.quantity
        return per_pack
