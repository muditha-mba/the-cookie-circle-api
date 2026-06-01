"""Collection business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.packaging import is_packaging_item_type
from app.models.collection import Collection
from app.models.collection_item_line import CollectionItemLine
from app.models.collection_product_line import CollectionProductLine
from app.models.product_item import ProductItem
from app.repositories.collection_repository import CollectionRepository
from app.repositories.product_item_repository import ProductItemRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.collection import (
    CollectionCostBreakdown,
    CollectionCostPreviewRequest,
    CollectionCreate,
    CollectionDetailResponse,
    CollectionItemLineInput,
    CollectionProductLineInput,
    CollectionSummaryResponse,
    CollectionUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.product import AttachedChargeSummary
from app.services.collection_cost_service import (
    calculate_breakdown_for_collection,
    calculate_collection_cost_breakdown,
)
from app.utils.charge_applicability import COLLECTION_APPLICABILITIES, validate_charges_for_target


class CollectionService:
    """Handles collection CRUD and costing."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.collections = CollectionRepository(db)
        self.products = ProductRepository(db)
        self.product_items = ProductItemRepository(db)

    def create(self, payload: CollectionCreate) -> CollectionDetailResponse:
        if self.collections.get_by_name(payload.name):
            raise ConflictError("A collection with this name already exists")

        collection = Collection(
            name=payload.name,
            description=payload.description,
            selling_price=payload.selling_price,
            buffer_amount=payload.buffer_amount,
            is_active=payload.is_active,
            is_public=payload.is_public,
        )
        self._apply_product_lines(collection, payload.product_lines)
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

    def list(self, params: PaginationParams) -> PaginatedResponse[CollectionSummaryResponse]:
        items, total = self.collections.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        return PaginatedResponse(
            items=[CollectionSummaryResponse.model_validate(item) for item in items],
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
                "product_lines",
                "item_lines",
                "utility_charge_ids",
                "labour_charge_ids",
                "tax_charge_ids",
            },
        )
        if (
            not update_data
            and payload.product_lines is None
            and payload.item_lines is None
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
        if payload.selling_price is not None:
            collection.selling_price = payload.selling_price
        if payload.buffer_amount is not None:
            collection.buffer_amount = payload.buffer_amount
        if payload.is_active is not None:
            collection.is_active = payload.is_active
        if payload.is_public is not None:
            collection.is_public = payload.is_public

        if payload.product_lines is not None:
            self._replace_product_lines(collection, payload.product_lines)

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

    def preview_cost(self, payload: CollectionCostPreviewRequest) -> CollectionCostBreakdown:
        product_lines = self._build_preview_product_lines(payload.product_lines)
        item_lines = self._build_preview_item_lines(payload.item_lines)
        utility = self._resolve_charges(
            payload.utility_charge_ids,
            self.collections.get_utility_charges_by_ids,
            "utility",
        )
        labour = self._resolve_charges(
            payload.labour_charge_ids,
            self.collections.get_labour_charges_by_ids,
            "labour",
        )
        tax = self._resolve_charges(
            payload.tax_charge_ids,
            self.collections.get_tax_charges_by_ids,
            "tax",
        )
        return calculate_collection_cost_breakdown(
            selling_price=payload.selling_price,
            buffer_amount=payload.buffer_amount,
            product_lines=product_lines,
            item_lines=item_lines,
            utility_charges=utility,
            labour_charges=labour,
            tax_charges=tax,
        )

    def _replace_product_lines(
        self,
        collection: Collection,
        lines: list[CollectionProductLineInput],
    ) -> None:
        collection.product_lines.clear()
        self.db.flush()
        if lines:
            self._apply_product_lines(collection, lines)

    def _replace_item_lines(
        self,
        collection: Collection,
        lines: list[CollectionItemLineInput],
    ) -> None:
        collection.item_lines.clear()
        self.db.flush()
        if lines:
            self._apply_item_lines(collection, lines)

    def _apply_product_lines(
        self,
        collection: Collection,
        lines: list[CollectionProductLineInput],
    ) -> None:
        if not lines:
            return
        seen: set[uuid.UUID] = set()
        for line in lines:
            if line.product_id in seen:
                raise ValidationError("Duplicate product in collection")
            seen.add(line.product_id)

        products = self._load_products([line.product_id for line in lines])
        for line in lines:
            product = products[line.product_id]
            collection.product_lines.append(
                CollectionProductLine(
                    product_id=product.id,
                    quantity=line.quantity,
                ),
            )

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

    def _load_products(self, ids: list[uuid.UUID]):
        products_list = self.products.get_for_costing_by_ids(ids)
        products: dict[uuid.UUID, object] = {product.id: product for product in products_list}
        for product_id in ids:
            product = products.get(product_id)
            if not product:
                raise NotFoundError(f"Product not found: {product_id}")
            if not product.is_active:
                raise ValidationError(f"Product is inactive: {product.name}")
        return products

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

    def _build_preview_product_lines(
        self,
        lines: list[CollectionProductLineInput],
    ) -> list[CollectionProductLine]:
        preview_lines: list[CollectionProductLine] = []
        seen: set[uuid.UUID] = set()
        products = self._load_products([line.product_id for line in lines])
        for line in lines:
            if line.product_id in seen:
                raise ValidationError("Duplicate product in collection")
            seen.add(line.product_id)
            product = products[line.product_id]
            preview_lines.append(
                CollectionProductLine(
                    product_id=product.id,
                    quantity=line.quantity,
                    product=product,
                ),
            )
        return preview_lines

    def _build_preview_item_lines(
        self,
        lines: list[CollectionItemLineInput],
    ) -> list[CollectionItemLine]:
        preview_lines: list[CollectionItemLine] = []
        seen: set[uuid.UUID] = set()
        items = self._load_packaging_items([line.product_item_id for line in lines])
        for line in lines:
            if line.product_item_id in seen:
                raise ValidationError("Duplicate packaging item in collection")
            seen.add(line.product_item_id)
            item = items[line.product_item_id]
            preview_lines.append(
                CollectionItemLine(
                    product_item_id=item.id,
                    quantity=line.quantity,
                    product_item=item,
                ),
            )
        return preview_lines

    def _to_detail_response(self, collection: Collection) -> CollectionDetailResponse:
        breakdown = calculate_breakdown_for_collection(collection)
        return CollectionDetailResponse(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            selling_price=collection.selling_price,
            buffer_amount=collection.buffer_amount,
            is_active=collection.is_active,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            product_lines=breakdown.products.lines,
            item_lines=breakdown.collection_items.lines,
            utility_charges=[self._charge_summary(c) for c in collection.utility_charges],
            labour_charges=[self._charge_summary(c) for c in collection.labour_charges],
            tax_charges=[self._charge_summary(c) for c in collection.tax_charges],
            cost_breakdown=breakdown,
        )

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
