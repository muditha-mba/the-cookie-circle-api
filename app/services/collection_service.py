"""Package configuration business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.packaging import is_packaging_item_type
from app.models.collection import Collection
from app.models.collection_item_line import CollectionItemLine
from app.models.product_item import ProductItem
from app.repositories.collection_repository import CollectionRepository
from app.repositories.collection_package_repository import CollectionPackageRepository
from app.repositories.product_category_repository import ProductCategoryRepository
from app.repositories.product_item_repository import ProductItemRepository
from app.schemas.collection import (
    CollectionCreate,
    CollectionDetailResponse,
    CollectionItemLineInput,
    CollectionItemLineResponse,
    CollectionListParams,
    CollectionSummaryResponse,
    CollectionUpdate,
    ProductCategorySummary,
)
from app.schemas.pagination import PaginatedResponse
from app.schemas.product import AttachedChargeSummary
from app.utils.charge_applicability import COLLECTION_APPLICABILITIES, validate_charges_for_target


class CollectionService:
    """Handles package configuration CRUD."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.collections = CollectionRepository(db)
        self.collection_packages = CollectionPackageRepository(db)
        self.product_categories = ProductCategoryRepository(db)
        self.product_items = ProductItemRepository(db)

    def create(self, payload: CollectionCreate) -> CollectionDetailResponse:
        if self.collections.get_by_name(payload.name):
            raise ConflictError("A collection with this name already exists")

        collection = Collection(
            name=payload.name,
            description=payload.description,
            package_id=self._resolve_package(payload.package_id).id,
            package_size=payload.package_size,
            package_fee=payload.package_fee,
            is_active=payload.is_active,
            is_public=payload.is_public,
        )
        collection.allowed_categories = self._resolve_categories(payload.allowed_category_ids)
        self._apply_item_lines(collection, payload.item_lines)
        self._apply_charges(
            collection,
            utility_charge_ids=payload.utility_charge_ids,
            labour_charge_ids=payload.labour_charge_ids,
            tax_charge_ids=payload.tax_charge_ids,
        )
        self.collections.create(collection)
        self.db.commit()
        loaded = self.collections.get_by_id(collection.id)
        assert loaded is not None
        return self._to_detail_response(loaded)

    def get(self, collection_id: uuid.UUID) -> CollectionDetailResponse:
        collection = self.collections.get_by_id(collection_id)
        if not collection:
            raise NotFoundError("Collection not found")
        return self._to_detail_response(collection)

    def list(self, params: CollectionListParams) -> PaginatedResponse[CollectionSummaryResponse]:
        items, total = self.collections.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            package_id=params.package_id,
        )
        return PaginatedResponse(
            items=[self._to_summary_response(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.collections.total_pages(total, params.page_size),
        )

    def update(self, collection_id: uuid.UUID, payload: CollectionUpdate) -> CollectionDetailResponse:
        collection = self.collections.get_by_id(collection_id)
        if not collection:
            raise NotFoundError("Collection not found")

        update_data = payload.model_dump(
            exclude_unset=True,
            exclude={
                "item_lines",
                "allowed_category_ids",
                "utility_charge_ids",
                "labour_charge_ids",
                "tax_charge_ids",
            },
        )
        if (
            not update_data
            and payload.item_lines is None
            and payload.allowed_category_ids is None
            and payload.utility_charge_ids is None
            and payload.labour_charge_ids is None
            and payload.tax_charge_ids is None
        ):
            raise ValidationError("No fields provided to update")

        if payload.name is not None:
            existing = self.collections.get_by_name(payload.name)
            if existing and existing.id != collection.id:
                raise ConflictError("A collection with this name already exists")
            collection.name = payload.name

        if payload.description is not None:
            collection.description = payload.description
        if payload.package_id is not None:
            collection.package_id = self._resolve_package(payload.package_id).id
        if payload.package_size is not None:
            collection.package_size = payload.package_size
        if payload.package_fee is not None:
            collection.package_fee = payload.package_fee
        if payload.is_active is not None:
            collection.is_active = payload.is_active
        if payload.is_public is not None:
            collection.is_public = payload.is_public
        if payload.allowed_category_ids is not None:
            collection.allowed_categories = self._resolve_categories(payload.allowed_category_ids)

        if payload.item_lines is not None:
            self._replace_item_lines(collection, payload.item_lines)

        if (
            payload.utility_charge_ids is not None
            or payload.labour_charge_ids is not None
            or payload.tax_charge_ids is not None
        ):
            self._apply_charges(
                collection,
                utility_charge_ids=(
                    payload.utility_charge_ids
                    if payload.utility_charge_ids is not None
                    else [c.id for c in collection.utility_charges]
                ),
                labour_charge_ids=(
                    payload.labour_charge_ids
                    if payload.labour_charge_ids is not None
                    else [c.id for c in collection.labour_charges]
                ),
                tax_charge_ids=(
                    payload.tax_charge_ids
                    if payload.tax_charge_ids is not None
                    else [c.id for c in collection.tax_charges]
                ),
            )

        self.db.add(collection)
        self.db.commit()
        loaded = self.collections.get_by_id(collection.id)
        assert loaded is not None
        return self._to_detail_response(loaded)

    def delete(self, collection_id: uuid.UUID) -> None:
        collection = self.collections.get_by_id(collection_id)
        if not collection:
            raise NotFoundError("Collection not found")
        self.collections.delete(collection)
        self.db.commit()

    def _replace_item_lines(
        self,
        collection: Collection,
        lines: list[CollectionItemLineInput],
    ) -> None:
        collection.item_lines.clear()
        self.db.flush()
        if lines:
            self._apply_item_lines(collection, lines)

    def _apply_item_lines(
        self,
        collection: Collection,
        lines: list[CollectionItemLineInput],
    ) -> None:
        if not lines:
            return
        seen: set[uuid.UUID] = set()
        for line in lines:
            if line.product_item_id in seen:
                raise ValidationError("Duplicate packaging item in collection")
            seen.add(line.product_item_id)

        items = self._load_packaging_items([line.product_item_id for line in lines])
        for line in lines:
            item = items[line.product_item_id]
            collection.item_lines.append(
                CollectionItemLine(
                    product_item_id=item.id,
                    quantity=line.quantity,
                ),
            )

    def _apply_charges(
        self,
        collection: Collection,
        *,
        utility_charge_ids: list[uuid.UUID],
        labour_charge_ids: list[uuid.UUID],
        tax_charge_ids: list[uuid.UUID],
    ) -> None:
        collection.utility_charges = self._resolve_charges(
            utility_charge_ids,
            self.collections.get_utility_charges_by_ids,
            "utility",
        )
        collection.labour_charges = self._resolve_charges(
            labour_charge_ids,
            self.collections.get_labour_charges_by_ids,
            "labour",
        )
        collection.tax_charges = self._resolve_charges(
            tax_charge_ids,
            self.collections.get_tax_charges_by_ids,
            "tax",
        )

    def _resolve_categories(self, ids: list[uuid.UUID]):
        if not ids:
            raise ValidationError("At least one allowed category is required")
        categories = self.product_categories.get_by_ids(ids)
        if len(categories) != len(set(ids)):
            raise NotFoundError("One or more product categories were not found")
        inactive = [category.name for category in categories if not category.is_active]
        if inactive:
            raise ValidationError(f"Inactive categories cannot be assigned: {', '.join(inactive)}")
        return categories

    def _resolve_charges(self, ids: list[uuid.UUID], loader, label: str):
        if not ids:
            return []
        charges = loader(ids)
        if len(charges) != len(set(ids)):
            raise NotFoundError(f"One or more {label} charges were not found")
        validate_charges_for_target(
            charges,
            target_label="collection",
            allowed=COLLECTION_APPLICABILITIES,
        )
        return charges

    def _load_packaging_items(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, ProductItem]:
        items_list = self.product_items.get_by_ids_with_type(ids)
        items: dict[uuid.UUID, ProductItem] = {item.id: item for item in items_list}
        for item_id in ids:
            item = items.get(item_id)
            if not item:
                raise NotFoundError(f"Product item not found: {item_id}")
            if not item.is_active:
                raise ValidationError(f"Product item is inactive: {item.name}")
            if not is_packaging_item_type(item.item_type.name):
                raise ValidationError(
                    "Only packaging product items can be added to a collection. "
                    f"'{item.name}' is not a packaging item.",
                )
        return items

    def _to_summary_response(self, collection: Collection) -> CollectionSummaryResponse:
        package = collection.package
        return CollectionSummaryResponse(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            package_id=collection.package_id,
            package_name=package.name if package else "",
            package_code=package.code if package else "",
            package_size=collection.package_size,
            package_fee=collection.package_fee,
            is_active=collection.is_active,
            is_public=collection.is_public,
            allowed_category_ids=[category.id for category in collection.allowed_categories],
            created_at=collection.created_at,
            updated_at=collection.updated_at,
        )

    def _to_detail_response(self, collection: Collection) -> CollectionDetailResponse:
        return CollectionDetailResponse(
            **self._to_summary_response(collection).model_dump(),
            allowed_categories=[
                ProductCategorySummary.model_validate(category)
                for category in collection.allowed_categories
            ],
            item_lines=[
                CollectionItemLineResponse(
                    id=line.id,
                    product_item_id=line.product_item_id,
                    product_item_name=line.product_item.name if line.product_item else "",
                    quantity=line.quantity,
                    unit=line.product_item.purchase_unit if line.product_item else "",
                )
                for line in collection.item_lines
            ],
            utility_charges=[self._charge_summary(c) for c in collection.utility_charges],
            labour_charges=[self._charge_summary(c) for c in collection.labour_charges],
            tax_charges=[self._charge_summary(c) for c in collection.tax_charges],
            package=collection.package,
        )

    def _resolve_package(self, package_id: uuid.UUID):
        package = self.collection_packages.get_by_id(package_id)
        if not package:
            raise NotFoundError("Collection package not found")
        if not package.is_active:
            raise ValidationError(f"Collection package is inactive: {package.name}")
        return package

    @staticmethod
    def _charge_summary(charge) -> AttachedChargeSummary:
        return AttachedChargeSummary(
            id=charge.id,
            name=charge.name,
            charge_type=charge.charge_type.value,
            amount=charge.amount,
            applicability=charge.applicability.value,
            is_active=charge.is_active,
        )
