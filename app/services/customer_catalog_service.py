"""Public catalog for client ordering."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.collection import Collection
from app.models.collection_package import CollectionPackage
from app.models.product import Product
from app.schemas.client_ordering import (
    ClientCatalogCollection,
    ClientCatalogPackage,
    ClientCatalogProduct,
    ClientCatalogResponse,
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
                    selectinload(Collection.allowed_categories),
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
        return ClientCatalogCollection(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            package_code=collection.package.code,
            package_name=collection.package.name,
            package_size=collection.package_size,
            package_fee=collection.package_fee,
            allowed_category_ids=[category.id for category in collection.allowed_categories],
        )

    def _load_selectable_products(self) -> list[ClientCatalogProduct]:
        stmt = (
            select(Product)
            .where(Product.is_active.is_(True), Product.is_public.is_(True))
            .options(selectinload(Product.category))
            .order_by(Product.name)
        )
        rows = list(self.db.scalars(stmt).all())
        return [
            ClientCatalogProduct(
                id=product.id,
                name=product.name,
                description=product.description,
                category_id=product.category_id,
                category_code=product.category.code,
                category_name=product.category.name,
                selling_price_per_unit=(
                    _money(product.selling_price / product.yield_quantity)
                    if product.yield_quantity > 0
                    else product.selling_price
                ),
            )
            for product in rows
        ]
