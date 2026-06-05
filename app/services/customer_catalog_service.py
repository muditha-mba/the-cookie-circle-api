"""Public catalog for client ordering."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import CollectionSelectionMode
from app.models.collection import Collection
from app.models.collection_package import CollectionPackage
from app.models.product import Product
from app.schemas.client_ordering import (
    ClientCatalogCollection,
    ClientCatalogPackage,
    ClientCatalogProduct,
    ClientCatalogResponse,
    CollectionCookieSelectionInput,
)
from app.services.product_cost_service import _money


class CustomerCatalogService:
    """Read-only storefront catalog."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_catalog(self) -> ClientCatalogResponse:
        packages = self._load_packages()
        products = self._load_selectable_products()
        return ClientCatalogResponse(packages=packages, selectable_products=products)

    def _load_packages(self) -> list[ClientCatalogPackage]:
        stmt = (
            select(CollectionPackage)
            .where(CollectionPackage.is_active.is_(True))
            .options(
                selectinload(CollectionPackage.collections).options(
                    selectinload(Collection.product_lines),
                    selectinload(Collection.package),
                ),
            )
            .order_by(CollectionPackage.name)
        )
        package_rows = list(self.db.scalars(stmt).unique().all())
        result: list[ClientCatalogPackage] = []
        for package in package_rows:
            collections = [
                self._to_catalog_collection(collection)
                for collection in package.collections
                if collection.is_active and collection.is_public
            ]
            if collections:
                result.append(
                    ClientCatalogPackage(
                        code=package.code,
                        name=package.name,
                        description=package.description,
                        badge_tone=package.badge_tone,
                        collections=sorted(collections, key=lambda row: row.name),
                    ),
                )
        return result

    def _to_catalog_collection(self, collection: Collection) -> ClientCatalogCollection:
        default_composition: list[CollectionCookieSelectionInput] = []
        if collection.selection_mode == CollectionSelectionMode.FIXED:
            default_composition = [
                CollectionCookieSelectionInput(
                    product_id=line.product_id,
                    quantity=line.quantity,
                )
                for line in collection.product_lines
            ]
        return ClientCatalogCollection(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            package_code=collection.package.code,
            package_name=collection.package.name,
            selling_price=collection.selling_price,
            selection_mode=collection.selection_mode,
            max_premium_cookies=collection.max_premium_cookies,
            cookie_slot_count=collection.cookie_slot_count,
            default_composition=default_composition,
        )

    def _load_selectable_products(self) -> list[ClientCatalogProduct]:
        stmt = (
            select(Product)
            .where(Product.is_active.is_(True), Product.is_public.is_(True))
            .order_by(Product.name)
        )
        rows = list(self.db.scalars(stmt).all())
        return [
            ClientCatalogProduct(
                id=product.id,
                name=product.name,
                description=product.description,
                is_premium=product.is_premium,
                selling_price_per_unit=(
                    _money(product.selling_price / product.yield_quantity)
                    if product.yield_quantity > 0
                    else product.selling_price
                ),
            )
            for product in rows
        ]
