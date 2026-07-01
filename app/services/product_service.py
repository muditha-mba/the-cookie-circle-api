"""Product business logic."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.product import Product
from app.models.product_recipe_line import ProductRecipeLine
from app.repositories.product_category_repository import ProductCategoryRepository
from app.repositories.product_item_repository import ProductItemRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.product import (
    ProductCostBreakdown,
    ProductCostPreviewRequest,
    ProductCreate,
    ProductDetailResponse,
    ProductSummaryResponse,
    ProductUpdate,
    RecipeLineInput,
)
from app.services.product_cost_service import calculate_breakdown_for_product, calculate_product_cost_breakdown
from app.utils.product_duplicate_name import generate_duplicate_product_name


class ProductService:
    """Handles product CRUD and costing."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.product_items = ProductItemRepository(db)
        self.categories = ProductCategoryRepository(db)

    def create(self, payload: ProductCreate) -> ProductDetailResponse:
        if self.products.get_by_name(payload.name):
            raise ConflictError("A product with this name already exists")

        product = Product(
            name=payload.name,
            description=payload.description,
            category_id=self._resolve_category(payload.category_id).id,
            selling_price=payload.selling_price,
            buffer_amount=payload.buffer_amount,
            yield_quantity=payload.yield_quantity,
            production_notes=payload.production_notes,
            is_active=payload.is_active,
            is_public=payload.is_public,
        )
        self._apply_recipe_lines(product, payload.recipe_lines)
        self.products.create(product)
        self.db.commit()
        loaded = self.products.get_by_id(product.id)
        assert loaded is not None
        return self._to_detail_response(loaded)

    def get(self, product_id: uuid.UUID) -> ProductDetailResponse:
        product = self.products.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")
        return self._to_detail_response(product)

    def list(self, params: PaginationParams) -> PaginatedResponse[ProductSummaryResponse]:
        items, total = self.products.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        return PaginatedResponse(
            items=[ProductSummaryResponse.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.products.total_pages(total, params.page_size),
        )

    def update(self, product_id: uuid.UUID, payload: ProductUpdate) -> ProductDetailResponse:
        product = self.products.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")

        update_data = payload.model_dump(
            exclude_unset=True,
            exclude={"recipe_lines"},
        )
        if not update_data and payload.recipe_lines is None:
            raise ValidationError("No fields provided to update")

        if payload.name is not None:
            existing = self.products.get_by_name(payload.name)
            if existing and existing.id != product.id:
                raise ConflictError("A product with this name already exists")
            product.name = payload.name

        if payload.description is not None:
            product.description = payload.description
        if payload.category_id is not None:
            product.category_id = self._resolve_category(payload.category_id).id
        if payload.selling_price is not None:
            product.selling_price = payload.selling_price
        if payload.buffer_amount is not None:
            product.buffer_amount = payload.buffer_amount
        if payload.yield_quantity is not None:
            product.yield_quantity = payload.yield_quantity
        if payload.production_notes is not None:
            product.production_notes = payload.production_notes
        if payload.is_active is not None:
            product.is_active = payload.is_active
        if payload.is_public is not None:
            product.is_public = payload.is_public

        if payload.recipe_lines is not None:
            self._replace_recipe_lines(product, payload.recipe_lines)

        self.db.add(product)
        self.db.commit()
        loaded = self.products.get_by_id(product.id)
        assert loaded is not None
        return self._to_detail_response(loaded)

    def delete(self, product_id: uuid.UUID) -> None:
        product = self.products.get_by_id(product_id)
        if not product:
            raise NotFoundError("Product not found")
        self.products.delete(product)
        self.db.commit()

    def duplicate(self, product_id: uuid.UUID) -> ProductDetailResponse:
        """Create a new product copied from an existing one, including recipe lines."""
        source = self.products.get_by_id(product_id)
        if not source:
            raise NotFoundError("Product not found")

        duplicate_name = generate_duplicate_product_name(
            source.name,
            name_exists=lambda name: self.products.get_by_name(name) is not None,
        )

        product = Product(
            name=duplicate_name,
            description=source.description,
            category_id=source.category_id,
            selling_price=source.selling_price,
            buffer_amount=source.buffer_amount,
            yield_quantity=source.yield_quantity,
            production_notes=source.production_notes,
            is_active=source.is_active,
            is_public=source.is_public,
            is_premium=source.is_premium,
        )

        recipe_lines = [
            RecipeLineInput(product_item_id=line.product_item_id, quantity=line.quantity)
            for line in source.recipe_lines
        ]
        self._apply_recipe_lines(product, recipe_lines)
        self.products.create(product)
        self.db.commit()

        loaded = self.products.get_by_id(product.id)
        assert loaded is not None
        return self._to_detail_response(loaded)

    def preview_cost(self, payload: ProductCostPreviewRequest) -> ProductCostBreakdown:
        recipe_lines = self._build_preview_recipe_lines(payload.recipe_lines)
        return calculate_product_cost_breakdown(
            selling_price=payload.selling_price,
            buffer_amount=payload.buffer_amount,
            yield_quantity=payload.yield_quantity,
            recipe_lines=recipe_lines,
        )

    def _replace_recipe_lines(self, product: Product, lines: list[RecipeLineInput]) -> None:
        """Replace all recipe lines, flushing deletes before inserts."""
        product.recipe_lines.clear()
        self.db.flush()
        if lines:
            self._apply_recipe_lines(product, lines)

    def _apply_recipe_lines(self, product: Product, lines: list[RecipeLineInput]) -> None:
        if not lines:
            return
        seen: set[uuid.UUID] = set()
        for line in lines:
            if line.product_item_id in seen:
                raise ValidationError("Duplicate product item in recipe")
            seen.add(line.product_item_id)

        items = self._load_product_items([line.product_item_id for line in lines])
        for line in lines:
            item = items[line.product_item_id]
            product.recipe_lines.append(
                ProductRecipeLine(
                    product_item_id=item.id,
                    quantity=line.quantity,
                ),
            )

    def _load_product_items(self, ids: list[uuid.UUID]):
        items: dict[uuid.UUID, object] = {}
        for item_id in ids:
            item = self.product_items.get_by_id(item_id)
            if not item:
                raise NotFoundError(f"Product item not found: {item_id}")
            if not item.is_active:
                raise ValidationError(f"Product item is inactive: {item.name}")
            items[item_id] = item
        return items

    def _build_preview_recipe_lines(self, lines: list[RecipeLineInput]) -> list[ProductRecipeLine]:
        preview_lines: list[ProductRecipeLine] = []
        seen: set[uuid.UUID] = set()
        for line in lines:
            if line.product_item_id in seen:
                raise ValidationError("Duplicate product item in recipe")
            seen.add(line.product_item_id)
            item = self.product_items.get_by_id(line.product_item_id)
            if not item:
                raise NotFoundError(f"Product item not found: {line.product_item_id}")
            preview_lines.append(
                ProductRecipeLine(
                    product_item_id=item.id,
                    quantity=line.quantity,
                    product_item=item,
                ),
            )
        return preview_lines

    def _to_detail_response(self, product: Product) -> ProductDetailResponse:
        breakdown = calculate_breakdown_for_product(product)
        return ProductDetailResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            category_id=product.category_id,
            selling_price=product.selling_price,
            buffer_amount=product.buffer_amount,
            yield_quantity=product.yield_quantity,
            production_notes=product.production_notes,
            is_active=product.is_active,
            is_public=product.is_public,
            created_at=product.created_at,
            updated_at=product.updated_at,
            recipe_lines=breakdown.ingredients.lines,
            cost_breakdown=breakdown,
        )

    def _resolve_category(self, category_id: uuid.UUID):
        category = self.categories.get_by_id(category_id)
        if not category:
            raise NotFoundError("Product category not found")
        if not category.is_active:
            raise ValidationError(f"Product category is inactive: {category.name}")
        return category
