"""Public catalog for client ordering."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import PackagingFeeMode
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
from app.utils.collection_packaging_fee import (
    collection_order_quantity_bounds,
    resolve_collection_packaging_fee,
)


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
                        min_quantity=package.min_quantity,
                        max_quantity=package.max_quantity,
                        packaging_fee_mode=self._fee_mode(package.packaging_fee_mode),
                        packaging_fee_amount=_money(package.packaging_fee_amount),
                        collections=sorted(collections, key=lambda row: row.name),
                    ),
                )
        return result

    def _to_catalog_collection(self, collection: Collection) -> ClientCatalogCollection:
        min_qty, max_qty = collection_order_quantity_bounds(collection)
        package = collection.package
        fee_mode = self._fee_mode(
            package.packaging_fee_mode if package else PackagingFeeMode.FLAT.value,
        )
        fee_amount = (
            _money(package.packaging_fee_amount)
            if package and package.packaging_fee_amount > 0
            else _money(collection.package_fee)
        )
        sample_fee = resolve_collection_packaging_fee(
            collection,
            cookie_count=Decimal(min_qty),
        )
        return ClientCatalogCollection(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            package_code=collection.package.code,
            package_name=collection.package.name,
            package_size=collection.package_size,
            min_quantity=min_qty,
            max_quantity=max_qty,
            packaging_fee_mode=fee_mode,
            packaging_fee_amount=fee_amount,
            allowed_category_ids=[category.id for category in collection.allowed_categories],
            premium_packaging_included=sample_fee > 0,
        )

    @staticmethod
    def _fee_mode(value: str | None) -> str:
        mode = (value or PackagingFeeMode.FLAT.value).strip().lower()
        if mode == PackagingFeeMode.PER_COOKIE.value:
            return PackagingFeeMode.PER_COOKIE.value
        return PackagingFeeMode.FLAT.value

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
